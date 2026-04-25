"""Smoke test: Cloud SQL (or any MySQL) + local Flask API. Run from project root: python scripts/smoke_test.py"""
from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Project root = parent of scripts/
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.chdir(ROOT)

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")


def test_mysql() -> bool:
    import mysql.connector

    try:
        port = int(os.getenv("DB_PORT", "3306"))
    except ValueError:
        port = 3306
    kwargs = {
        "host": (os.getenv("DB_HOST") or "").strip(),
        "port": port,
        "user": (os.getenv("DB_USER") or "").strip(),
        "password": os.getenv("DB_PASSWORD") or "",
        "database": (os.getenv("DB_NAME") or "").strip(),
    }
    ssl_ca = os.getenv("DB_SSL_CA")
    if ssl_ca:
        kwargs["ssl_ca"] = ssl_ca.strip()
    if os.getenv("DB_SSL_DISABLED", "").lower() in ("1", "true", "yes"):
        kwargs["ssl_disabled"] = True

    print("MySQL: connecting to", kwargs["host"], "db=", kwargs["database"], "...")
    conn = mysql.connector.connect(**kwargs)
    cur = conn.cursor()
    cur.execute("SELECT 1")
    one = cur.fetchone()
    cur.close()
    conn.close()
    print("MySQL: OK", one)
    return True


def test_http(base: str) -> None:
    url = base.rstrip("/") + "/api/leaderboard"
    print("HTTP GET", url, "...")
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            body = r.read(500)
            print("HTTP:", r.status, body[:200])
    except urllib.error.HTTPError as e:
        print("HTTP error:", e.code, e.read(300))
    except Exception as e:
        print("HTTP failed:", e)


if __name__ == "__main__":
    ok = test_mysql()
    if not ok:
        sys.exit(1)
    base = os.getenv("SMOKE_BASE_URL", "http://127.0.0.1:5000")
    if len(sys.argv) > 1:
        base = sys.argv[1]
    test_http(base)
