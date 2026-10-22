# ==============================================================================
# MODULE: DATABASE CONFIGURATION & CORE IMPORTS
# Purpose: Imports required database libraries and defines database file path.
# ==============================================================================
import sqlite3
import pandas as pd
from datetime import datetime, timedelta

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
    # Purpose: Tracks equipment borrowed by students, duration, return deadline (due_date),
    #          issue dates, and return statuses.
    # --------------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            roll_no TEXT NOT NULL,
            equipment_id TEXT NOT NULL,
            issue_date TEXT NOT NULL,
            duration_days INTEGER NOT NULL DEFAULT 7,
            due_date TEXT NOT NULL DEFAULT '',
            return_date TEXT,
            condition_on_return TEXT,
            status TEXT NOT NULL CHECK(status IN ('Issued', 'Returned')),
            FOREIGN KEY (equipment_id) REFERENCES equipment(equipment_id)
        )
    """)

    # --------------------------------------------------------------------------
    # SCHEMA MIGRATION: Safe column additions for transactions (duration_days, due_date)
    # Purpose: Adds duration_days and due_date if upgrading existing database.
    # --------------------------------------------------------------------------
    cursor.execute("PRAGMA table_info(transactions)")
    trans_cols = [c[1] for c in cursor.fetchall()]
    if "duration_days" not in trans_cols:
        cursor.execute("ALTER TABLE transactions ADD COLUMN duration_days INTEGER DEFAULT 7")
    if "due_date" not in trans_cols:
        cursor.execute("ALTER TABLE transactions ADD COLUMN due_date TEXT DEFAULT ''")

    # Backfill any existing transactions missing due_date
    cursor.execute("SELECT transaction_id, issue_date, duration_days, due_date FROM transactions WHERE due_date IS NULL OR due_date = ''")
    rows_to_backfill = cursor.fetchall()
    for row in rows_to_backfill:
        t_id, iss_date, dur, _ = row
        dur = dur if dur is not None and dur > 0 else 7
        try:
            iss_dt = datetime.strptime(str(iss_date).strip(), "%Y-%m-%d")
            calc_due = (iss_dt + timedelta(days=dur)).strftime("%Y-%m-%d")
        except Exception:
            calc_due = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("UPDATE transactions SET duration_days = ?, due_date = ? WHERE transaction_id = ?", (dur, calc_due, t_id))

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
               t.issue_date, t.duration_days, t.due_date, t.return_date, t.condition_on_return, t.status
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
# Purpose: Validates stock and status, inserts an 'Issued' transaction record with duration
#          and calculated deadline due_date, and decrements available stock count by 1.
# ==============================================================================
def issue_equipment(student_name, roll_no, eq_id, duration_days=7):
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
    # STEP 2: Validate duration (1 to 90 days maximum limit)
    # Purpose: Ensures borrowing window respects academic department duration policy.
    # --------------------------------------------------------------------------
    try:
        duration_days = int(duration_days)
        if duration_days < 1:
            duration_days = 1
        elif duration_days > 90:
            duration_days = 90
    except (ValueError, TypeError):
        duration_days = 7

    today_dt = datetime.now()
    today = today_dt.strftime("%Y-%m-%d")
    due_date = (today_dt + timedelta(days=duration_days)).strftime("%Y-%m-%d")

    # --------------------------------------------------------------------------
    # STEP 3: Record issue transaction with duration and calculated due date
    # Purpose: Logs student details, equipment ID, issue date, duration, due date, and 'Issued' status.
    # --------------------------------------------------------------------------
    cursor.execute(
        """
        INSERT INTO transactions (student_name, roll_no, equipment_id, issue_date, duration_days, due_date, status)
        VALUES (?, ?, ?, ?, ?, ?, 'Issued')
    """,
        (student_name, roll_no, eq_id, today, duration_days, due_date),
    )

    # --------------------------------------------------------------------------
    # STEP 4: Decrement available inventory quantity
    # Purpose: Deducts 1 unit from available_qty in equipment table.
    # --------------------------------------------------------------------------
    cursor.execute(
        "UPDATE equipment SET available_qty = available_qty - 1 WHERE equipment_id = ?",
        (eq_id,),
    )
    conn.commit()
    conn.close()
    return True, f"Equipment issued successfully for {duration_days} days (Due: {due_date})."


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
# TOPIC: FETCH CURRENT ACTIVE ISSUES WITH DEADLINES
# Purpose: Returns all transactions currently in 'Issued' status along with
#          equipment metadata, issue duration, and return deadline (due_date).
# ==============================================================================
def get_active_issues():
    conn = get_connection()
    query = """
        SELECT t.transaction_id, t.student_name, t.roll_no, t.equipment_id, e.name AS equipment_name,
               e.lab_name, t.issue_date, t.duration_days, t.due_date, t.status
        FROM transactions t
        LEFT JOIN equipment e ON t.equipment_id = e.equipment_id
        WHERE t.status = 'Issued'
        ORDER BY t.due_date ASC
    """
    df = pd.read_sql(query, conn)
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


# ==============================================================================
# TOPIC: DEADLINE CALCULATION & ALARM ENGINE
# Purpose: Calculates time remaining until borrowing deadline, flags overdue or
#          near-deadline equipment, and produces warning badges for UI display.
# ==============================================================================
def compute_deadline_info(due_date_str):
    """
    Calculates days remaining and status descriptor for a given due_date (YYYY-MM-DD).
    Returns a dictionary:
      - days_remaining (int): Negative if overdue, 0 if due today, positive if remaining.
      - status_text (str): Color-coded human-readable status badge.
      - urgency (str): 'overdue', 'due_today', 'due_soon', 'safe'.
      - is_alert (bool): True if item requires student/faculty attention (overdue or <= 3 days).
    """
    if not due_date_str:
        return {
            "days_remaining": 999,
            "status_text": "No Deadline Set",
            "urgency": "safe",
            "is_alert": False,
        }
    try:
        due_dt = datetime.strptime(str(due_date_str).strip(), "%Y-%m-%d").date()
        today = datetime.now().date()
        diff = (due_dt - today).days

        if diff < 0:
            abs_diff = abs(diff)
            day_word = "day" if abs_diff == 1 else "days"
            return {
                "days_remaining": diff,
                "status_text": f"🚨 Overdue by {abs_diff} {day_word}!",
                "urgency": "overdue",
                "is_alert": True,
            }
        elif diff == 0:
            return {
                "days_remaining": 0,
                "status_text": "⏰ Due Today!",
                "urgency": "due_today",
                "is_alert": True,
            }
        elif diff <= 3:
            day_word = "day" if diff == 1 else "days"
            return {
                "days_remaining": diff,
                "status_text": f"⚠️ Due in {diff} {day_word}!",
                "urgency": "due_soon",
                "is_alert": True,
            }
        else:
            return {
                "days_remaining": diff,
                "status_text": f"🟢 {diff} days left",
                "urgency": "safe",
                "is_alert": False,
            }
    except Exception:
        return {
            "days_remaining": 999,
            "status_text": "Unknown Deadline",
            "urgency": "safe",
            "is_alert": False,
        }


# ==============================================================================
# TOPIC: FETCH DEADLINE ALARMS & WARNINGS
# Purpose: Retrieves active borrowings that are overdue or nearing their return deadline.
#          Filters by roll_no / student_name if supplied, or returns department-wide alerts.
# ==============================================================================
def get_deadline_alerts(roll_no=None, student_name=None, threshold_days=3):
    """
    Returns a list of dicts for active issued items where return deadline is within
    threshold_days or already passed (overdue).
    """
    conn = get_connection()
    if roll_no or student_name:
        query = """
            SELECT t.transaction_id, t.student_name, t.roll_no, t.equipment_id,
                   e.name AS equipment_name, e.lab_name, t.issue_date, t.duration_days, t.due_date
            FROM transactions t
            LEFT JOIN equipment e ON t.equipment_id = e.equipment_id
            WHERE t.status = 'Issued'
              AND ((? IS NOT NULL AND t.roll_no = ?) OR (? IS NOT NULL AND t.student_name = ?))
            ORDER BY t.due_date ASC
        """
        df = pd.read_sql(query, conn, params=(roll_no, roll_no, student_name, student_name))
    else:
        query = """
            SELECT t.transaction_id, t.student_name, t.roll_no, t.equipment_id,
                   e.name AS equipment_name, e.lab_name, t.issue_date, t.duration_days, t.due_date
            FROM transactions t
            LEFT JOIN equipment e ON t.equipment_id = e.equipment_id
            WHERE t.status = 'Issued'
            ORDER BY t.due_date ASC
        """
        df = pd.read_sql(query, conn)
    conn.close()

    if df.empty:
        return []

    alerts = []
    for _, row in df.iterrows():
        info = compute_deadline_info(row.get("due_date"))
        if info["is_alert"] or info["days_remaining"] <= threshold_days:
            alerts.append({
                "transaction_id": row["transaction_id"],
                "student_name": row["student_name"],
                "roll_no": row["roll_no"],
                "equipment_id": row["equipment_id"],
                "equipment_name": row["equipment_name"] or row["equipment_id"],
                "lab_name": row["lab_name"] or "Lab Counter",
                "issue_date": row["issue_date"],
                "duration_days": row["duration_days"],
                "due_date": row["due_date"],
                "days_remaining": info["days_remaining"],
                "status_text": info["status_text"],
                "urgency": info["urgency"],
            })

    # Sort so most critical items (most days overdue) appear first
    urgency_ranks = {"overdue": 0, "due_today": 1, "due_soon": 2, "safe": 3}
    alerts.sort(key=lambda x: (urgency_ranks.get(x["urgency"], 4), x["days_remaining"]))
    return alerts


# ==============================================================================
# TOPIC: ENRICH DATAFRAME WITH DEADLINE STATUS
# Purpose: Appends 'Days Remaining' and 'Deadline Status' columns to any table
#          containing 'due_date' for standardized visual display.
# ==============================================================================
def format_deadline_dataframe(df):
    """
    Appends 'Days Remaining' and 'Deadline Status' columns to a DataFrame.
    """
    if df.empty:
        return df

    df = df.copy()
    if "due_date" not in df.columns:
        return df

    days_list = []
    status_list = []

    for _, row in df.iterrows():
        if "status" in df.columns and row.get("status") == "Returned":
            days_list.append(None)
            status_list.append("✅ Returned")
            continue

        info = compute_deadline_info(row.get("due_date"))
        days_list.append(info["days_remaining"])
        status_list.append(info["status_text"])

    df["Days Remaining"] = days_list
    df["Deadline Status"] = status_list
    return df

