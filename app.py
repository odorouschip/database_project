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

    return f"The Goita Online Backend is running successfully! {session['username']} is logged in."


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
        return redirect(url_for('home'))

    
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
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
        
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT g.game_id, g.started_time, GROUP_CONCAT(gp.player_id) as players
        FROM Game g
        LEFT JOIN Game_Player gp ON g.game_id = gp.game_id
        WHERE g.status = 'active'
        GROUP BY g.game_id
    """)
    results = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return jsonify(results)

@app.route('/api/create_game', methods=['POST'])
def create_game():
    data = request.json
    player_id = data.get('player_id') 
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT gp.game_id FROM Game_Player gp 
        JOIN Game g ON gp.game_id = g.game_id 
        WHERE gp.player_id = %s AND g.status = 'active'
    """, (player_id,))
    
    if cursor.fetchone():
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
    data = request.json
    game_id = data.get('game_id')
    player_id = data.get('player_id')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT gp.game_id FROM Game_Player gp 
        JOIN Game g ON gp.game_id = g.game_id 
        WHERE gp.player_id = %s AND g.status = 'active'
    """, (player_id,))
    
    if cursor.fetchone():
        return jsonify({"status": "error", "message": "You are already in an active game!"})

    try:
        cursor.execute("SELECT seat_position FROM Game_Player WHERE game_id = %s", (game_id,))
        taken_seats = [row[0] for row in cursor.fetchall()]
        
        available_seat = None
        for seat in [2, 3, 4]:
            if seat not in taken_seats:
                available_seat = seat
                break
                
        if not available_seat:
            return jsonify({"status": "error", "message": "This lobby is full!"})

        cursor.execute(
            "INSERT INTO Game_Player (game_id, player_id, seat_position) VALUES (%s, %s, %s)",
            (game_id, player_id, available_seat)
        )
        conn.commit()
        response = {"message": f"Successfully joined in Seat {available_seat}!", "status": "success"}
        
    except mysql.connector.IntegrityError:
        conn.rollback()
        response = {"message": "A database error occurred.", "status": "error"}
        
    finally:
        cursor.close()
        conn.close()
        
    return jsonify(response)

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
            SELECT p.username, gp.seat_position
            FROM Game_Player gp
            JOIN Player p ON p.player_id = gp.player_id
            WHERE gp.game_id = %s AND gp.player_id != %s
            ORDER BY gp.seat_position
        """, (m['game_id'], pid))
        m['opponents'] = cursor.fetchall()
        if m['ended_time']:
            m['ended_time'] = m['ended_time'].isoformat()

    cursor.close()
    conn.close()
    return jsonify(matches)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
