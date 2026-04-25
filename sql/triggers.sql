USE goita;

DROP TRIGGER IF EXISTS after_player_insert;
DROP TRIGGER IF EXISTS after_game_completed;

DELIMITER //

-- Stats row for each new player. Install this trigger if new accounts are created via the app
-- and you are not mirroring the logic in Python. Required for Player_Stats / Stats integrity.
CREATE TRIGGER after_player_insert
AFTER INSERT ON Player
FOR EACH ROW
BEGIN
    INSERT INTO Stats (wins, losses, average_score) VALUES (0, 0, 0.00);
    INSERT INTO Player_Stats (player_id, stats_id) VALUES (NEW.player_id, LAST_INSERT_ID());
END //

-- Match completion (rating ±25, stats, average) is applied in app.py complete_match.
-- The old after_game_completed trigger was removed to avoid double-applying and to work
-- when triggers are not installed. If you have that trigger from an older version, run:
--   sql/migration_drop_after_game_completed_trigger.sql

DELIMITER ;
