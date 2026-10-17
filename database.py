import os
import sqlite3
import requests
from typing import Optional, Dict, Any, List

TURSO_URL = os.environ.get("TURSO_DATABASE_URL", "https://pes-db-hossamfayad.aws-us-east-1.turso.io")
TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN", "eyJhbGciOiJFZERTQSIsInR5cCI6InJ3IiwiaWF0IjoxNzkyMjE1OTQyLCJpZCI6IjAxYTE0ODYzLWM5MDEtNzBhZi1iYWMyLTYyNjNmYzVlMTFiZCIsImtpZCI6Ik9BdWd6LXc2aTU5cFZvYTFRTXJYS25xUERsNEVmOHZtQV8tRVJweHBuOTAiLCJyaWQiOiJkNWU0ODYyYi00NzcxLTQ1OWQtOWE1OS0yY2VkNTNjOTBiZTAifQ.YCVzUQRNc9kDdj5Pgc3jo7EGSqyz-W_h-CdzpO3yWm8b3JlkCB5IcEyWPEwVxX75zjbg6q9k_vrfohcQfhIWBg")

USE_TURSO = bool(TURSO_URL and TURSO_TOKEN)

if TURSO_URL and TURSO_URL.startswith("libsql://"):
    TURSO_URL = TURSO_URL.replace("libsql://", "https://")

if os.environ.get("VERCEL"):
    DB_PATH = "/tmp/fpl_bot.db"
else:
    DB_PATH = os.path.join(os.path.dirname(__file__), "fpl_bot.db")

SUPER_ADMINS = [5575156113]

def _format_arg(val: Any) -> Dict[str, Any]:
    if val is None:
        return {"type": "null"}
    elif isinstance(val, int):
        return {"type": "integer", "value": str(val)}
    elif isinstance(val, float):
        return {"type": "float", "value": val}
    else:
        return {"type": "text", "value": str(val)}

def turso_execute(sql: str, args: list = None) -> List[Dict[str, Any]]:
    if not args:
        args = []
    formatted_args = [_format_arg(a) for a in args]
    
    url = f"{TURSO_URL.rstrip('/')}/v2/pipeline"
    headers = {
        "Authorization": f"Bearer {TURSO_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "requests": [
            {"type": "execute", "stmt": {"sql": sql, "args": formatted_args}},
            {"type": "close"}
        ]
    }
    
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            if results and results[0].get("type") == "ok":
                exec_result = results[0]["response"]["result"]
                cols = [c["name"] for c in exec_result.get("cols", [])]
                out = []
                for row in exec_result.get("rows", []):
                    row_dict = {}
                    for col_name, col_val in zip(cols, row):
                        row_dict[col_name] = col_val.get("value")
                    out.append(row_dict)
                return out
        else:
            print(f"[TursoError] Status {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"[TursoException] {e}")
    return []

def get_sqlite_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    sql1 = """
    CREATE TABLE IF NOT EXISTS fpl_users (
        telegram_id INTEGER PRIMARY KEY,
        team_id INTEGER,
        team_name TEXT DEFAULT '',
        manager_name TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    sql2 = """
    CREATE TABLE IF NOT EXISTS fpl_user_state (
        telegram_id INTEGER PRIMARY KEY,
        prompt_state TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    sql3 = """
    CREATE TABLE IF NOT EXISTS fpl_settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """
    if USE_TURSO:
        turso_execute(sql1)
        turso_execute(sql2)
        turso_execute(sql3)
    else:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute(sql1)
        cursor.execute(sql2)
        cursor.execute(sql3)
        conn.commit()
        conn.close()

MEM_USER_TEAMS: Dict[int, Dict[str, Any]] = {}
MEM_PROMPT_STATES: Dict[int, str] = {}
MEM_SETTINGS: Dict[str, str] = {
    "league_code": "",
    "league_id": "",
    "league_name": "دوري مساعد الفانتسي الرسمي 🏆"
}

def set_bot_setting(key: str, value: str):
    MEM_SETTINGS[key] = str(value)
    try:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO fpl_settings (key, value) VALUES (?, ?)", (key, str(value)))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[SetSettingError] {e}")

def get_bot_setting(key: str, default: str = "") -> str:
    if key in MEM_SETTINGS and MEM_SETTINGS[key]:
        return MEM_SETTINGS[key]
    try:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM fpl_settings WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        if row and row[0]:
            MEM_SETTINGS[key] = row[0]
            return row[0]
    except Exception:
        pass
    return default

def save_user_team(telegram_id: int, team_id: int, team_name: str = "", manager_name: str = ""):
    t_id = int(telegram_id)
    MEM_USER_TEAMS[t_id] = {
        "telegram_id": t_id,
        "team_id": int(team_id),
        "team_name": team_name,
        "manager_name": manager_name
    }
    try:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO fpl_users (telegram_id, team_id, team_name, manager_name, last_active)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (t_id, team_id, team_name, manager_name))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[SQLiteSaveError] {e}")

def get_user_team(telegram_id: int) -> Optional[Dict[str, Any]]:
    t_id = int(telegram_id)
    if t_id in MEM_USER_TEAMS:
        return MEM_USER_TEAMS[t_id]
    try:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM fpl_users WHERE telegram_id = ?", (t_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            res = dict(row)
            MEM_USER_TEAMS[t_id] = res
            return res
    except Exception as e:
        print(f"[SQLiteGetError] {e}")
    return None

def set_prompt_state(telegram_id: int, state: str):
    t_id = int(telegram_id)
    MEM_PROMPT_STATES[t_id] = state
    try:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO fpl_user_state (telegram_id, prompt_state) VALUES (?, ?)", (t_id, state))
        conn.commit()
        conn.close()
    except Exception:
        pass

def get_prompt_state(telegram_id: int) -> Optional[str]:
    t_id = int(telegram_id)
    if t_id in MEM_PROMPT_STATES:
        return MEM_PROMPT_STATES[t_id]
    try:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT prompt_state FROM fpl_user_state WHERE telegram_id = ?", (t_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            MEM_PROMPT_STATES[t_id] = row[0]
            return row[0]
    except Exception:
        pass
    return None

def clear_prompt_state(telegram_id: int):
    t_id = int(telegram_id)
    MEM_PROMPT_STATES.pop(t_id, None)
    try:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM fpl_user_state WHERE telegram_id = ?", (t_id,))
        conn.commit()
        conn.close()
    except Exception:
        pass

def get_all_user_ids() -> List[int]:
    if USE_TURSO:
        res = turso_execute("SELECT telegram_id FROM fpl_users")
        return [int(r["telegram_id"]) for r in res if r.get("telegram_id")]
    else:
        conn = get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT telegram_id FROM fpl_users")
        rows = cursor.fetchall()
        conn.close()
        return [r[0] for r in rows]

def get_stats() -> Dict[str, Any]:
    try:
        if USE_TURSO:
            res = turso_execute("SELECT COUNT(*) as total_users FROM fpl_users")
            return {"total_users": int(res[0].get("total_users", 0))} if res else {"total_users": 0}
        else:
            conn = get_sqlite_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM fpl_users")
            cnt = cursor.fetchone()[0]
            conn.close()
            return {"total_users": cnt}
    except Exception:
        return {"total_users": 0}

def is_admin(telegram_id: int) -> bool:
    return int(telegram_id) in SUPER_ADMINS

if __name__ == "__main__":
    init_db()
    print("FPL Database initialized successfully! USE_TURSO =", USE_TURSO)
