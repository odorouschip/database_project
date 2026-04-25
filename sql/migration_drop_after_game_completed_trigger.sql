-- Run once if you upgraded from a version that installed after_game_completed on Game.
-- Match completion effects are now applied in app.py (complete_match) so they work without triggers.
DROP TRIGGER IF EXISTS after_game_completed;
