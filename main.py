from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime, timedelta
import sqlite3

app = FastAPI()

conn = sqlite3.connect("db.sqlite", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS licenses (
    license_key TEXT PRIMARY KEY,
    hwid TEXT,
    expires_at TEXT,
    is_active INTEGER
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS usage (
    license_key TEXT PRIMARY KEY,
    reports_count INTEGER,
    locked_until TEXT
)
""")
conn.commit()

class Verify(BaseModel):
    license_key: str
    hwid: str

def now():
    return datetime.utcnow()

@app.post("/verify")
def verify(req: Verify):
    cur.execute("SELECT * FROM licenses WHERE license_key=?", (req.license_key,))
    row = cur.fetchone()
    if not row:
        return {"status": "invalid"}

    key, hwid, expires_at, is_active = row
    if not is_active:
        return {"status": "disabled"}

    if now() > datetime.fromisoformat(expires_at):
        return {"status": "expired"}

    if hwid and hwid != req.hwid:
        return {"status": "used"}

    if not hwid:
        cur.execute(
            "UPDATE licenses SET hwid=? WHERE license_key=?",
            (req.hwid, req.license_key)
        )
        conn.commit()

    cur.execute("SELECT * FROM usage WHERE license_key=?", (req.license_key,))
    u = cur.fetchone()
    if u and u[2] and now() < datetime.fromisoformat(u[2]):
        seconds = int((datetime.fromisoformat(u[2]) - now()).total_seconds())
        return {"status": "locked", "seconds_left": seconds}

    return {"status": "ok"}

@app.post("/use")
def use(req: Verify):
    cur.execute("SELECT * FROM usage WHERE license_key=?", (req.license_key,))
    u = cur.fetchone()

    if not u:
        cur.execute(
            "INSERT INTO usage VALUES (?, ?, ?)",
            (req.license_key, 1, None)
        )
        conn.commit()
        return {"status": "allowed", "remaining": 4}

    _, count, locked_until = u

    if locked_until and now() < datetime.fromisoformat(locked_until):
        seconds = int((datetime.fromisoformat(locked_until) - now()).total_seconds())
        return {"status": "locked", "seconds_left": seconds}

    if count >= 5:
        lock = now() + timedelta(hours=10)
        cur.execute(
            "UPDATE usage SET locked_until=? WHERE license_key=?",
            (lock.isoformat(), req.license_key)
        )
        conn.commit()
        return {"status": "locked", "seconds_left": 10 * 3600}

    cur.execute(
        "UPDATE usage SET reports_count=? WHERE license_key=?",
        (count + 1, req.license_key)
    )
    conn.commit()
    return {"status": "allowed", "remaining": 5 - (count + 1)}
