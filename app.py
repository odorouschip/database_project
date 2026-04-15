import os
from flask import Flask, request, jsonify, render_template
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

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

@app.route('/')
def home():
    return "The Goita Online Backend is running successfully!"

@app.route('/leaderboard')
def show_leaderboard():
    return render_template('leaderboard.html')

@app.route('/matchmaking')
def show_matchmaking():
    return render_template('matchmaking.html')

@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    search_query = request.args.get('search', '')
    conn = get_db_connection()
    
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500
        
    cursor = conn.cursor(dictionary=True)
    
    if search_query:
        # Prevent SQL injection by parameterizing the search string
        query = "SELECT * FROM Lobby WHERE username LIKE %s ORDER BY `rank` DESC"
        cursor.execute(query, (f"%{search_query}%",))
    else:
        # Added backticks around rank
        query = "SELECT * FROM Lobby ORDER BY `rank` DESC LIMIT 50"
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
    # Fetch games that are waiting for players
    # Replace your old SELECT statement with this one:
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
    
    # 1. The Bouncer
    cursor.execute("""
        SELECT gp.game_id FROM Game_Player gp 
        JOIN Game g ON gp.game_id = g.game_id 
        WHERE gp.player_id = %s AND g.status = 'active'
    """, (player_id,))
    
    if cursor.fetchone():
        return jsonify({"status": "error", "message": "You are already in an active game!"})
        
    # 2. Create the lobby
    cursor.execute(
        "INSERT INTO Game (started_time, status, target_score) VALUES (NOW(), 'active', 150)"
    )
    new_game_id = cursor.lastrowid
    
    # 3. Add the creator to seat 1
    cursor.execute(
        "INSERT INTO Game_Player (game_id, player_id, seat_position) VALUES (%s, %s, 1)",
        (new_game_id, player_id)
    )
    
    conn.commit()
    cursor.close()
    conn.close()
    
    # Return a formatted success status so the frontend understands it
    return jsonify({"status": "success", "game_id": new_game_id}), 201

@app.route('/api/join_game', methods=['POST'])
def join_game():
    data = request.json
    game_id = data.get('game_id')
    player_id = data.get('player_id')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. The Bouncer (Check if they are already in a game)
    cursor.execute("""
        SELECT gp.game_id FROM Game_Player gp 
        JOIN Game g ON gp.game_id = g.game_id 
        WHERE gp.player_id = %s AND g.status = 'active'
    """, (player_id,))
    
    if cursor.fetchone():
        return jsonify({"status": "error", "message": "You are already in an active game!"})

    try:
        # 2. Find the next available seat
        cursor.execute("SELECT seat_position FROM Game_Player WHERE game_id = %s", (game_id,))
        # Fetch the results and extract just the seat numbers into a list
        taken_seats = [row[0] for row in cursor.fetchall()]
        
        available_seat = None
        for seat in [2, 3, 4]:
            if seat not in taken_seats:
                available_seat = seat
                break
                
        # If seats 2, 3, and 4 are all in the taken_seats list, the room is full
        if not available_seat:
            return jsonify({"status": "error", "message": "This lobby is full!"})

        # 3. Put the player in the calculated empty seat
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

if __name__ == '__main__':
    app.run(debug=True, port=5000)