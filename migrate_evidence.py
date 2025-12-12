import psycopg2
import psycopg2.extras
import json
import ast
import os

RATEL_DB_URL = os.getenv("DATABASE_URL")

def migrate_evidence():
    db = psycopg2.connect(RATEL_DB_URL, sslmode="require")
    with db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT id, evidence FROM reports")
        rows = cur.fetchall()
        for row in rows:
            try:
                # Convert old string representation to Python list
                lst = ast.literal_eval(row['evidence'])
                # Save proper JSON
                cur.execute("UPDATE reports SET evidence=%s WHERE id=%s", (json.dumps(lst), row['id']))
            except Exception as e:
                print(f"Skipping report {row['id']}: {e}")
        db.commit()
    db.close()
    print("Migration complete.")

if __name__ == "__main__":
    migrate_evidence()