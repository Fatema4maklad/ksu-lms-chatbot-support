import sqlite3

conn = sqlite3.connect("ksu_lms.db")
cursor = conn.cursor()

# Check if the column already exists, so this script is safe to re-run.
cursor.execute("PRAGMA table_info(conversations)")
columns = [row[1] for row in cursor.fetchall()]

if "ticket_status" in columns:
    print("Column 'ticket_status' already exists — nothing to do.")
else:
    cursor.execute(
        "ALTER TABLE conversations ADD COLUMN ticket_status TEXT DEFAULT 'open'"
    )
    conn.commit()
    print("Added 'ticket_status' column, defaulted to 'open' for all existing rows.")

conn.close()