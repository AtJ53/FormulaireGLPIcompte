import sys
import yaml
import requests
import unicodedata
import ldap
import datetime
from ldap import modlist
import random
import string
import os
import logging

def get_interface(id_reponse):
    logging.debug("Récupération des interfaces pour l'ID de réponse: {}".format(id_reponse))
    questions_url = f"{API['AppURL']}/PluginFormcreatorQuestion?expand_drodpowns=true&range=0-1000"
    answers_url = f"{API['AppURL']}/PluginFormcreatorAnswer?expand_drodpowns=true&range=0-1000"

    questions_response = requests.get(questions_url, headers=headers, verify=False)
    answers_response = requests.get(answers_url, headers=headers, verify=False)

    questions = questions_response.json()
    answers = answers_response.json()

    filtered_answers = [answer for answer in answers if answer['plugin_formcreator_formanswers_id'] == id_reponse]

    resultat = []

    for answer in filtered_answers:
        question = next((question for question in questions if question['id'] == answer['plugin_formcreator_questions_id']), None)

        if question:
            prop_name = question['name']
            prop_value = answer['answer']

            obj = {prop_name: prop_value}
            resultat.append(obj)
    return resultat

#------------------------------------------------------------------------------#
#Partie Import des données et log                                              #
#------------------------------------------------------------------------------#

cheminscript = os.path.dirname(os.path.abspath(__file__))

cheminlog = os.path.join(cheminscript, 'log', 'app.log')

logging.basicConfig(filename=cheminlog,
                    filemode='a',  # 'a' pour ajouter les logs aux fichiers existants
                    level=logging.DEBUG,  # Niveau de log le plus bas à capturer
                    format='%(asctime)s - %(levelname)s - %(message)s')  # Format des messages de log

logging.info("Démarrage du script")

logging.info("Chemin du script: {}".format(cheminscript))

cheminyaml = os.path.join(cheminscript, 'Conf', 'configuration.yml')
cheminfichecollaborateur = os.path.join(cheminscript, 'Fichecollaborateur')

with open(cheminyaml, 'r') as file:
    params = yaml.safe_load(file)

Questions = params['Nomdesquestions']
API = params['API']
AD = params['AD']
Profils = params['Profil']
SSH = params['SSH']

id_reponse = int(sys.argv[1])
logging.info("ID de réponse récupéré: {}".format(id_reponse))

#-----------------------------------------------------------------------------#
#Partie API                                                                   #
#-----------------------------------------------------------------------------#

# Déclaration des headers pour l'initialisation
headers_init = {
    "Content-Type": "application/json",
    "Authorization": f"{API['AuthorizationType']} {API['user_token']}",
    "App-Token": f"{API['app_token']}"
}

# Initialisation du session token
response = requests.get(f"{API['AppURL']}/initSession", headers=headers_init, verify=False)

# Vérification si la requête a réussi et extraction du session token
if response.status_code == 200:
    session_token = response.json().get('session_token')
    logging.info("Session token récupéré avec succès")
else:
    logging.error(f"Erreur lors de l'initialisation de la session : {response.status_code}")

# Si le session token a bien été récupéré, déclaration des headers principaux
if session_token:
    headers = {
        "session-token": session_token,
        "App-Token": API['app_token']
    }

formulaire = get_interface(id_reponse)

#-----------------------------------------------------------------------------#
#Partie création du compte                                                    #
#-----------------------------------------------------------------------------#

#Initialisation de la connexion au serveur active directory.
ldap_conn = ldap.initialize(AD['Serveur'])
try:
    ldap_conn.simple_bind_s(AD['utilisateur'], AD['password'])
    logging.info("Connexion LDAP réussie")
except ldap.LDAPError as e:
    logging.error(f"Erreur de connexion LDAP: {e}")

#Déclaration des valeurs utiles.
nom = formulaire[0][Questions['Nomducollaborteur']]
prenom = formulaire[1][Questions['Prenomducollaborateur']]
nomprofilform = formulaire[2][Questions['Profils']]
type_contrat = formulaire[3][Questions['typedecontrat']]
date_text = formulaire[5][Questions['Datedepart']] 

paramprofil = Profils[nomprofilform]
nomprenom = nom + ' ' + prenom

# Mise en forme de la nomenclature du nom de compte.
# Dans notre cas, c'est la première lettre du prénom et le nom.
initiales = prenom[0] + nom
initiales_sans_accents = unicodedata.normalize('NFKD', initiales).encode('ASCII', 'ignore').decode()
initiales_sans_caracteres_speciaux = ''.join(c for c in initiales_sans_accents if c.isalpha())
identifiant = initiales_sans_caracteres_speciaux.lower()
identifiantorigine = initiales_sans_caracteres_speciaux.lower()

#Recherche du compte en cas de création déja existante.
#Si compte existe déjà ajoute +1 ce qui donne {nomcompte}i.
#Sinon passe à la suite.
recherche = f"(sAMAccountName={identifiant})"

recherche = 1
i = 0

while recherche == 1:
    search_filter = f"(sAMAccountName={identifiant})"
    ldap_result_id = ldap_conn.search(AD['basederecherche'], ldap.SCOPE_SUBTREE, search_filter, None)
    result_set = []
    while True:
        result_type, result_data = ldap_conn.result(ldap_result_id, 0)
        if result_data == []:
            break
        else:
            if result_type == ldap.RES_SEARCH_ENTRY:
                result_set.append(result_data)
    if (len(result_set)) == 1:
        i = i + 1
        identifiant =  f"{identifiantorigine}{i}"
        logging.warning("Nom d'utilisateur déjà pris, nouveau nom généré : {}".format(identifiant))
        recherche = 1
    else:
        recherche = 0
        logging.info("Nom d'utilisateur unique confirmé : {}".format(identifiant))

#Création du compte
user_cn = identifiant
user_ou_dn = paramprofil['OU']  
user_dn = f"cn={user_cn},{user_ou_dn}"  
user_samaccountname = user_cn  
user_upn = f"{user_cn}@{AD['mail']}" 

#Génère le mot de passe aléatoire et l'encode
letters = string.ascii_letters
digits = string.digits
punctuation = '?!'
password = [
    random.choice(letters),
    random.choice(digits),
    random.choice(punctuation)
]
all_characters = letters + digits + punctuation
password += [random.choice(all_characters) for _ in range(12)]
random.shuffle(password)
password = ''.join(password)
password_value = ('"' + password + '"').encode('utf-16-le')

#Si c'est un contrat à durée limité : Ajoute date d'expiration en fonction de la date d'arriver.
#Sinon c'est un contrat limité : Ajoute date d'expiration jamais.
if type_contrat != "CDI":
    date_object = datetime.datetime.strptime(date_text, "%Y-%m-%d")
    epoch_start = datetime.datetime(year=1601, month=1, day=1)
    expiration_timestamp = int((date_object - epoch_start).total_seconds() * 10000000)
    account_expires = str(expiration_timestamp).encode()
    logging.info("Compte avec expiration configurée.")
else:
    account_expires = b'9223372036854775807'  # Jamais expirer
    logging.info("Compte CDI configuré pour ne jamais expirer.")

#Tableau des attributs du compte.
user_attrs = {
    "objectClass": [b"top", b"person", b"organizationalPerson", b"user"],
    "cn": [user_cn.encode()],
    "sn": [nom.encode()],
    "givenName": [prenom.encode()],
    "displayName": [nomprenom.encode()],
    "userPrincipalName": [user_upn.encode()],
    "sAMAccountName": [user_cn.encode()],
    "userAccountControl": [b'514'],
    "userPassword": [password_value],
    "mail": [user_upn.encode()],
    "accountExpires": [account_expires]
}

# Préparation de la liste de modifications à appliquer
ldif = modlist.addModlist(user_attrs)

# Ajout de l'utilisateur
try:
    ldap_conn.add_s(user_dn, ldif)
    logging.info("Compte utilisateur créé avec succès : {}".format(user_dn))
except ldap.LDAPError as e:
    logging.error("Erreur lors de la création du compte utilisateur : {}".format(e))

#Ajout du profil (Groupe de sécurité) à l'utilisateurs
group_ou_dn = AD['ouprofil']
group_cn = paramprofil['Nomdugroupe']
group_dn = f"cn={group_cn},{group_ou_dn}"

group_attrs = [(ldap.MOD_ADD, 'member', [user_dn.encode()])]

try:
    ldap_conn.modify_s(group_dn, group_attrs)
    logging.info("Utilisateur ajouté au groupe de sécurité.")
except ldap.LDAPError as e:
    logging.error("Erreur lors de l'ajout au groupe de sécurité : {}".format(e))

#Cette partie n'est pas obligatoire si votre ad est en ldaps
import paramiko
if AD['Protocol'] != "ldaps":
    command = f"powershell -ExecutionPolicy Bypass -File {SSH['cheminscript']}{SSH['scriptpowershell']} {identifiant} {password}"

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(SSH['host'], port=22, username=SSH['username'], password=SSH['password'])
    try:
        stdin, stdout, stderr = client.exec_command(command)
        logging.info("Commande PowerShell exécutée via SSH.")
        logging.info(stdout.read().decode('utf-8'))  # Affiche la sortie de la commande
        if stderr:
            logging.error(stderr.read().decode('utf-8'))  # Affiche les erreurs si elles existent
    except Exception as e:
        logging.error("Erreur lors de l'exécution de la commande SSH : {}".format(e))


#------------------------------------------------------------------------
# Partie création d'une fiche récapitulatif
#------------------------------------------------------------------------

fichecollaborateur = [
    ['Login', identifiant],
    ['Nom', nom],
    ['Prénom', prenom],
    ['motdepasse', password],
]

date_heure = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
nom_fichier = f'donnees_{date_heure}_{identifiant}.txt'
chemin_complet_fichecollaborateur = os.path.join(cheminfichecollaborateur, nom_fichier)
try:
    with open(chemin_complet_fichecollaborateur, 'w') as fichier:
        for ligne in fichecollaborateur:
            fichier.write('\t'.join(ligne) + '\n')
    logging.info("Fiche collaborateur créée : {}".format(chemin_complet_fichecollaborateur))
except IOError as e:
    logging.error("Impossible de créer la fiche collaborateur : {}".format(e))
