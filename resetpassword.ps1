param(
    [string]$Username,
    [string]$NewPassword
)

# Importation du module Active Directory
Import-Module ActiveDirectory

# Réinitialisation du mot de passe
Set-ADAccountPassword -Identity $Username -Reset -NewPassword (ConvertTo-SecureString -AsPlainText $NewPassword -Force)

# Activation du compte en cas de besoin (décommenter la ligne suivante si nécessaire)
Enable-ADAccount -Identity $Username
