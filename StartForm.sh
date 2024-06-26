#!/bin/bash

# Paramètres de connexion à la base de données
USER="GLPIFormulaire"
PASSWORD=""
DATABASE="GLPIFormulaire"
HOST="192.168.x.x"

# Requête SQL
QUERY="SELECT id_de_reponse_au_formulaire FROM trigger_formulaire_rh_entre WHERE DATE(date_execution) = CURDATE();"

# Exécution de la requête et stockage des résultats dans une variable
RESULTS=$(mysql -h "$HOST" -u "$USER" -p"$PASSWORD" "$DATABASE" -e "$QUERY" -s -N)

# Compter le nombre de résultats
RESULT_COUNT=$(echo "$RESULTS" | wc -l)

if [ "$RESULTS" -eq $null ]; then
    echo "Aucun résultat trouvé, arrêt du script."
    exit 0
fi

source script/bin/active

# Boucle basée sur la longueur du résultat
for (( i=1; i<=$RESULT_COUNT; i++ ))
do
    # Extraction d'une ligne à la fois
    LINE=$(echo "$RESULTS" | sed -n "${i}p")
    
    python3 /path/DSI-CreateCompte.py $LINE
    
    sleep 1m
done
