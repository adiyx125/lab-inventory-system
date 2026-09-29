import sqlite3
import pandas as pd
from datetime import datetime

DB_NAME = "inventory.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Users Table (M1) - with full_name, roll_no, department
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            full_name TEXT DEFAULT '',
            roll_no TEXT DEFAULT '',
            department TEXT DEFAULT ''
        )
    """)

    # Safe schema migration for existing databases
    cursor.execute("PRAGMA table_info(users)")
    existing_cols = [c[1] for c in cursor.fetchall()]
    if "full_name" not in existing_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN full_name TEXT DEFAULT ''")
    if "roll_no" not in existing_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN roll_no TEXT DEFAULT ''")
    if "department" not in existing_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN department TEXT DEFAULT ''")

    # 2. Equipment Inventory Table (M2 - with status column)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS equipment (
            equipment_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            brand TEXT,
            lab_name TEXT NOT NULL,
            total_qty INTEGER NOT NULL CHECK(total_qty >= 0),
            available_qty INTEGER NOT NULL CHECK(available_qty >= 0),
            status TEXT NOT NULL DEFAULT 'Active' CHECK(status IN ('Active', 'Under Repair', 'Retired')),
            purchase_date TEXT
        )
    """)

    # 3. Transactions Table (M3)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            roll_no TEXT NOT NULL,
            equipment_id TEXT NOT NULL,
            issue_date TEXT NOT NULL,
            return_date TEXT,
            condition_on_return TEXT,
            status TEXT NOT NULL CHECK(status IN ('Issued', 'Returned')),
            FOREIGN KEY (equipment_id) REFERENCES equipment(equipment_id)
        )
    """)

    # 4. Maintenance / Damage Logs (M4)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS maintenance (
            repair_id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_id TEXT NOT NULL,
            technician_name TEXT NOT NULL,
            repair_date TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('Under Repair', 'Repaired', 'Scrapped')),
            FOREIGN KEY (equipment_id) REFERENCES equipment(equipment_id)
        )
    """)

    conn.commit()
    conn.close()


# --- M1: Authentication ---
def verify_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT username, role, full_name, roll_no, department FROM users WHERE username = ? AND password = ?",
        (username.strip(), password),
    )
    user = cursor.fetchone()
    conn.close()
    if user:
        return {
            "username": user[0],
            "role": user[1],
            "full_name": user[2] if user[2] else user[0],
            "roll_no": user[3] if user[3] else "",
            "department": user[4] if user[4] else "Information Technology",
        }
    return None


def register_user(username, password, role="Student", full_name="", roll_no="", department=""):
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if username exists
    cursor.execute("SELECT username FROM users WHERE LOWER(username) = LOWER(?)", (username.strip(),))
    if cursor.fetchone():
        conn.close()
        return False, f"Username '{username}' is already taken. Please choose another username."

    # If Student and roll number provided, check if roll number already exists
    if role == "Student" and roll_no.strip():
        cursor.execute("SELECT username FROM users WHERE LOWER(roll_no) = LOWER(?)", (roll_no.strip(),))
        existing = cursor.fetchone()
        if existing:
            conn.close()
            return False, f"Roll Number '{roll_no}' is already registered under username '{existing[0]}'."

    cursor.execute(
        """
        INSERT INTO users (username, password, role, full_name, roll_no, department)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (username.strip(), password, role, full_name.strip(), roll_no.strip(), department.strip()),
    )
    conn.commit()
    conn.close()
    return True, "Account created successfully! You can now log in."


def get_student_transactions(roll_no=None, student_name=None):
    conn = get_connection()
    query = """
        SELECT t.transaction_id, t.equipment_id, e.name AS equipment_name, e.lab_name,
               t.issue_date, t.return_date, t.condition_on_return, t.status
        FROM transactions t
        LEFT JOIN equipment e ON t.equipment_id = e.equipment_id
        WHERE (? IS NOT NULL AND t.roll_no = ?) OR (? IS NOT NULL AND t.student_name = ?)
        ORDER BY t.transaction_id DESC
    """
    df = pd.read_sql(query, conn, params=(roll_no, roll_no, student_name, student_name))
    conn.close()
    return df


# --- M2: Inventory Operations (Full CRUD) ---
def add_equipment(eq_id, name, cat, brand, lab, qty, status, p_date):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO equipment (equipment_id, name, category, brand, lab_name, total_qty, available_qty, status, purchase_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (eq_id, name, cat, brand, lab, qty, qty, status, p_date),
    )
    conn.commit()
    conn.close()


def update_equipment(eq_id, name, cat, brand, lab, total_qty, avail_qty, status):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE equipment 
        SET name = ?, category = ?, brand = ?, lab_name = ?, total_qty = ?, available_qty = ?, status = ?
        WHERE equipment_id = ?
    """,
        (name, cat, brand, lab, total_qty, avail_qty, status, eq_id),
    )
    conn.commit()
    conn.close()


def delete_equipment(eq_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM equipment WHERE equipment_id = ?", (eq_id,))
    conn.commit()
    conn.close()


def get_all_equipment():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM equipment", conn)
    conn.close()
    return df


# --- M3: Issue & Return Helpers ---
def issue_equipment(student_name, roll_no, eq_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT available_qty, status FROM equipment WHERE equipment_id = ?", (eq_id,)
    )
    res = cursor.fetchone()
    if not res or res[0] <= 0:
        conn.close()
        return False, "Equipment is out of stock."
    if res[1] != "Active":
        conn.close()
        return False, f"Cannot issue item currently marked as '{res[1]}'."

    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute(
        """
        INSERT INTO transactions (student_name, roll_no, equipment_id, issue_date, status)
        VALUES (?, ?, ?, ?, 'Issued')
    """,
        (student_name, roll_no, eq_id, today),
    )

    cursor.execute(
        "UPDATE equipment SET available_qty = available_qty - 1 WHERE equipment_id = ?",
        (eq_id,),
    )
    conn.commit()
    conn.close()
    return True, "Equipment issued successfully."


def return_equipment(trans_id, condition):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT equipment_id, status FROM transactions WHERE transaction_id = ?",
        (trans_id,),
    )
    res = cursor.fetchone()
    if not res or res[1] != "Issued":
        conn.close()
        return False, "Transaction is invalid or already returned."

    eq_id = res[0]
    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute(
        """
        UPDATE transactions
        SET return_date = ?, condition_on_return = ?, status = 'Returned'
        WHERE transaction_id = ?
    """,
        (today, condition, trans_id),
    )

    if condition == "Good":
        cursor.execute(
            "UPDATE equipment SET available_qty = available_qty + 1 WHERE equipment_id = ?",
            (eq_id,),
        )
    else:
        if condition == "Damaged":
            cursor.execute(
                """
                INSERT INTO maintenance (equipment_id, technician_name, repair_date, status)
                VALUES (?, 'Pending Assignment', ?, 'Under Repair')
            """,
                (eq_id, today),
            )
            cursor.execute(
                "UPDATE equipment SET status = 'Under Repair' WHERE equipment_id = ?",
                (eq_id,),
            )
        cursor.execute(
            "UPDATE equipment SET total_qty = total_qty - 1 WHERE equipment_id = ?",
            (eq_id,),
        )

    conn.commit()
    conn.close()
    return True, f"Equipment returned and recorded as {condition}."


def get_active_issues():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM transactions WHERE status = 'Issued'", conn)
    conn.close()
    return df


# --- M4: Maintenance Helpers ---
def get_maintenance_records(eq_id=None):
    conn = get_connection()
    if eq_id:
        df = pd.read_sql(
            "SELECT * FROM maintenance WHERE equipment_id = ?", conn, params=(eq_id,)
        )
    else:
        df = pd.read_sql("SELECT * FROM maintenance", conn)
    conn.close()
    return df


def update_repair(repair_id, technician, status):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE maintenance
        SET technician_name = ?, status = ?
        WHERE repair_id = ?
    """,
        (technician, status, repair_id),
    )

    if status == "Repaired":
        cursor.execute(
            "SELECT equipment_id FROM maintenance WHERE repair_id = ?", (repair_id,)
        )
        eq_id = cursor.fetchone()[0]
        cursor.execute(
            """
            UPDATE equipment 
            SET total_qty = total_qty + 1, available_qty = available_qty + 1, status = 'Active' 
            WHERE equipment_id = ?
        """,
            (eq_id,),
        )

    conn.commit()
    conn.close()
