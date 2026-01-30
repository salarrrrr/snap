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

    license_key, hwid, activated_at, expires_at, is_active = row

    if not is_active:
        return {"status": "disabled"}

    now_time = now()

    # أول تفعيل
    if not activated_at:
        new_expires = now_time + timedelta(days=30)
        cur.execute("""
            UPDATE licenses
            SET hwid=?, activated_at=?, expires_at=?
            WHERE license_key=?
        """, (
            req.hwid,
            now_time.isoformat(),
            new_expires.isoformat(),
            license_key
        ))
        conn.commit()
        return {
            "status": "ok",
            "expires_at": new_expires.isoformat(),
            "first_activation": True
        }

    # جهاز مختلف
    if hwid != req.hwid:
        return {"status": "used_on_other_device"}

    # منتهي
    if now_time > datetime.fromisoformat(expires_at):
        return {"status": "expired"}

    return {
        "status": "ok",
        "expires_at": expires_at,
        "first_activation": False
    }

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
