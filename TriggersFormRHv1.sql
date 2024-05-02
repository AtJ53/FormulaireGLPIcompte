DELIMITER //

CREATE TRIGGER after_status_update
AFTER UPDATE ON glpi_plugin_formcreator_formanswers
FOR EACH ROW
BEGIN
    IF NEW.status = '103' AND NEW.plugin_formcreator_forms_id = 2 THEN
        SET @command = CONCAT('script/script.py ', NEW.id);
        INSERT INTO GLPIFormulaire.trigger_formulaire_rh_entre (nom_table, action_trigger, id_de_reponse_au_formulaire, commande, date_execution)
        VALUES ('glpi_plugin_formcreator_formanswers', 'AFTER UPDATE', NEW.id, @command, CURDATE());
    END IF;
END;

//
DELIMITER ;
