# Goita Online

A web app for playing Goita, a 4-player Japanese tile game.

## What it does

Four players sign up, jump into a lobby, and play a real-time match against each other from their own browsers. Past matches are saved so you can come back and step through a replay of any game you played.

Features:
- Account signup and login
- Matchmaking lobby (create or join open games)
- Leaderboard ranked by wins and rating
- Live multiplayer gameplay across 4 browsers
- Match summary and step-through replay for any completed game
- Stats tracking (wins, losses, average score, rating)

## Stack

- **Backend:** Flask (Python)
- **Database:** MySQL (via XAMPP for local dev)
- **Frontend:** React + TypeScript + Vite
- **Auth:** Flask sessions with hashed passwords

## How to run it locally

You will need Python 3, Node.js, and MySQL (XAMPP works).

### 1. Set up the database

Start your MySQL server (XAMPP control panel: start Apache and MySQL).

Open phpMyAdmin and create a database called `goita`. Then run the SQL files in this order:
1. `sql/schema.sql`
2. `sql/seed.sql`
3. `sql/procedures.sql`
4. `sql/triggers.sql`

### 2. Set up the Python backend

From the project root:

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Make a `.env` file in the project root with these values:

```
FLASK_SECRET_KEY=any_random_string_here
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=
DB_NAME=goita
```

### 3. Build the frontend

The React app gets built into Flask's static folder so Flask can serve it.

```
cd frontend
npm install
npm run build
cd ..
```

### 4. Run Flask

```
python main.py
```

Open `http://127.0.0.1:5000` in your browser. You should see the login page.

## How to test multiplayer

Open 4 separate browser windows (Chrome regular + Chrome incognito + Firefox + Edge, or any combo of 4). Log in as a different account in each. From one of them, create a game in the matchmaking page. From the other 3, join that game (2 on each team). Once the lobby is full (4/4), one player clicks Start Game and everyone gets sent to the gameplay screen.

## Project structure

```
main.py                    Flask backend (all routes and DB logic)
app.yaml                   GCP App Engine deployment config
classes/                   Helper classes (password hashing)
sql/                       Schema, seed data, procedures, triggers
templates/                 Flask HTML templates
static/                    CSS and built React app
frontend/                  React + Vite source for the gameplay UI
report/                    Course report sections
```

## Deploying to GCP

The project includes an `app.yaml` for Google App Engine Standard (Python 3.12). It points at a Cloud SQL instance instead of a local MySQL server.

Before deploying, update the credentials in `app.yaml` (or use Secret Manager) and make sure your Cloud SQL instance is running. Then from the project root:

```
gcloud app deploy
```

The frontend must be built first (`npm run build` inside `frontend/`) since Flask serves the compiled React bundle from `static/`.

## Limitations and Notes

- The deal seed approach means each client computes all 4 hands locally. The UI hides opponent hands but a determined cheater could inspect browser state to see them. A production version would deal server-side per seat.
- This was built for CS 4750 (Database Systems), so it focuses more on demonstrating SQL features (window functions, triggers, stored procedures, complex joins) than on a production styled app.
