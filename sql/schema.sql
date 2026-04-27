USE goita;

DROP VIEW IF EXISTS Lobby;
DROP TABLE IF EXISTS Game_Moves;
DROP TABLE IF EXISTS Players_Team;
DROP TABLE IF EXISTS Replay;
DROP TABLE IF EXISTS Tile_Moved;
DROP TABLE IF EXISTS Player_Move;
DROP TABLE IF EXISTS Game_Player;
DROP TABLE IF EXISTS Games_Rounds;
DROP TABLE IF EXISTS Team;
DROP TABLE IF EXISTS Player_Stats;
DROP TABLE IF EXISTS Move;
DROP TABLE IF EXISTS Round;
DROP TABLE IF EXISTS Tile;
DROP TABLE IF EXISTS Stats;
DROP TABLE IF EXISTS Game;
DROP TABLE IF EXISTS Player;

CREATE TABLE Player (
    player_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    created_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_time DATETIME,
    rating INT NOT NULL DEFAULT 1000
);

CREATE TABLE Stats (
    stats_id INT AUTO_INCREMENT PRIMARY KEY,
    wins INT NOT NULL DEFAULT 0,
    losses INT NOT NULL DEFAULT 0,
    average_score DECIMAL(7,2) NOT NULL DEFAULT 0.00
);

CREATE TABLE Game (
    game_id INT AUTO_INCREMENT PRIMARY KEY,
    started_time DATETIME NOT NULL,
    ended_time DATETIME,
    status VARCHAR(20) NOT NULL,
    target_score INT NOT NULL,
    winning_team_number INT,
    deal_seed INT UNSIGNED,
    current_round INT NOT NULL DEFAULT 1
);

CREATE TABLE Round (
    round_id INT AUTO_INCREMENT PRIMARY KEY,
    round_number INT NOT NULL
);

CREATE TABLE Tile (
    tile_id INT AUTO_INCREMENT PRIMARY KEY,
    tile_name VARCHAR(50) NOT NULL,
    score INT NOT NULL,
    image VARCHAR(255)
);

CREATE TABLE Move (
    move_id INT AUTO_INCREMENT PRIMARY KEY,
    order_played INT NOT NULL,
    time_stamp DATETIME NOT NULL
);

CREATE TABLE Player_Stats (
    player_id INT NOT NULL,
    stats_id INT NOT NULL,
    PRIMARY KEY (player_id, stats_id),
    FOREIGN KEY (player_id) REFERENCES Player(player_id),
    FOREIGN KEY (stats_id) REFERENCES Stats(stats_id)
);

CREATE TABLE Team (
    team_id INT AUTO_INCREMENT PRIMARY KEY,
    game_id INT NOT NULL,
    team_number INT NOT NULL,
    score INT NOT NULL DEFAULT 0,
    UNIQUE (game_id, team_number),
    FOREIGN KEY (game_id) REFERENCES Game(game_id)
);

CREATE TABLE Games_Rounds (
    game_id INT NOT NULL,
    round_id INT NOT NULL,
    PRIMARY KEY (game_id, round_id),
    FOREIGN KEY (game_id) REFERENCES Game(game_id),
    FOREIGN KEY (round_id) REFERENCES Round(round_id)
);

CREATE TABLE Game_Player (
    game_id INT NOT NULL,
    player_id INT NOT NULL,
    seat_position INT NOT NULL,
    PRIMARY KEY (game_id, player_id),
    UNIQUE (game_id, seat_position),
    FOREIGN KEY (game_id) REFERENCES Game(game_id),
    FOREIGN KEY (player_id) REFERENCES Player(player_id)
);

CREATE TABLE Player_Move (
    player_id INT NOT NULL,
    move_id INT NOT NULL,
    PRIMARY KEY (player_id, move_id),
    FOREIGN KEY (player_id) REFERENCES Player(player_id),
    FOREIGN KEY (move_id) REFERENCES Move(move_id)
);

CREATE TABLE Tile_Moved (
    move_id INT NOT NULL,
    tile_id INT NOT NULL,
    line_idx TINYINT UNSIGNED NOT NULL DEFAULT 0,
    PRIMARY KEY (move_id, tile_id, line_idx),
    FOREIGN KEY (move_id) REFERENCES Move(move_id),
    FOREIGN KEY (tile_id) REFERENCES Tile(tile_id)
);

CREATE TABLE Replay (
    replay_id INT AUTO_INCREMENT PRIMARY KEY,
    game_id INT NOT NULL UNIQUE,
    FOREIGN KEY (game_id) REFERENCES Game(game_id)
);

CREATE TABLE Players_Team (
    player_id INT NOT NULL,
    team_id INT NOT NULL,
    PRIMARY KEY (player_id, team_id),
    FOREIGN KEY (player_id) REFERENCES Player(player_id),
    FOREIGN KEY (team_id) REFERENCES Team(team_id)
);

CREATE TABLE Game_Moves (
    game_id INT NOT NULL,
    round_id INT NOT NULL,
    move_id INT NOT NULL,
    PRIMARY KEY (game_id, round_id, move_id),
    FOREIGN KEY (game_id) REFERENCES Game(game_id),
    FOREIGN KEY (round_id) REFERENCES Round(round_id),
    FOREIGN KEY (move_id) REFERENCES Move(move_id)
);

CREATE VIEW Lobby AS
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
