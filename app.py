import os
import mysql.connector

from classes.password_handler import password_handler

from mysql.connector import Error
from mysql.connector.errors import IntegrityError
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
        cursor.execute(""" INSERT INTO Player (username, password) VALUES (%s, %s)""", (username, hashed_password))
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

@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    search_query = request.args.get('search', '')
    conn = get_db_connection()
    
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
        
    cursor = conn.cursor(dictionary=True)
    
    if search_query:
        query = "SELECT * FROM Lobby WHERE username LIKE %s ORDER BY `rank` ASC"
        cursor.execute(query, (f"%{search_query}%",))
    else:
        query = "SELECT * FROM Lobby ORDER BY `rank` ASC LIMIT 50"
        cursor.execute(query)
        
    results = cursor.fetchall()
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
        cursor.execute("""
            SELECT t.tile_id, t.tile_name, t.score
            FROM Tile_Moved tm
            JOIN Tile t ON t.tile_id = tm.tile_id
            WHERE tm.move_id = %s
        """, (mv['move_id'],))
        mv['tiles'] = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify({
        "game": game,
        "moves": moves
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
