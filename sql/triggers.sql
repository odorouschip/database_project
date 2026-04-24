USE goita;

DROP TRIGGER IF EXISTS after_player_insert;
DROP TRIGGER IF EXISTS after_game_completed;

DELIMITER //

CREATE TRIGGER after_player_insert
AFTER INSERT ON Player
FOR EACH ROW
BEGIN
    INSERT INTO Stats (wins, losses, average_score) VALUES (0, 0, 0.00);
    INSERT INTO Player_Stats (player_id, stats_id) VALUES (NEW.player_id, LAST_INSERT_ID());
END //

CREATE TRIGGER after_game_completed
AFTER UPDATE ON Game
FOR EACH ROW
BEGIN
    IF NEW.status = 'completed'
       AND (OLD.status IS NULL OR OLD.status <> 'completed')
       AND NEW.winning_team_number IS NOT NULL THEN

        UPDATE Stats s
        JOIN Player_Stats ps ON ps.stats_id = s.stats_id
        JOIN Game_Player gp ON gp.player_id = ps.player_id
        JOIN Team t ON t.game_id = gp.game_id
            AND t.team_number = (CASE WHEN gp.seat_position IN (1,3) THEN 1 ELSE 2 END)
        SET s.average_score =
            (s.average_score * (s.wins + s.losses) + t.score) / (s.wins + s.losses + 1)
        WHERE gp.game_id = NEW.game_id;

        UPDATE Stats s
        JOIN Player_Stats ps ON ps.stats_id = s.stats_id
        JOIN Game_Player gp ON gp.player_id = ps.player_id
        SET s.wins = s.wins + 1
        WHERE gp.game_id = NEW.game_id
          AND (CASE WHEN gp.seat_position IN (1,3) THEN 1 ELSE 2 END) = NEW.winning_team_number;

        UPDATE Stats s
        JOIN Player_Stats ps ON ps.stats_id = s.stats_id
        JOIN Game_Player gp ON gp.player_id = ps.player_id
        SET s.losses = s.losses + 1
        WHERE gp.game_id = NEW.game_id
          AND (CASE WHEN gp.seat_position IN (1,3) THEN 1 ELSE 2 END) <> NEW.winning_team_number;

        UPDATE Player p
        JOIN Game_Player gp ON gp.player_id = p.player_id
        SET p.rating = p.rating + 25
        WHERE gp.game_id = NEW.game_id
          AND (CASE WHEN gp.seat_position IN (1,3) THEN 1 ELSE 2 END) = NEW.winning_team_number;

        UPDATE Player p
        JOIN Game_Player gp ON gp.player_id = p.player_id
        SET p.rating = GREATEST(p.rating - 25, 0)
        WHERE gp.game_id = NEW.game_id
          AND (CASE WHEN gp.seat_position IN (1,3) THEN 1 ELSE 2 END) <> NEW.winning_team_number;
    END IF;
END //

DELIMITER ;
