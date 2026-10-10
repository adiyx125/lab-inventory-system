# ==============================================================================
# MODULE: DATABASE CONFIGURATION & CORE IMPORTS
# Purpose: Imports required database libraries and defines database file path.
# ==============================================================================
import sqlite3
import pandas as pd
from datetime import datetime

DB_NAME = "inventory.db"


# ==============================================================================
# TOPIC: DATABASE CONNECTION MANAGEMENT
# Purpose: Establishes and returns a SQLite connection with foreign keys enabled.
# ==============================================================================
def get_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


# ==============================================================================
# TOPIC: DATABASE INITIALIZATION & SCHEMA MIGRATION
# Purpose: Creates required tables (users, equipment, transactions, maintenance)
#          and performs automatic column migrations if upgrading existing DB.
# ==============================================================================
def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # --------------------------------------------------------------------------
    # TABLE 1: Users Table (Authentication & User Profiles)
    # Purpose: Stores credentials, roles (Admin, Faculty, Student), and student details.
    # --------------------------------------------------------------------------
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

    # --------------------------------------------------------------------------
    # SCHEMA MIGRATION: Safe column additions for older database files
    # Purpose: Adds full_name, roll_no, department if missing from existing users table.
    # --------------------------------------------------------------------------
    cursor.execute("PRAGMA table_info(users)")
    existing_cols = [c[1] for c in cursor.fetchall()]
    if "full_name" not in existing_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN full_name TEXT DEFAULT ''")
    if "roll_no" not in existing_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN roll_no TEXT DEFAULT ''")
    if "department" not in existing_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN department TEXT DEFAULT ''")

    # --------------------------------------------------------------------------
    # TABLE 2: Equipment Inventory Table
    # Purpose: Stores laboratory equipment, specs, categories, quantities, and status.
    # --------------------------------------------------------------------------
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

    # --------------------------------------------------------------------------
    # TABLE 3: Equipment Transactions Table (Issues & Returns)
    # Purpose: Tracks equipment borrowed by students, issue dates, and return statuses.
    # --------------------------------------------------------------------------
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

    # --------------------------------------------------------------------------
    # TABLE 4: Maintenance & Damage Logs Table
    # Purpose: Tracks equipment under repair, technician names, and repair progress.
    # --------------------------------------------------------------------------
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


# ==============================================================================
# TOPIC: USER AUTHENTICATION & LOGIN VERIFICATION
# Purpose: Verifies user credentials against database and returns profile details.
# ==============================================================================
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


# ==============================================================================
# TOPIC: STUDENT & USER REGISTRATION
# Purpose: Registers a new user account with duplicate username and roll number checks.
# ==============================================================================
def register_user(username, password, role="Student", full_name="", roll_no="", department=""):
    conn = get_connection()
    cursor = conn.cursor()
    
    # --------------------------------------------------------------------------
    # VALIDATION 1: Check if username already exists
    # Purpose: Ensures unique usernames across all system accounts.
    # --------------------------------------------------------------------------
    cursor.execute("SELECT username FROM users WHERE LOWER(username) = LOWER(?)", (username.strip(),))
    if cursor.fetchone():
        conn.close()
        return False, f"Username '{username}' is already taken. Please choose another username."

    # --------------------------------------------------------------------------
    # VALIDATION 2: Check if student roll number is already registered
    # Purpose: Prevents duplicate student registrations with the same PRN / Roll Number.
    # --------------------------------------------------------------------------
    if role == "Student" and roll_no.strip():
        cursor.execute("SELECT username FROM users WHERE LOWER(roll_no) = LOWER(?)", (roll_no.strip(),))
        existing = cursor.fetchone()
        if existing:
            conn.close()
            return False, f"Roll Number '{roll_no}' is already registered under username '{existing[0]}'."

    # --------------------------------------------------------------------------
    # INSERTION: Save new user record
    # Purpose: Stores the newly registered user into the users table.
    # --------------------------------------------------------------------------
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


# ==============================================================================
# TOPIC: STUDENT BORROWING & RETURN TRANSACTION HISTORY
# Purpose: Fetches borrowing and return history for a specific student by roll number or name.
# ==============================================================================
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


# ==============================================================================
# TOPIC: ADD EQUIPMENT (INVENTORY CRUD - CREATE)
# Purpose: Inserts a newly procured laboratory equipment item into the inventory.
# ==============================================================================
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


# ==============================================================================
# TOPIC: UPDATE EQUIPMENT (INVENTORY CRUD - UPDATE)
# Purpose: Modifies metadata, lab assignment, quantities, and status of existing equipment.
# ==============================================================================
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


# ==============================================================================
# TOPIC: DELETE EQUIPMENT (INVENTORY CRUD - DELETE)
# Purpose: Permanently deletes an equipment record from the inventory table.
# ==============================================================================
def delete_equipment(eq_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM equipment WHERE equipment_id = ?", (eq_id,))
    conn.commit()
    conn.close()


# ==============================================================================
# TOPIC: RETRIEVE ALL EQUIPMENT (INVENTORY CRUD - READ)
# Purpose: Retrieves the full equipment catalog from the database as a DataFrame.
# ==============================================================================
def get_all_equipment():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM equipment", conn)
    conn.close()
    return df


# ==============================================================================
# TOPIC: ISSUE EQUIPMENT TRANSACTION
# Purpose: Validates stock and status, inserts an 'Issued' transaction record,
#          and decrements the available stock count by 1.
# ==============================================================================
def issue_equipment(student_name, roll_no, eq_id):
    conn = get_connection()
    cursor = conn.cursor()

    # --------------------------------------------------------------------------
    # STEP 1: Verify equipment exists, is in stock, and has Active status
    # Purpose: Prevents issuing equipment that is out of stock or under repair.
    # --------------------------------------------------------------------------
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

    # --------------------------------------------------------------------------
    # STEP 2: Record issue transaction
    # Purpose: Logs student details, equipment ID, issue date, and 'Issued' status.
    # --------------------------------------------------------------------------
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute(
        """
        INSERT INTO transactions (student_name, roll_no, equipment_id, issue_date, status)
        VALUES (?, ?, ?, ?, 'Issued')
    """,
        (student_name, roll_no, eq_id, today),
    )

    # --------------------------------------------------------------------------
    # STEP 3: Decrement available inventory quantity
    # Purpose: Deducts 1 unit from available_qty in equipment table.
    # --------------------------------------------------------------------------
    cursor.execute(
        "UPDATE equipment SET available_qty = available_qty - 1 WHERE equipment_id = ?",
        (eq_id,),
    )
    conn.commit()
    conn.close()
    return True, "Equipment issued successfully."


# ==============================================================================
# TOPIC: RETURN EQUIPMENT TRANSACTION & DAMAGE ROUTING
# Purpose: Updates transaction to 'Returned', records condition (Good / Damaged / Lost),
#          and either restores available stock or logs damaged item to maintenance.
# ==============================================================================
def return_equipment(trans_id, condition):
    conn = get_connection()
    cursor = conn.cursor()

    # --------------------------------------------------------------------------
    # STEP 1: Verify transaction exists and is currently in 'Issued' state
    # Purpose: Ensures only open borrowings can be processed for return.
    # --------------------------------------------------------------------------
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

    # --------------------------------------------------------------------------
    # STEP 2: Update transaction record with return date and physical condition
    # Purpose: Marks transaction as 'Returned' with condition inspection recorded.
    # --------------------------------------------------------------------------
    cursor.execute(
        """
        UPDATE transactions
        SET return_date = ?, condition_on_return = ?, status = 'Returned'
        WHERE transaction_id = ?
    """,
        (today, condition, trans_id),
    )

    # --------------------------------------------------------------------------
    # STEP 3: Branch stock adjustments based on component condition
    # Purpose: If Good -> increment available_qty.
    #          If Damaged -> reduce total_qty, set status to 'Under Repair', log maintenance.
    #          If Lost -> reduce total_qty.
    # --------------------------------------------------------------------------
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


# ==============================================================================
# TOPIC: FETCH CURRENT ACTIVE ISSUES
# Purpose: Returns all transactions currently in 'Issued' status.
# ==============================================================================
def get_active_issues():
    conn = get_connection()
    df = pd.read_sql("SELECT * FROM transactions WHERE status = 'Issued'", conn)
    conn.close()
    return df


# ==============================================================================
# TOPIC: FETCH MAINTENANCE & REPAIR RECORDS
# Purpose: Retrieves maintenance history, optionally filtered for a specific equipment ID.
# ==============================================================================
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


# ==============================================================================
# TOPIC: UPDATE REPAIR / MAINTENANCE RECORD
# Purpose: Updates assigned technician and repair status; if status is 'Repaired',
#          restores equipment stock and resets status to 'Active'.
# ==============================================================================
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

    # --------------------------------------------------------------------------
    # RESTORATION LOGIC: Return repaired item back to active inventory
    # Purpose: Increments total_qty & available_qty and marks status as 'Active'.
    # --------------------------------------------------------------------------
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
