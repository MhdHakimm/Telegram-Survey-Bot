# import sqlite3
# import os
# import sys

# sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# from config import DATABASE_PATH


# def get_connection():
#     conn = sqlite3.connect(DATABASE_PATH)
#     conn.row_factory = sqlite3.Row
#     conn.execute("PRAGMA foreign_keys = ON")
#     return conn


# def init_db():
#     conn = get_connection()
#     cursor = conn.cursor()
#     cursor.executescript("""
#         CREATE TABLE IF NOT EXISTS surveys (
#             id          INTEGER PRIMARY KEY AUTOINCREMENT,
#             title       TEXT    NOT NULL,
#             description TEXT    DEFAULT '',
#             is_active   INTEGER DEFAULT 1,
#             created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#         );

#         CREATE TABLE IF NOT EXISTS questions (
#             id            INTEGER PRIMARY KEY AUTOINCREMENT,
#             survey_id     INTEGER NOT NULL,
#             question_text TEXT    NOT NULL,
#             question_type TEXT    NOT NULL,
#             order_num     INTEGER NOT NULL DEFAULT 0,
#             FOREIGN KEY (survey_id) REFERENCES surveys(id) ON DELETE CASCADE
#         );

#         CREATE TABLE IF NOT EXISTS options (
#             id          INTEGER PRIMARY KEY AUTOINCREMENT,
#             question_id INTEGER NOT NULL,
#             option_text TEXT    NOT NULL,
#             order_num   INTEGER NOT NULL DEFAULT 0,
#             FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
#         );

#         CREATE TABLE IF NOT EXISTS response_tracking (
#             id           INTEGER PRIMARY KEY AUTOINCREMENT,
#             survey_id    INTEGER NOT NULL,
#             user_id      INTEGER NOT NULL,
#             completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#             UNIQUE(survey_id, user_id)
#         );
#     """)
#     conn.commit()
#     conn.close()


# # ── Survey CRUD ───────────────────────────────────────────────────────────────

# def create_survey(title: str, description: str) -> int:
#     conn = get_connection()
#     cur = conn.cursor()
#     cur.execute("INSERT INTO surveys (title, description) VALUES (?, ?)", (title, description))
#     survey_id = cur.lastrowid
#     conn.commit()
#     conn.close()
#     return survey_id


# def get_all_surveys():
#     conn = get_connection()
#     rows = conn.execute("SELECT * FROM surveys ORDER BY created_at DESC").fetchall()
#     conn.close()
#     return rows


# def get_active_surveys():
#     conn = get_connection()
#     rows = conn.execute(
#         "SELECT * FROM surveys WHERE is_active = 1 ORDER BY created_at DESC"
#     ).fetchall()
#     conn.close()
#     return rows


# def get_survey_by_id(survey_id: int):
#     conn = get_connection()
#     row = conn.execute("SELECT * FROM surveys WHERE id = ?", (survey_id,)).fetchone()
#     conn.close()
#     return row


# def update_survey_title(survey_id: int, title: str):
#     conn = get_connection()
#     conn.execute("UPDATE surveys SET title = ? WHERE id = ?", (title, survey_id))
#     conn.commit()
#     conn.close()


# def update_survey_description(survey_id: int, description: str):
#     conn = get_connection()
#     conn.execute("UPDATE surveys SET description = ? WHERE id = ?", (description, survey_id))
#     conn.commit()
#     conn.close()


# def toggle_survey_active(survey_id: int):
#     conn = get_connection()
#     conn.execute(
#         "UPDATE surveys SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END WHERE id = ?",
#         (survey_id,),
#     )
#     conn.commit()
#     conn.close()


# def delete_survey(survey_id: int):
#     conn = get_connection()
#     conn.execute("DELETE FROM surveys WHERE id = ?", (survey_id,))
#     conn.commit()
#     conn.close()


# # ── Question CRUD ─────────────────────────────────────────────────────────────

# def add_question(survey_id: int, question_text: str, question_type: str) -> int:
#     conn = get_connection()
#     cur = conn.cursor()
#     cur.execute(
#         "SELECT COALESCE(MAX(order_num), 0) + 1 FROM questions WHERE survey_id = ?",
#         (survey_id,),
#     )
#     order_num = cur.fetchone()[0]
#     cur.execute(
#         "INSERT INTO questions (survey_id, question_text, question_type, order_num) VALUES (?, ?, ?, ?)",
#         (survey_id, question_text, question_type, order_num),
#     )
#     question_id = cur.lastrowid
#     conn.commit()
#     conn.close()
#     return question_id


# def get_questions_by_survey(survey_id: int):
#     conn = get_connection()
#     rows = conn.execute(
#         "SELECT * FROM questions WHERE survey_id = ? ORDER BY order_num", (survey_id,)
#     ).fetchall()
#     conn.close()
#     return rows


# def get_question_by_id(question_id: int):
#     conn = get_connection()
#     row = conn.execute("SELECT * FROM questions WHERE id = ?", (question_id,)).fetchone()
#     conn.close()
#     return row


# def update_question_text(question_id: int, text: str):
#     conn = get_connection()
#     conn.execute("UPDATE questions SET question_text = ? WHERE id = ?", (text, question_id))
#     conn.commit()
#     conn.close()


# def delete_question(question_id: int):
#     conn = get_connection()
#     conn.execute("DELETE FROM questions WHERE id = ?", (question_id,))
#     conn.commit()
#     conn.close()


# # ── Options CRUD ──────────────────────────────────────────────────────────────

# def add_option(question_id: int, option_text: str) -> int:
#     conn = get_connection()
#     cur = conn.cursor()
#     cur.execute(
#         "SELECT COALESCE(MAX(order_num), 0) + 1 FROM options WHERE question_id = ?",
#         (question_id,),
#     )
#     order_num = cur.fetchone()[0]
#     cur.execute(
#         "INSERT INTO options (question_id, option_text, order_num) VALUES (?, ?, ?)",
#         (question_id, option_text, order_num),
#     )
#     option_id = cur.lastrowid
#     conn.commit()
#     conn.close()
#     return option_id


# def get_options_by_question(question_id: int):
#     conn = get_connection()
#     rows = conn.execute(
#         "SELECT * FROM options WHERE question_id = ? ORDER BY order_num", (question_id,)
#     ).fetchall()
#     conn.close()
#     return rows


# def delete_option(option_id: int):
#     conn = get_connection()
#     conn.execute("DELETE FROM options WHERE id = ?", (option_id,))
#     conn.commit()
#     conn.close()


# # ── Response tracking ─────────────────────────────────────────────────────────

# def mark_survey_completed(survey_id: int, user_id: int):
#     conn = get_connection()
#     try:
#         conn.execute(
#             "INSERT INTO response_tracking (survey_id, user_id) VALUES (?, ?)",
#             (survey_id, user_id),
#         )
#         conn.commit()
#     except sqlite3.IntegrityError:
#         pass
#     finally:
#         conn.close()


# def has_user_completed_survey(survey_id: int, user_id: int) -> bool:
#     conn = get_connection()
#     row = conn.execute(
#         "SELECT id FROM response_tracking WHERE survey_id = ? AND user_id = ?",
#         (survey_id, user_id),
#     ).fetchone()
#     conn.close()
#     return row is not None


import sqlite3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import DATABASE_PATH


# ── Connection ────────────────────────────────────────────────────────────────


def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# ── Init DB ───────────────────────────────────────────────────────────────────


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS surveys (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT    NOT NULL,
            description TEXT    DEFAULT '',
            is_active   INTEGER DEFAULT 1,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS questions (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            survey_id     INTEGER NOT NULL,
            question_text TEXT    NOT NULL,
            question_type TEXT    NOT NULL,
            order_num     INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (survey_id) REFERENCES surveys(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS options (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER NOT NULL,
            option_text TEXT    NOT NULL,
            order_num   INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS response_tracking (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            survey_id    INTEGER NOT NULL,
            user_id      INTEGER NOT NULL,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(survey_id, user_id)
        );

        -- ✅ NEW: store actual answers
        CREATE TABLE IF NOT EXISTS responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            survey_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            question_text TEXT,
            answer TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (survey_id) REFERENCES surveys(id) ON DELETE CASCADE
        );
    """
    )

    conn.commit()
    conn.close()


# ── Survey CRUD ───────────────────────────────────────────────────────────────


def create_survey(title: str, description: str) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO surveys (title, description) VALUES (?, ?)", (title, description)
    )
    survey_id = cur.lastrowid
    conn.commit()
    conn.close()
    return survey_id


def get_active_surveys():
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM surveys WHERE is_active = 1 ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return rows


def get_survey_by_id(survey_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM surveys WHERE id = ?", (survey_id,)).fetchone()
    conn.close()
    return row


def delete_survey(survey_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM surveys WHERE id = ?", (survey_id,))
    conn.commit()
    conn.close()


# ── Question CRUD ─────────────────────────────────────────────────────────────


def add_question(survey_id: int, question_text: str, question_type: str) -> int:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT COALESCE(MAX(order_num), 0) + 1 FROM questions WHERE survey_id = ?",
        (survey_id,),
    )
    order_num = cur.fetchone()[0]

    cur.execute(
        "INSERT INTO questions (survey_id, question_text, question_type, order_num) VALUES (?, ?, ?, ?)",
        (survey_id, question_text, question_type, order_num),
    )

    question_id = cur.lastrowid
    conn.commit()
    conn.close()
    return question_id


def get_questions_by_survey(survey_id: int):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM questions WHERE survey_id = ? ORDER BY order_num", (survey_id,)
    ).fetchall()
    conn.close()
    return rows


# ── Options ───────────────────────────────────────────────────────────────────


def add_option(question_id: int, option_text: str) -> int:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT COALESCE(MAX(order_num), 0) + 1 FROM options WHERE question_id = ?",
        (question_id,),
    )
    order_num = cur.fetchone()[0]

    cur.execute(
        "INSERT INTO options (question_id, option_text, order_num) VALUES (?, ?, ?)",
        (question_id, option_text, order_num),
    )

    option_id = cur.lastrowid
    conn.commit()
    conn.close()
    return option_id


def get_options_by_question(question_id: int):
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM options WHERE question_id = ? ORDER BY order_num", (question_id,)
    ).fetchall()
    conn.close()
    return rows


# ── Responses (THIS IS THE IMPORTANT PART) ────────────────────────────────────


def save_response(survey_id: int, user_id: int, responses: list):
    conn = get_connection()
    cursor = conn.cursor()

    for r in responses:
        cursor.execute(
            """
            INSERT INTO responses (
                survey_id, user_id, question_id, question_text, answer
            )
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                survey_id,
                user_id,
                r.get("question_id", 0),
                r["question_text"],
                r["answer"],
            ),
        )

    conn.commit()
    conn.close()


# ── Tracking (prevent duplicates) ─────────────────────────────────────────────


def mark_survey_completed(survey_id: int, user_id: int):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO response_tracking (survey_id, user_id) VALUES (?, ?)",
            (survey_id, user_id),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()


def has_user_completed_survey(survey_id: int, user_id: int) -> bool:
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM response_tracking WHERE survey_id = ? AND user_id = ?",
        (survey_id, user_id),
    ).fetchone()
    conn.close()
    return row is not None
