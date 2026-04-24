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
    winning_team_number INT
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
    PRIMARY KEY (move_id, tile_id),
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
    p.player_id,
    p.username,
    RANK() OVER (ORDER BY COALESCE(s.wins, 0) DESC, p.rating DESC) AS `rank`,
    COALESCE(s.wins, 0) AS wins,
    COALESCE(s.losses, 0) AS losses,
    CASE
        WHEN COALESCE(s.wins, 0) + COALESCE(s.losses, 0) = 0 THEN 0.00
        ELSE ROUND(s.wins * 100.0 / (s.wins + s.losses), 2)
    END AS win_rate
FROM Player p
LEFT JOIN Player_Stats ps ON p.player_id = ps.player_id
LEFT JOIN Stats s ON ps.stats_id = s.stats_id;
