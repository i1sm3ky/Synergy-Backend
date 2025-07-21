import sqlite3
import bcrypt
import os

DB_FILE = "./test/users.db"

os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)


def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                hashed_password TEXT NOT NULL,
                org_id TEXT NOT NULL DEFAULT ''
            )
        """
        )
        conn.commit()


# Function to add a user
def add_user(email, password, org_id):
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode(
        "utf-8"
    )

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO users (email, hashed_password, org_id)
                VALUES (?, ?, ?)
            """,
                (email, hashed_password, org_id),
            )
            conn.commit()
        except sqlite3.IntegrityError:
            print(f"User with email {email} already exists.")


# Function to get user by email
def get_user_by_email(email):
    with sqlite3.connect(DB_FILE) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        return dict(row) if row else None


def check_password(hashed_password, password):
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))


# Function to update user's password
def update_password(email, new_password):
    hashed_password = bcrypt.hashpw(
        new_password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE users
            SET hashed_password = ?
            WHERE email = ?
            """,
            (hashed_password, email),
        )
        conn.commit()
        return cursor.rowcount > 0  # Returns True if password was updated


if __name__ == "__main__":
    init_db()
