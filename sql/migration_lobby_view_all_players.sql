-- Align wins/losses/win% with completed games (same rules as /api/leaderboard).
-- Run after: USE your_database;
CREATE OR REPLACE VIEW Lobby AS
SELECT
    t.player_id,
    t.username,
    t.rating,
    RANK() OVER (ORDER BY t.wins DESC, t.rating DESC) AS `rank`,
    t.wins,
    t.losses,
    t.win_rate
FROM (
    SELECT
        p.player_id,
        p.username,
        p.rating,
        COALESCE(m.wins, 0) AS wins,
        COALESCE(m.losses, 0) AS losses,
        CASE
            WHEN COALESCE(m.wins, 0) + COALESCE(m.losses, 0) = 0 THEN 0.00
            ELSE ROUND(
                100.0 * COALESCE(m.wins, 0)
                / (COALESCE(m.wins, 0) + COALESCE(m.losses, 0)),
                2
            )
        END AS win_rate
    FROM Player p
    LEFT JOIN (
        SELECT
            gp.player_id,
            SUM(
                CASE
                    WHEN (
                        CASE WHEN gp.seat_position IN (1, 3) THEN 1 ELSE 2 END
                    ) = g.winning_team_number
                    THEN 1
                    ELSE 0
                END
            ) AS wins,
            SUM(
                CASE
                    WHEN (
                        CASE WHEN gp.seat_position IN (1, 3) THEN 1 ELSE 2 END
                    ) <> g.winning_team_number
                    THEN 1
                    ELSE 0
                END
            ) AS losses
        FROM Game_Player gp
        INNER JOIN Game g ON g.game_id = gp.game_id
        WHERE g.status = 'completed' AND g.winning_team_number IS NOT NULL
        GROUP BY gp.player_id
    ) m ON m.player_id = p.player_id
) t;
