import csv
import os
from datetime import datetime, timezone

USERS_CSV = os.path.join(os.path.dirname(__file__), "users.csv")
PRINTERS_CSV = os.path.join(os.path.dirname(__file__), "printers.csv")

if not os.path.exists(PRINTERS_CSV):
    with open(PRINTERS_CSV, "w", newline="") as f:
        csv.writer(f).writerow(["name", "ip", "type", "status", "last_seen"])


def save_printers(network_printers, usb_printers):
    """Upsert discovered printers and mark missing ones as offline."""
    now = datetime.now(timezone.utc).isoformat()

    # Load existing rows
    with open(PRINTERS_CSV, newline="") as f:
        rows = {r["name"]: r for r in csv.DictReader(f) if r.get("name")}

    # Upsert online printers
    for p in network_printers:
        name = p.get("name", "")
        rows[name] = {
            "name": name,
            "ip": p.get("ip", ""),
            "type": "Network",
            "status": "online",
            "last_seen": now,
        }
    for p in usb_printers:
        name = p.get("name", "")
        rows[name] = {
            "name": name,
            "ip": "",
            "type": "USB",
            "status": "online",
            "last_seen": now,
        }

    # Mark anything not seen this scan as offline
    seen_names = {p["name"] for p in network_printers + usb_printers}
    for name, row in rows.items():
        if name not in seen_names:
            row["status"] = "offline"

    # Write back
    with open(PRINTERS_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "ip", "type", "status", "last_seen"])
        writer.writeheader()
        writer.writerows(rows.values())


def load_printers():
    """Return all known printers from the CSV."""
    with open(PRINTERS_CSV, newline="") as f:
        return [r for r in csv.DictReader(f) if r.get("name")]

# make sure the file exists with a header
if not os.path.exists(USERS_CSV):
    with open(USERS_CSV, "w", newline="") as f:
        csv.writer(f).writerow(["id", "email", "created_at", "access"])


def _migrate_access_column():
    """Add the access column to existing rows if it's missing."""
    with open(USERS_CSV, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []
    if "access" in fieldnames:
        return
    # rewrite with access column defaulting to True for all existing users
    with open(USERS_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "email", "created_at", "access"])
        writer.writeheader()
        for row in rows:
            if not row.get("email"):
                continue
            writer.writerow({
                "id": row.get("id", ""),
                "email": row["email"],
                "created_at": row.get("created_at", ""),
                "access": row.get("access", "True"),
            })


_migrate_access_column()


def user_id(email):
    with open(USERS_CSV, newline="") as f:
        for row in csv.DictReader(f):
            if row.get("email") == email:
                return row["id"]
    return None


def save_user_email(email):
    if user_id(email):
        return
    rows = []
    with open(USERS_CSV, newline="") as f:
        rows = [r for r in csv.DictReader(f) if r.get("email")]
    new_id = len(rows) + 1
    with open(USERS_CSV, "a", newline="") as f:
        csv.writer(f).writerow([new_id, email, datetime.now(timezone.utc).isoformat(), "True"])


def set_user_access(user_id_val, granted: bool):
    """Grant or restrict access for a user by their id."""
    with open(USERS_CSV, newline="") as f:
        rows = [r for r in csv.DictReader(f) if r.get("email")]
    with open(USERS_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "email", "created_at", "access"])
        writer.writeheader()
        for row in rows:
            if row["id"] == str(user_id_val):
                row["access"] = str(granted)
            writer.writerow(row)


def print_all_user_data():
    with open(USERS_CSV, newline="") as f:
        rows = [r for r in csv.DictReader(f) if r.get("email")]
    if rows:
        print("All Users:")
        for row in rows:
            for k, v in row.items():
                print(f"{k}: {v}")
            print("-" * 20)
    else:
        print("No users found.")
    return rows


def count_users():
    with open(USERS_CSV, newline="") as f:
        count = sum(1 for r in csv.DictReader(f) if r.get("email"))
    print(f"There are currently {count} user(s).")
    return count


def print_users():
    with open(USERS_CSV, newline="") as f:
        for row in csv.DictReader(f):
            if row.get("email"):
                print(row)


"""
# ---- PostgreSQL versions (swap back in if needed) ----

import psycopg2
from psycopg2 import pool

database_url = os.environ.get('DATABASE_URL')

db_pool = pool.SimpleConnectionPool(1, 10, dsn=database_url)


def user_id(email):
    conn = db_pool.getconn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s;", (email,))
        result = cursor.fetchone()
        cursor.close()
        return result[0]
    finally:
        db_pool.putconn(conn)


def save_user_email(email):
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO userrs (email) VALUES (%s) ON CONFLICT (email) DO NOTHING",
                (email,)
            )
            conn.commit()
    except Exception:
        conn.rollback()
    finally:
        db_pool.putconn(conn)


def print_all_user_data():
    conn = db_pool.getconn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM userrs;")
        users = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]
        cursor.close()
        if users:
            print("All Users:")
            for user in users:
                user_data = dict(zip(column_names, user))
                for key, value in user_data.items():
                    print(f"{key}: {value}")
                print("-" * 20)
        else:
            print("No users found.")
        return users
    finally:
        db_pool.putconn(conn)


def count_users():
    conn = db_pool.getconn()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM userrs;")
            count = cursor.fetchone()[0]
            print(f"There are currently {count} user(s) in the database.")
            return count
    finally:
        db_pool.putconn(conn)


def print_users():
    conn = db_pool.getconn()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users;")
        for row in cursor.fetchall():
            print(row)
        cursor.close()
    finally:
        db_pool.putconn(conn)
"""
