import os
import mysql.connector

from classes.password_handler import password_handler

from mysql.connector import Error
from mysql.connector.errors import IntegrityError, ProgrammingError
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template, redirect, url_for, session

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")
if not app.secret_key:
    raise RuntimeError("FLASK_SECRET_KEY not set. please set in .env for session control")

def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def logged_in():
    if 'player_id' not in session:
        return False
    return True

def redirect_to_login():
    return redirect(url_for('show_login'))

@app.route('/')
def home():
    if not logged_in():
        return redirect_to_login()

    return redirect(url_for('show_matchmaking'))


@app.route('/login')
def show_login():
    return render_template('login.html')

@app.route('/api/login_button', methods=['POST'])
def check_user():
    data = request.json
    ph = password_handler()

    username = data.get('username')
    password = data.get('password')
    hashed_password = ph.hash_password(password)
        
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(""" SELECT player_id, username from Player where username = %s AND password = %s LIMIT 1""", (username, hashed_password))
    
    row = cursor.fetchone()
    print(row)
    valid = row is not None

    if valid:
        player_id = row[0]
        username = row[1]
        cursor.execute(
        "UPDATE Player SET last_login_time = NOW() WHERE username = %s",
        (username,)
        )
        conn.commit()

        session['player_id'] = player_id
        session['username'] = username
        return redirect(url_for('show_matchmaking'))

    
    cursor.close()
    conn.close()
    return jsonify({"status":"invalid"}), 401

@app.route('/newuser')
def show_newuser():
    return render_template('newuser.html')

@app.route('/api/create_account', methods=['POST'])
def create_account():
    data = request.json
    ph = password_handler()
    
    username = data.get('username')
    password = data.get('password')
    
    if not ph.valid_password(password):
        return jsonify({"status":"error", "message":"invalid password bypassed html"}), 400

    hashed_password = ph.hash_password(password)

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(""" 
            INSERT INTO Player (username, password, created_time) 
            VALUES (%s, %s, NOW())
        """, (username, hashed_password))
        conn.commit()

    except IntegrityError:
        cursor.close()
        conn.close()
        return jsonify({"status":"exists"}), 409

    cursor.close()
    conn.close()
    return jsonify({"status":"success"}), 201

@app.route('/account')
def show_account_information():
    if not logged_in():
        return redirect_to_login()

    return render_template('account.html')

@app.route('/api/account', methods=['GET'])
def display_current_user():
    if not logged_in():
        return jsonify({'logged_in':False}), 200

    return jsonify({"logged_in":True, "player_id":session["player_id"], "username":session["username"]})

@app.route('/api/delete_account',methods=['POST'])
def delete_account():
    player_id = session['player_id']
    
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM Player WHERE player_id = %s", (player_id,))
    conn.commit()
    session.clear()
    cursor.close()
    conn.close()

    return jsonify({"status":"success"}), 200

@app.route('/api/change_password', methods=['POST'])
def change_password():

    data = request.json
    ph = password_handler()
    
    new_password = data.get('password')

    if not new_password:
        return jsonify({
            "status": "error",
            "message": "Password is required."
        }), 400

    if not ph.valid_password(new_password):
        return jsonify({
            "status": "error",
            "message": "Password does not meet requirements."
        }), 400

    hashed_new_password = ph.hash_password(new_password)
    player_id = session.get('player_id')

    conn = get_db_connection()
    
    cursor = conn.cursor()

    cursor.execute("""UPDATE Player SET password = %s WHERE player_id = %s""", (hashed_new_password, player_id))
    conn.commit()
    
    cursor.close()
    conn.close()

    return jsonify({"status": "success"}, {"message":"password changed successfully,"}), 200

@app.route('/api/change_username', methods=['POST'])
def change_username():
    data = request.json
    new_username = data.get('username')

    if not new_username:
        return jsonify({"status":"error", "message":"Username is required."}),400

    player_id = session.get('player_id')

    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""UPDATE Player SET username = %s WHERE player_id = %s """, (new_username, player_id))
        conn.commit()

        session['username'] = new_username
    
    except IntegrityError:
        conn.rollback()
        return jsonify({"status":"error", "message": "Username already exists"}), 409

    cursor.close()
    conn.close()

    return jsonify({"status":"success", "message":"Username changed successfully."}), 200

@app.route('/api/logout', methods=["POST"])
def logout():
    session.clear()
    return jsonify({"status":"success"}), 200

    


@app.route('/leaderboard')
def show_leaderboard():
    if not logged_in():
        return redirect_to_login()

    return render_template('leaderboard.html')

@app.route('/matchmaking')
def show_matchmaking():
    if not logged_in():
        return redirect_to_login()

    return render_template('matchmaking.html')

def _query_leaderboard_rows(cursor, where_username_like):
    """
    All registered players, one row each. Wins/losses and win% come from completed Game rows
    (same team/winner rules as the DB trigger) — not from Stats sums, so duplicate Player_Stats
    links or out-of-sync Stats cannot skew win rate.
    """
    where_sql = "WHERE p.username LIKE %s" if where_username_like is not None else ""
    params = (f"%{where_username_like}%",) if where_username_like is not None else ()
    query = f"""
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
                            CASE
                                WHEN gp.seat_position IN (1, 3) THEN 1
                                ELSE 2
                            END
                        ) = g.winning_team_number
                        THEN 1
                        ELSE 0
                    END
                ) AS wins,
                SUM(
                    CASE
                        WHEN (
                            CASE
                                WHEN gp.seat_position IN (1, 3) THEN 1
                                ELSE 2
                            END
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
        {where_sql}
    ) t
    ORDER BY `rank` ASC
    """
    cursor.execute(query, params)


@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    search_query = (request.args.get("search") or "").strip()
    conn = get_db_connection()
    
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        if search_query:
            _query_leaderboard_rows(cursor, search_query)
        else:
            _query_leaderboard_rows(cursor, None)
        results = cursor.fetchall()
    finally:
        cursor.close()
        conn.close()

    return jsonify(results)

@app.route('/api/open_games', methods=['GET'])
def get_open_games():
    if not logged_in():
        return jsonify({"error": "Not logged in"}), 401

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT
            g.game_id,
            g.started_time,
            GROUP_CONCAT(gp.player_id ORDER BY gp.player_id) AS players,
            COALESCE(SUM(CASE WHEN gp.seat_position IN (1, 3) THEN 1 ELSE 0 END), 0) AS team1_count,
            COALESCE(SUM(CASE WHEN gp.seat_position IN (2, 4) THEN 1 ELSE 0 END), 0) AS team2_count,
            COALESCE(COUNT(gp.player_id), 0) AS player_count
        FROM Game g
        LEFT JOIN Game_Player gp ON g.game_id = gp.game_id
        WHERE g.status = 'active'
          AND NOT EXISTS (SELECT 1 FROM Team t WHERE t.game_id = g.game_id)
        GROUP BY g.game_id, g.started_time
    """)
    results = cursor.fetchall()

    my_id = str(session["player_id"])
    for r in results:
        if r.get("started_time"):
            r["started_time"] = r["started_time"].isoformat()
        for k in ("team1_count", "team2_count", "player_count"):
            if r.get(k) is not None:
                r[k] = int(r[k])
        players = r.get("players")
        ids = players.split(",") if players else []
        r["in_this_lobby"] = my_id in ids

    cursor.close()
    conn.close()
    return jsonify(results)

@app.route('/api/create_game', methods=['POST'])
def create_game():
    if not logged_in():
        return jsonify({"status": "error", "message": "Not logged in"}), 401

    player_id = session["player_id"]

    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT gp.game_id FROM Game_Player gp 
        JOIN Game g ON gp.game_id = g.game_id 
        WHERE gp.player_id = %s AND g.status = 'active'
    """, (player_id,))
    
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return jsonify({"status": "error", "message": "You are already in an active game!"})
        
    cursor.execute(
        "INSERT INTO Game (started_time, status, target_score) VALUES (NOW(), 'active', 150)"
    )
    new_game_id = cursor.lastrowid
    
    cursor.execute(
        "INSERT INTO Game_Player (game_id, player_id, seat_position) VALUES (%s, %s, 1)",
        (new_game_id, player_id)
    )
    
    conn.commit()
    cursor.close()
    conn.close()
    
    return jsonify({"status": "success", "game_id": new_game_id}), 201

@app.route('/api/join_game', methods=['POST'])
def join_game():
    if not logged_in():
        return jsonify({"status": "error", "message": "Not logged in"}), 401

    data = request.json or {}
    game_id = data.get("game_id")
    player_id = session["player_id"]
    team_number = data.get("team_number")

    try:
        team_number = int(team_number)
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "team_number must be 1 or 2"}), 400

    if team_number not in (1, 2):
        return jsonify({"status": "error", "message": "team_number must be 1 or 2"}), 400

    if game_id is None:
        return jsonify({"status": "error", "message": "game_id is required"}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "Database connection failed"}), 500

    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT gp.game_id FROM Game_Player gp
            JOIN Game g ON gp.game_id = g.game_id
            WHERE gp.player_id = %s AND g.status = 'active'
        """, (player_id,))

        if cursor.fetchone():
            return jsonify({"status": "error", "message": "You are already in an active game!"})

        cursor.execute(
            "SELECT status FROM Game WHERE game_id = %s",
            (game_id,),
        )
        row = cursor.fetchone()
        if not row or row[0] != "active":
            return jsonify({"status": "error", "message": "This lobby is not available."}), 400

        cursor.execute(
            "SELECT COUNT(*) FROM Team WHERE game_id = %s",
            (game_id,),
        )
        if cursor.fetchone()[0] > 0:
            return jsonify(
                {"status": "error", "message": "This game has already started."}
            ), 400

        team_seats = (1, 3) if team_number == 1 else (2, 4)

        cursor.execute(
            "SELECT seat_position FROM Game_Player WHERE game_id = %s",
            (game_id,),
        )
        taken_seats = {row[0] for row in cursor.fetchall()}

        available_seat = None
        for seat in team_seats:
            if seat not in taken_seats:
                available_seat = seat
                break

        if not available_seat:
            return jsonify(
                {"status": "error", "message": f"Team {team_number} is full (2/2)."}
            ), 400

        cursor.execute(
            "INSERT INTO Game_Player (game_id, player_id, seat_position) VALUES (%s, %s, %s)",
            (game_id, player_id, available_seat),
        )
        conn.commit()
        return jsonify({
            "message": f"Joined team {team_number} (seat {available_seat}).",
            "status": "success",
        })

    except IntegrityError:
        conn.rollback()
        return jsonify({"message": "A database error occurred.", "status": "error"})
    finally:
        cursor.close()
        conn.close()

@app.route('/api/my_match', methods=['GET'])
def get_my_match():
    if not logged_in():
        return jsonify({"error": "Not logged in"}), 401

    player_id = session["player_id"]
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT
            g.game_id,
            g.status,
            (SELECT COUNT(*) FROM Team t WHERE t.game_id = g.game_id) AS team_count
        FROM Game_Player gp
        JOIN Game g ON g.game_id = gp.game_id
        WHERE gp.player_id = %s AND g.status = 'active'
        ORDER BY g.game_id DESC
        LIMIT 1
    """, (player_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row:
        return jsonify({"game_id": None, "status": None, "at_table": False})
    team_count = int(row["team_count"] or 0)
    at_table = team_count >= 2
    return jsonify({
        "game_id": int(row["game_id"]),
        "status": row["status"],
        "at_table": at_table,
    })

@app.route('/api/start_game', methods=['POST'])
def start_game():
    if not logged_in():
        return jsonify({"status": "error", "message": "Not logged in"}), 401

    data = request.json or {}
    try:
        game_id = int(data.get("game_id"))
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "game_id is required"}), 400

    player_id = session["player_id"]
    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "Database connection failed"}), 500

    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT status FROM Game WHERE game_id = %s",
            (game_id,),
        )
        grow = cursor.fetchone()
        if not grow:
            return jsonify({"status": "error", "message": "Game not found."}), 404

        game_status = grow[0]
        cursor.execute(
            "SELECT 1 FROM Game_Player WHERE game_id = %s AND player_id = %s",
            (game_id, player_id),
        )
        if not cursor.fetchone():
            return jsonify(
                {"status": "error", "message": "You are not in this lobby."}
            ), 403

        cursor.execute(
            "SELECT COUNT(*) FROM Team WHERE game_id = %s",
            (game_id,),
        )
        if cursor.fetchone()[0] >= 2:
            return jsonify({
                "status": "success",
                "message": "Game already started.",
                "game_id": game_id,
            })

        if game_status != "active":
            return jsonify(
                {"status": "error", "message": "This game cannot be started."}
            ), 400

        cursor.execute(
            "SELECT COUNT(*) FROM Game_Player WHERE game_id = %s",
            (game_id,),
        )
        if cursor.fetchone()[0] != 4:
            return jsonify(
                {
                    "status": "error",
                    "message": "All 4 players must join before the game can start.",
                }
            ), 400

        cursor.execute(
            "INSERT INTO Team (game_id, team_number, score) VALUES (%s, 1, 0), (%s, 2, 0)",
            (game_id, game_id),
        )
        cursor.execute(
            "UPDATE Game SET deal_seed = FLOOR(RAND() * 4294967295) WHERE game_id = %s AND deal_seed IS NULL",
            (game_id,),
        )
        conn.commit()
        return jsonify({
            "status": "success",
            "message": "Game started.",
            "game_id": game_id,
        })
    except IntegrityError:
        conn.rollback()
        cursor.execute(
            "SELECT COUNT(*) FROM Team WHERE game_id = %s",
            (game_id,),
        )
        if cursor.fetchone()[0] >= 2:
            return jsonify({
                "status": "success",
                "message": "Game already started.",
                "game_id": game_id,
            })
        return jsonify({"message": "A database error occurred.", "status": "error"})
    finally:
        cursor.close()
        conn.close()

@app.route('/play/<int:game_id>')
def play_game_screen(game_id):
    if not logged_in():
        return redirect_to_login()

    player_id = session["player_id"]
    conn = get_db_connection()
    if not conn:
        return render_template("play.html", game_id=game_id, error="Database unavailable"), 500

    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT g.status, gp.seat_position
        FROM Game g
        JOIN Game_Player gp ON gp.game_id = g.game_id AND gp.player_id = %s
        WHERE g.game_id = %s
        """,
        (player_id, game_id),
    )
    row = cursor.fetchone()
    if not row:
        cursor.close()
        conn.close()
        return redirect(url_for("show_matchmaking"))

    cursor.execute(
        "SELECT COUNT(*) AS team_count FROM Team WHERE game_id = %s",
        (game_id,),
    )
    trow = cursor.fetchone()
    team_n = int((trow.get("team_count") if trow else 0) or 0)
    cursor.close()
    conn.close()

    if row["status"] == "completed":
        return redirect(url_for("show_match_summary", game_id=game_id))
    if row["status"] == "active" and team_n < 2:
        return redirect(url_for("show_matchmaking"))

    return render_template("play.html", game_id=game_id, error=None)


@app.route('/api/match/<int:game_id>/moves', methods=['GET'])
def list_match_moves(game_id):
    if not logged_in():
        return jsonify({"status": "error", "message": "Not logged in"}), 401

    try:
        since = int(request.args.get('since', '0'))
    except (TypeError, ValueError):
        since = 0

    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "Database connection failed"}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT 1 FROM Game_Player
            WHERE game_id = %s AND player_id = %s
            """,
            (game_id, session["player_id"]),
        )
        if not cursor.fetchone():
            return jsonify(
                {"status": "error", "message": "Not part of this match."}
            ), 403

        cursor.execute(
            """
            SELECT m.move_id, m.order_played, r.round_number, gp.seat_position
            FROM Game_Moves gm
            JOIN Move m ON m.move_id = gm.move_id
            JOIN Round r ON r.round_id = gm.round_id
            JOIN Player_Move pm ON pm.move_id = m.move_id
            JOIN Game_Player gp ON gp.player_id = pm.player_id AND gp.game_id = gm.game_id
            WHERE gm.game_id = %s AND m.move_id > %s
            ORDER BY m.move_id ASC
            """,
            (game_id, since),
        )
        moves = cursor.fetchall()
        for mv in moves:
            cursor.execute(
                """
                SELECT t.tile_name
                FROM Tile_Moved tm
                JOIN Tile t ON t.tile_id = tm.tile_id
                WHERE tm.move_id = %s
                ORDER BY t.tile_id ASC
                """,
                (mv["move_id"],),
            )
            mv["tile_kinds"] = [str(r["tile_name"]).lower() for r in cursor.fetchall()]

        return jsonify({"moves": moves})
    finally:
        cursor.close()
        conn.close()


@app.route('/api/game/<int:game_id>/players', methods=['GET'])
def get_game_players(game_id):
    if not logged_in():
        return jsonify({"status": "error", "message": "Not logged in"}), 401

    player_id = session["player_id"]
    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "Database connection failed"}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT gp.seat_position, p.username, gp.player_id
            FROM Game_Player gp
            JOIN Player p ON p.player_id = gp.player_id
            WHERE gp.game_id = %s
            ORDER BY gp.seat_position
            """,
            (game_id,),
        )
        rows = cursor.fetchall()
        if len(rows) != 4:
            return jsonify(
                {"status": "error", "message": "Match is not full yet."}
            ), 400

        my_seat = None
        for r in rows:
            if int(r["player_id"]) == int(player_id):
                my_seat = int(r["seat_position"])
                break
        if my_seat is None:
            return jsonify(
                {"status": "error", "message": "Not part of this match."}
            ), 403

        cursor.execute(
            "SELECT deal_seed FROM Game WHERE game_id = %s",
            (game_id,),
        )
        seed_row = cursor.fetchone()
        deal_seed = int(seed_row["deal_seed"]) if seed_row and seed_row.get("deal_seed") is not None else None

        return jsonify({
            "players": [
                {"seat": int(r["seat_position"]), "username": r["username"]}
                for r in rows
            ],
            "my_seat": my_seat,
            "deal_seed": deal_seed,
        })
    finally:
        cursor.close()
        conn.close()


def _apply_match_completion_effects(cursor, game_id, winning_team_number):
    """
    When a game is marked completed, update Stats (wins, losses, average) and Player.rating
    the same way as the historical DB trigger, so it works even if triggers are not installed.
    """
    cursor.execute(
        """
        UPDATE Stats s
        JOIN Player_Stats ps ON ps.stats_id = s.stats_id
        JOIN Game_Player gp ON gp.player_id = ps.player_id
        JOIN Team t ON t.game_id = gp.game_id
            AND t.team_number = (CASE WHEN gp.seat_position IN (1, 3) THEN 1 ELSE 2 END)
        SET s.average_score =
            (s.average_score * (s.wins + s.losses) + t.score) / (s.wins + s.losses + 1)
        WHERE gp.game_id = %s
        """,
        (game_id,),
    )
    cursor.execute(
        """
        UPDATE Stats s
        JOIN Player_Stats ps ON ps.stats_id = s.stats_id
        JOIN Game_Player gp ON gp.player_id = ps.player_id
        SET s.wins = s.wins + 1
        WHERE gp.game_id = %s
          AND (CASE WHEN gp.seat_position IN (1, 3) THEN 1 ELSE 2 END) = %s
        """,
        (game_id, winning_team_number),
    )
    cursor.execute(
        """
        UPDATE Stats s
        JOIN Player_Stats ps ON ps.stats_id = s.stats_id
        JOIN Game_Player gp ON gp.player_id = ps.player_id
        SET s.losses = s.losses + 1
        WHERE gp.game_id = %s
          AND (CASE WHEN gp.seat_position IN (1, 3) THEN 1 ELSE 2 END) <> %s
        """,
        (game_id, winning_team_number),
    )
    cursor.execute(
        """
        UPDATE Player p
        JOIN Game_Player gp ON gp.player_id = p.player_id
        SET p.rating = p.rating + 25
        WHERE gp.game_id = %s
          AND (CASE WHEN gp.seat_position IN (1, 3) THEN 1 ELSE 2 END) = %s
        """,
        (game_id, winning_team_number),
    )
    cursor.execute(
        """
        UPDATE Player p
        JOIN Game_Player gp ON gp.player_id = p.player_id
        SET p.rating = GREATEST(p.rating - 25, 0)
        WHERE gp.game_id = %s
          AND (CASE WHEN gp.seat_position IN (1, 3) THEN 1 ELSE 2 END) <> %s
        """,
        (game_id, winning_team_number),
    )


@app.route("/api/match/<int:game_id>/complete", methods=["POST"])
def complete_match(game_id):
    if not logged_in():
        return jsonify({"status": "error", "message": "Not logged in"}), 401

    data = request.get_json(silent=True) or {}
    try:
        team1_score = int(data.get("team1_score", 0))
        team2_score = int(data.get("team2_score", 0))
        winning_team_number = int(data.get("winning_team_number"))
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "Invalid scores or winner."}), 400

    if winning_team_number not in (1, 2):
        return jsonify(
            {"status": "error", "message": "winning_team_number must be 1 or 2."}
        ), 400
    if team1_score < 0 or team2_score < 0:
        return jsonify({"status": "error", "message": "Scores must be non-negative."}), 400

    player_id = session["player_id"]
    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "Database connection failed"}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT g.status
            FROM Game g
            JOIN Game_Player gp ON gp.game_id = g.game_id AND gp.player_id = %s
            WHERE g.game_id = %s
            """,
            (player_id, game_id),
        )
        grow = cursor.fetchone()
        if not grow:
            return jsonify({"status": "error", "message": "Not part of this match."}), 403

        if grow["status"] == "completed":
            return jsonify({"status": "success", "message": "Already recorded.", "game_id": game_id})

        if grow["status"] != "active":
            return jsonify(
                {"status": "error", "message": "This match cannot be completed."}
            ), 400

        cursor.execute(
            "SELECT COUNT(*) AS c FROM Team WHERE game_id = %s",
            (game_id,),
        )
        if int((cursor.fetchone() or {}).get("c") or 0) < 2:
            return jsonify(
                {"status": "error", "message": "Match has not been started on the server."}
            ), 400

        cursor.execute(
            "UPDATE Team SET score = %s WHERE game_id = %s AND team_number = 1",
            (team1_score, game_id),
        )
        cursor.execute(
            "UPDATE Team SET score = %s WHERE game_id = %s AND team_number = 2",
            (team2_score, game_id),
        )
        cursor.execute(
            """
            UPDATE Game
            SET status = 'completed',
                ended_time = NOW(),
                winning_team_number = %s
            WHERE game_id = %s AND status = 'active'
            """,
            (winning_team_number, game_id),
        )
        if cursor.rowcount == 0:
            conn.rollback()
            return jsonify(
                {
                    "status": "error",
                    "message": "Match was already completed or is no longer active.",
                }
            ), 400

        _apply_match_completion_effects(cursor, game_id, winning_team_number)
        conn.commit()
        return jsonify(
            {"status": "success", "message": "Match saved.", "game_id": game_id}
        )
    except IntegrityError:
        conn.rollback()
        return jsonify({"status": "error", "message": "Could not save match."}), 400
    except Error:
        conn.rollback()
        return jsonify({"status": "error", "message": "Database error."}), 500
    finally:
        cursor.close()
        conn.close()

TILE_KIND_TO_NAME = {
    "king": "King",
    "rook": "Rook",
    "bishop": "Bishop",
    "gold": "Gold",
    "silver": "Silver",
    "knight": "Knight",
    "lance": "Lance",
    "pawn": "Pawn",
}


def _get_or_create_round_id(cursor, game_id, round_number):
    cursor.execute(
        """
        SELECT r.round_id
        FROM Round r
        INNER JOIN Games_Rounds gr ON gr.round_id = r.round_id
        WHERE gr.game_id = %s AND r.round_number = %s
        """,
        (game_id, round_number),
    )
    r = cursor.fetchone()
    if r:
        return r[0]
    cursor.execute(
        "INSERT INTO Round (round_number) VALUES (%s)",
        (round_number,),
    )
    rid = cursor.lastrowid
    cursor.execute(
        "INSERT INTO Games_Rounds (game_id, round_id) VALUES (%s, %s)",
        (game_id, rid),
    )
    return rid


def _next_order_in_round(cursor, game_id, round_id):
    cursor.execute(
        """
        SELECT COALESCE(MAX(m.order_played), 0)
        FROM Game_Moves gm
        JOIN Move m ON m.move_id = gm.move_id
        WHERE gm.game_id = %s AND gm.round_id = %s
        """,
        (game_id, round_id),
    )
    mx = cursor.fetchone()[0]
    return int(mx) + 1


def _get_tile_id(cursor, kind: str) -> int:
    name = TILE_KIND_TO_NAME.get((kind or "").lower().strip())
    if not name:
        name = (kind or "").strip().title() or "Pawn"
    cursor.execute("SELECT tile_id FROM Tile WHERE tile_name = %s", (name,))
    row = cursor.fetchone()
    if not row:
        raise ValueError(f"Unknown tile kind: {kind}")
    return int(row[0])


def _insert_tile_moved_row(cursor, move_id: int, t_id: int, line_idx: int) -> None:
    """
    Prefer new schema (line_idx). If that column is missing, insert old shape only.
    Two of the same tile in one play need line_idx; without it, the second insert may fail.
    """
    try:
        cursor.execute(
            "INSERT INTO Tile_Moved (move_id, tile_id, line_idx) VALUES (%s, %s, %s)",
            (move_id, t_id, line_idx),
        )
    except ProgrammingError:
        cursor.execute(
            "INSERT INTO Tile_Moved (move_id, tile_id) VALUES (%s, %s)",
            (move_id, t_id),
        )


@app.route("/api/match/<int:game_id>/moves", methods=["POST"])
def record_match_move(game_id):
    """Persist a single turn from the browser client (same-tabled match)."""
    if not logged_in():
        return jsonify({"status": "error", "message": "Not logged in"}), 401

    player_id = session["player_id"]
    data = request.get_json(silent=True) or {}
    try:
        round_number = int(data.get("round_number"))
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "round_number is required."}), 400
    try:
        seat_position = int(data.get("seat_position"))
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "seat_position is required."}), 400

    if seat_position not in (1, 2, 3, 4):
        return jsonify({"status": "error", "message": "seat_position must be 1–4."}), 400

    tile_kinds = data.get("tile_kinds")
    if tile_kinds is None:
        tile_kinds = []
    if not isinstance(tile_kinds, list):
        return jsonify({"status": "error", "message": "tile_kinds must be a list."}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "Database connection failed"}), 500

    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT status FROM Game WHERE game_id = %s",
            (game_id,),
        )
        gr = cursor.fetchone()
        if not gr or gr[0] != "active":
            return jsonify(
                {
                    "status": "error",
                    "message": "Moves can only be recorded for an in-progress match.",
                }
            ), 400

        cursor.execute(
            """
            SELECT 1 FROM Game_Player
            WHERE game_id = %s AND player_id = %s
            """,
            (game_id, player_id),
        )
        if not cursor.fetchone():
            return jsonify(
                {"status": "error", "message": "Not part of this match."}
            ), 403

        cursor.execute(
            "SELECT COUNT(*) FROM Team WHERE game_id = %s",
            (game_id,),
        )
        if int(cursor.fetchone()[0] or 0) < 2:
            return jsonify(
                {
                    "status": "error",
                    "message": "Match has not been started on the server.",
                }
            ), 400

        cursor.execute(
            """
            SELECT player_id FROM Game_Player
            WHERE game_id = %s AND seat_position = %s
            """,
            (game_id, seat_position),
        )
        move_player_row = cursor.fetchone()
        if not move_player_row:
            return jsonify({"status": "error", "message": "Invalid seat."}), 400
        move_player_id = int(move_player_row[0])

        round_id = _get_or_create_round_id(cursor, game_id, round_number)
        ordn = _next_order_in_round(cursor, game_id, round_id)

        cursor.execute(
            "INSERT INTO Move (order_played, time_stamp) VALUES (%s, NOW())",
            (ordn,),
        )
        move_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO Player_Move (player_id, move_id) VALUES (%s, %s)",
            (move_player_id, move_id),
        )
        for line_idx, k in enumerate(tile_kinds):
            if not k:
                continue
            t_id = _get_tile_id(cursor, str(k))
            _insert_tile_moved_row(cursor, move_id, t_id, line_idx)
        cursor.execute(
            "INSERT INTO Game_Moves (game_id, round_id, move_id) VALUES (%s, %s, %s)",
            (game_id, round_id, move_id),
        )
        cursor.execute(
            "INSERT IGNORE INTO Replay (game_id) VALUES (%s)",
            (game_id,),
        )
        conn.commit()
        return jsonify(
            {
                "status": "success",
                "move_id": move_id,
            }
        )
    except ValueError as e:
        conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 400
    except IntegrityError:
        conn.rollback()
        return jsonify({"status": "error", "message": "Could not record move."}), 400
    except Error:
        conn.rollback()
        return jsonify({"status": "error", "message": "Database error."}), 500
    finally:
        cursor.close()
        conn.close()

@app.route("/api/match/<int:game_id>/abandon", methods=["POST"])
def abandon_match(game_id):
    if not logged_in():
        return jsonify({"status": "error", "message": "Not logged in"}), 401

    player_id = session["player_id"]
    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "Database connection failed"}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            """
            SELECT g.status
            FROM Game g
            JOIN Game_Player gp ON gp.game_id = g.game_id AND gp.player_id = %s
            WHERE g.game_id = %s
            """,
            (player_id, game_id),
        )
        grow = cursor.fetchone()
        if not grow:
            return jsonify({"status": "error", "message": "Not part of this match."}), 403

        if grow["status"] != "active":
            return jsonify(
                {"status": "error", "message": "This match is already finished."}
            ), 400

        cursor.execute(
            """
            UPDATE Game
            SET status = 'cancelled',
                ended_time = NOW(),
                winning_team_number = NULL
            WHERE game_id = %s AND status = 'active'
            """,
            (game_id,),
        )
        conn.commit()
        return jsonify({"status": "success", "message": "Match abandoned.", "game_id": game_id})
    finally:
        cursor.close()
        conn.close()

def _player_ids_set(cursor, g_id):
    cursor.execute(
        "SELECT player_id FROM Game_Player WHERE game_id = %s ORDER BY player_id",
        (g_id,),
    )
    return {r[0] for r in cursor.fetchall()}


@app.route("/api/match/<int:game_id>/rematch", methods=["POST"])
def rematch_from_completed(game_id):
    """
    After a match is completed, the same four accounts can start a new table game
    (new Game row) without going through the lobby. If someone already created that
    rematch, we return the same new game_id for everyone in the old match.
    """
    if not logged_in():
        return jsonify({"status": "error", "message": "Not logged in"}), 401

    player_id = session["player_id"]
    conn = get_db_connection()
    if not conn:
        return jsonify({"status": "error", "message": "Database connection failed"}), 500

    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT status FROM Game WHERE game_id = %s",
            (game_id,),
        )
        gr = cursor.fetchone()
        if not gr or gr[0] != "completed":
            return jsonify(
                {
                    "status": "error",
                    "message": "Rematch is only available after a finished match is saved.",
                }
            ), 400

        cursor.execute(
            "SELECT 1 FROM Game_Player WHERE game_id = %s AND player_id = %s",
            (game_id, player_id),
        )
        if not cursor.fetchone():
            return jsonify({"status": "error", "message": "Not part of this match."}), 403

        cursor.execute(
            """
            SELECT player_id, seat_position FROM Game_Player
            WHERE game_id = %s ORDER BY seat_position
            """,
            (game_id,),
        )
        seats = cursor.fetchall()
        if len(seats) != 4:
            return jsonify(
                {"status": "error", "message": "Invalid prior match roster."}
            ), 400

        roster = _player_ids_set(cursor, game_id)

        cursor.execute(
            """
            SELECT gp.game_id
            FROM Game_Player gp
            JOIN Game g ON g.game_id = gp.game_id
            WHERE gp.player_id = %s AND g.status = 'active'
            LIMIT 1
            """,
            (player_id,),
        )
        active_row = cursor.fetchone()
        if active_row:
            other_id = active_row[0]
            other = _player_ids_set(cursor, other_id)
            if other == roster and len(other) == 4:
                return jsonify(
                    {"status": "success", "game_id": other_id, "existing": True}
                )
            return jsonify(
                {
                    "status": "error",
                    "message": "You are already in a different match. Finish or leave that one first.",
                }
            ), 400

        cursor.execute("SELECT game_id FROM Game WHERE status = 'active'")
        for (candidate_id,) in cursor.fetchall():
            if _player_ids_set(cursor, candidate_id) == roster:
                return jsonify(
                    {"status": "success", "game_id": candidate_id, "existing": True}
                )

        cursor.execute(
            "INSERT INTO Game (started_time, status, target_score) VALUES (NOW(), 'active', 150)"
        )
        new_id = cursor.lastrowid
        for pid, seat in seats:
            cursor.execute(
                "INSERT INTO Game_Player (game_id, player_id, seat_position) VALUES (%s, %s, %s)",
                (new_id, pid, seat),
            )
        cursor.execute(
            "INSERT INTO Team (game_id, team_number, score) VALUES (%s, 1, 0), (%s, 2, 0)",
            (new_id, new_id),
        )
        conn.commit()
        return jsonify({"status": "success", "game_id": new_id, "existing": False})
    except IntegrityError:
        conn.rollback()
        return jsonify({"status": "error", "message": "Could not create rematch."}), 400
    except Error:
        conn.rollback()
        return jsonify({"status": "error", "message": "Database error."}), 500
    finally:
        cursor.close()
        conn.close()

@app.route('/api/past_matches', methods=['GET'])
def get_past_matches():
    if not logged_in():
        return jsonify({"error": "Not logged in"}), 401

    pid = session['player_id']

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            g.game_id,
            g.ended_time,
            g.winning_team_number,
            gp.seat_position,
            CASE WHEN gp.seat_position IN (1,3) THEN 1 ELSE 2 END AS my_team_number,
            t_mine.score AS my_score,
            t_opp.score AS opp_score,
            CASE
                WHEN g.winning_team_number =
                    (CASE WHEN gp.seat_position IN (1,3) THEN 1 ELSE 2 END)
                THEN 'Win' ELSE 'Loss'
            END AS result
        FROM Game g
        JOIN Game_Player gp ON g.game_id = gp.game_id
        JOIN Team t_mine ON t_mine.game_id = g.game_id
            AND t_mine.team_number = (CASE WHEN gp.seat_position IN (1,3) THEN 1 ELSE 2 END)
        JOIN Team t_opp ON t_opp.game_id = g.game_id
            AND t_opp.team_number = (CASE WHEN gp.seat_position IN (1,3) THEN 2 ELSE 1 END)
        WHERE gp.player_id = %s AND g.status = 'completed'
        ORDER BY g.ended_time DESC
    """, (pid,))

    matches = cursor.fetchall()

    for m in matches:
        cursor.execute("""
            SELECT p.username, gp.seat_position,
                   CASE WHEN gp.seat_position IN (1,3) THEN 1 ELSE 2 END AS team_number
            FROM Game_Player gp
            JOIN Player p ON p.player_id = gp.player_id
            WHERE gp.game_id = %s AND gp.player_id != %s
            ORDER BY gp.seat_position
        """, (m['game_id'], pid))
        others = cursor.fetchall()

        m['teammate'] = None
        m['opponents'] = []
        for o in others:
            if o['team_number'] == m['my_team_number']:
                m['teammate'] = o
            else:
                m['opponents'].append(o)

        if m['ended_time']:
            m['ended_time'] = m['ended_time'].isoformat()

    cursor.close()
    conn.close()
    return jsonify(matches)

@app.route('/match/<int:game_id>/summary')
def show_match_summary(game_id):
    if not logged_in():
        return redirect_to_login()
    return render_template('match_summary.html', game_id=game_id)

@app.route('/api/match/<int:game_id>/summary', methods=['GET'])
def get_match_summary(game_id):
    if not logged_in():
        return jsonify({"error": "Not logged in"}), 401

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT game_id, started_time, ended_time, status,
               target_score, winning_team_number
        FROM Game
        WHERE game_id = %s
    """, (game_id,))
    game = cursor.fetchone()

    if not game:
        cursor.close()
        conn.close()
        return jsonify({"error": "Match not found"}), 404

    if game.get('started_time'):
        game['started_time'] = game['started_time'].isoformat()
    if game.get('ended_time'):
        game['ended_time'] = game['ended_time'].isoformat()

    cursor.execute("""
        SELECT team_number, score
        FROM Team
        WHERE game_id = %s
        ORDER BY team_number
    """, (game_id,))
    teams = cursor.fetchall()

    cursor.execute("""
        SELECT
            p.player_id, p.username, gp.seat_position,
            CASE WHEN gp.seat_position IN (1,3) THEN 1 ELSE 2 END AS team_number
        FROM Game_Player gp
        JOIN Player p ON p.player_id = gp.player_id
        WHERE gp.game_id = %s
        ORDER BY team_number, gp.seat_position
    """, (game_id,))
    players = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify({
        "game": game,
        "teams": teams,
        "players": players
    })

@app.route('/match/<int:game_id>/replay')
def show_match_replay(game_id):
    if not logged_in():
        return redirect_to_login()
    return render_template('replay.html', game_id=game_id)

def _fetch_tiles_for_replay_move(cursor, move_id):
    """
    Load tiles for one move. We only ORDER BY t.tile_id so this works on DBs that
    have not run the line_idx migration; when line_idx exists, order may not match
    play order for two identical pieces in the same play (rare).
    """
    cursor.execute(
        """
        SELECT t.tile_id, t.tile_name, t.score
        FROM Tile_Moved tm
        JOIN Tile t ON t.tile_id = tm.tile_id
        WHERE tm.move_id = %s
        ORDER BY t.tile_id
        """,
        (move_id,),
    )
    rows = cursor.fetchall()
    out = []
    for r in rows:
        s = r.get("score")
        if s is not None and hasattr(s, "as_integer_ratio"):
            s = int(s) if s == int(s) else float(s)
        out.append(
            {
                "tile_id": int(r.get("tile_id", 0)),
                "tile_name": r.get("tile_name") or "",
                "score": s,
            }
        )
    return out


@app.route('/api/match/<int:game_id>/replay', methods=['GET'])
def get_match_replay(game_id):
    if not logged_in():
        return jsonify({"error": "Not logged in"}), 401

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT game_id, started_time, ended_time, status,
               target_score, winning_team_number
        FROM Game
        WHERE game_id = %s
    """, (game_id,))
    game = cursor.fetchone()

    if not game:
        cursor.close()
        conn.close()
        return jsonify({"error": "Match not found"}), 404

    if game.get('started_time'):
        game['started_time'] = game['started_time'].isoformat()
    if game.get('ended_time'):
        game['ended_time'] = game['ended_time'].isoformat()

    cursor.execute("""
        SELECT
            m.move_id,
            r.round_number,
            m.order_played,
            m.time_stamp,
            p.username,
            gp.seat_position
        FROM Game_Moves gm
        JOIN Move m ON gm.move_id = m.move_id
        JOIN Round r ON gm.round_id = r.round_id
        JOIN Player_Move pm ON pm.move_id = m.move_id
        JOIN Player p ON p.player_id = pm.player_id
        JOIN Game_Player gp ON gp.game_id = gm.game_id AND gp.player_id = pm.player_id
        WHERE gm.game_id = %s
        ORDER BY r.round_number, m.order_played
    """, (game_id,))
    moves = cursor.fetchall()

    for mv in moves:
        if mv.get('time_stamp'):
            mv['time_stamp'] = mv['time_stamp'].isoformat()
        mid = mv.get("move_id")
        if mid is not None:
            mv["tiles"] = _fetch_tiles_for_replay_move(cursor, mid)
        else:
            mv["tiles"] = []

    cursor.close()
    conn.close()

    return jsonify({
        "game": game,
        "moves": moves
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
