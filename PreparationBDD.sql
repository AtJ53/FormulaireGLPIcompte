DELIMITER //

Create database GLPIFormulaire;

CREATE TABLE GLPIFormulaire.trigger_formulaire_rh_entre (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    nom_table VARCHAR(64),
    action_trigger VARCHAR(32),
    id_de_reponse_au_formulaire INT,
    commande TEXT,
    date_execution DATETIME
);

CREATE USER 'GLPIFormulaire'@'localhost' IDENTIFIED BY 'azerty';

GRANT SELECT ON GLPIFormulaire.* TO 'GLPIFormulaire'@'localhost';

FLUSH PRIVILEGES;

//
DELIMITER ;
