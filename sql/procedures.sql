USE goita;

DROP PROCEDURE IF EXISTS FinishGame;

DELIMITER //

CREATE PROCEDURE FinishGame(IN p_game_id INT)
BEGIN
    DECLARE v_winning_team_number INT;
    DECLARE v_max_score INT;

    SELECT MAX(score)
    INTO v_max_score
    FROM Team
    WHERE game_id = p_game_id;

    SELECT team_number
    INTO v_winning_team_number
    FROM Team
    WHERE game_id = p_game_id
      AND score = v_max_score
    LIMIT 1;

    UPDATE Game
    SET status = 'completed',
        ended_time = NOW(),
        winning_team_number = v_winning_team_number
    WHERE game_id = p_game_id;
END //

DELIMITER ;

ALTER TABLE Game
ADD CONSTRAINT chk_game_status
CHECK (status IN ('active', 'completed', 'cancelled'));

ALTER TABLE Team
ADD CONSTRAINT chk_team_score_nonnegative
CHECK (score >= 0);

ALTER TABLE Stats
ADD CONSTRAINT chk_stats_nonnegative
CHECK (wins >= 0 AND losses >= 0 AND average_score >= 0);
