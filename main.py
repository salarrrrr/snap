from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime, timedelta
import sqlite3

app = FastAPI()

# ================= DATABASE =================
conn = sqlite3.connect("db.sqlite", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS licenses (
    license_key TEXT PRIMARY KEY,
    hwid TEXT,
    activated_at TEXT,
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

# ================= MODELS =================
class Verify(BaseModel):
    license_key: str
    hwid: str

class CreateLicense(BaseModel):
    license_key: str
    secret: str

ADMIN_SECRET = "DEVBAND-SECRET-123"

def now():
    return datetime.utcnow()

# ================= VERIFY =================
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

    # أول تفعيل (هنا تبدأ 30 يوم)
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

    # انتهت المدة
    if now_time > datetime.fromisoformat(expires_at):
        return {"status": "expired"}

    return {
        "status": "ok",
        "expires_at": expires_at,
        "first_activation": False
    }

# ================= USAGE LIMIT =================
@app.post("/use")
def use(req: Verify):
    cur.execute("SELECT * FROM usage WHERE license_key=?", (req.license_key,))
    u = cur.fetchone()
    now_time = now()

    if not u:
        cur.execute(
            "INSERT INTO usage VALUES (?, ?, ?)",
            (req.license_key, 1, None)
        )
        conn.commit()
        return {"status": "allowed", "remaining": 4}

    _, count, locked_until = u

    if locked_until and now_time < datetime.fromisoformat(locked_until):
        seconds = int((datetime.fromisoformat(locked_until) - now_time).total_seconds())
        return {"status": "locked", "seconds_left": seconds}

    if count >= 5:
        lock_time = now_time + timedelta(hours=10)
        cur.execute(
            "UPDATE usage SET locked_until=? WHERE license_key=?",
            (lock_time.isoformat(), req.license_key)
        )
        conn.commit()
        return {"status": "locked", "seconds_left": 10 * 3600}

    cur.execute(
        "UPDATE usage SET reports_count=? WHERE license_key=?",
        (count + 1, req.license_key)
    )
    conn.commit()
    return {"status": "allowed", "remaining": 5 - (count + 1)}

# ================= ADMIN (NO SHELL) =================
@app.post("/admin/create")
def create_license(data: CreateLicense):
    if data.secret != ADMIN_SECRET:
        return {"status": "forbidden"}

    cur.execute(
        "INSERT OR IGNORE INTO licenses VALUES (?, ?, ?, ?, ?)",
        (data.license_key, None, None, None, 1)
    )
    conn.commit()
    return {"status": "created"}
