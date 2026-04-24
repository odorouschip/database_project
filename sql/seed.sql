USE goita;

INSERT INTO Player (username, password, created_time, last_login_time, rating) VALUES
('alice', 'hashed_pw_1', NOW(), NOW(), 1050),
('bob',   'hashed_pw_2', NOW(), NOW(), 980),
('carol', 'hashed_pw_3', NOW(), NOW(), 1100),
('dave',  'hashed_pw_4', NOW(), NOW(), 1020);

INSERT INTO Stats (wins, losses, average_score) VALUES
(10, 5, 42.50),
(7, 8, 31.75),
(12, 3, 47.20),
(5, 10, 28.40);

INSERT INTO Player_Stats (player_id, stats_id) VALUES
(1,1),(2,2),(3,3),(4,4);

INSERT INTO Game (started_time, ended_time, status, target_score, winning_team_number) VALUES
(NOW(), NULL, 'active', 100, NULL),
(DATE_SUB(NOW(), INTERVAL 2 DAY), DATE_SUB(NOW(), INTERVAL 2 DAY) + INTERVAL 1 HOUR, 'completed', 100, 1);

INSERT INTO Team (game_id, team_number, score) VALUES
(1, 1, 0),
(1, 2, 0),
(2, 1, 120),
(2, 2, 95);

INSERT INTO Round (round_number) VALUES
(1),(2),(3);

INSERT INTO Games_Rounds (game_id, round_id) VALUES
(1,1),(1,2),(1,3),(2,1);

INSERT INTO Game_Player (game_id, player_id, seat_position) VALUES
(1,1,1),(1,2,2),(1,3,3),(1,4,4),
(2,1,1),(2,2,2),(2,3,3),(2,4,4);

INSERT INTO Players_Team (player_id, team_id) VALUES
(1,1),(3,1),(2,2),(4,2);

INSERT INTO Tile (tile_name, score, image) VALUES
('King',   50, NULL),
('Rook',   40, NULL),
('Bishop', 40, NULL),
('Gold',   30, NULL),
('Silver', 30, NULL),
('Knight', 20, NULL),
('Lance',  20, NULL),
('Pawn',   10, NULL);

INSERT INTO Move (order_played, time_stamp) VALUES
(1, NOW()),
(2, NOW()),
(3, NOW()),
(4, NOW());

INSERT INTO Player_Move (player_id, move_id) VALUES
(1,1),(2,2),(3,3),(4,4);

INSERT INTO Tile_Moved (move_id, tile_id) VALUES
(1,1),(1,2),
(2,3),
(3,4),(3,5),
(4,1);

INSERT INTO Game_Moves (game_id, round_id, move_id) VALUES
(1,1,1),
(1,1,2),
(1,1,3),
(1,1,4);

INSERT INTO Replay (game_id) VALUES
(2);
