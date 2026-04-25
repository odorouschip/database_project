-- Run once on existing DBs: allow two of the same tile kind in one move.
USE goita;

ALTER TABLE Tile_Moved
  DROP PRIMARY KEY,
  ADD COLUMN line_idx TINYINT UNSIGNED NOT NULL DEFAULT 0 AFTER tile_id,
  ADD PRIMARY KEY (move_id, tile_id, line_idx);
