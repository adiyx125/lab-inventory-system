import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import database as db

st.set_page_config(page_title="Lab Equipment Inventory", layout="wide", page_icon="🔬")
db.init_db()

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
    st.session_state["user_role"] = None
    st.session_state["username"] = None
    st.session_state["full_name"] = None
    st.session_state["roll_no"] = None
    st.session_state["department"] = None

# --- M1: LOGIN & STUDENT REGISTRATION SCREEN ---
if not st.session_state["authenticated"]:
    st.markdown(
        "<h2 style='text-align: center; margin-bottom: 0px;'>🔬 Lab Equipment Inventory Management System</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align: center; color: #888; margin-top: 4px;'>SIES Graduate School of Technology — Department of Information Technology</p>",
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([0.8, 1.4, 0.8])
    with col2:
        tab_login, tab_register = st.tabs(["🔑 Sign In", "🎓 Student Sign Up / Register"])

        with tab_login:
            st.subheader("Login Portal")
            st.caption("Access laboratory equipment catalog, project BOMs, and issue hardware components.")

            with st.form("login_form"):
                username = st.text_input("Username / Roll No", placeholder="e.g. aditya125 or admin")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                login_btn = st.form_submit_button("Log In", use_container_width=True, type="primary")

                if login_btn:
                    if username and password:
                        user_data = db.verify_user(username, password)
                        if user_data:
                            st.session_state["authenticated"] = True
                            st.session_state["user_role"] = user_data["role"]
                            st.session_state["username"] = user_data["username"]
                            st.session_state["full_name"] = user_data["full_name"]
                            st.session_state["roll_no"] = user_data["roll_no"]
                            st.session_state["department"] = user_data["department"]
                            st.success(f"Welcome back, {user_data['full_name']}!")
                            st.rerun()
                        else:
                            st.error("❌ Invalid credentials. Please verify username and password or register a new student account.")
                    else:
                        st.warning("Please enter both username and password.")



        with tab_register:
            st.subheader("Student Registration")
            st.caption("Create your personalized lab account to issue items, track borrowings, and explore project BOMs.")

            with st.form("register_form"):
                reg_name = st.text_input("Full Name", placeholder="e.g. Aditya Yadav")
                col_r1, col_r2 = st.columns(2)
                reg_roll = col_r1.text_input("Roll Number / PRN", placeholder="e.g. 125A3125")
                reg_dept = col_r2.selectbox(
                    "Branch / Department",
                    [
                        "Information Technology",
                        "Computer Engineering",
                        "Artificial Intelligence & Data Science",
                        "Electronics & Telecommunication",
                        "Mechanical Engineering",
                    ],
                )
                reg_username = st.text_input("Choose Username", placeholder="e.g. aditya125")
                col_p1, col_p2 = st.columns(2)
                reg_pass1 = col_p1.text_input("Password", type="password")
                reg_pass2 = col_p2.text_input("Confirm Password", type="password")

                reg_submit = st.form_submit_button("Create Student Account", use_container_width=True, type="primary")

                if reg_submit:
                    if not (reg_name and reg_roll and reg_username and reg_pass1 and reg_pass2):
                        st.warning("⚠️ Please fill in all fields.")
                    elif reg_pass1 != reg_pass2:
                        st.error("❌ Passwords do not match. Please verify.")
                    elif len(reg_pass1) < 4:
                        st.error("❌ Password should be at least 4 characters long.")
                    else:
                        ok, msg = db.register_user(
                            username=reg_username,
                            password=reg_pass1,
                            role="Student",
                            full_name=reg_name,
                            roll_no=reg_roll,
                            department=reg_dept,
                        )
                        if ok:
                            # Auto-login the newly created student immediately
                            st.session_state["authenticated"] = True
                            st.session_state["user_role"] = "Student"
                            st.session_state["username"] = reg_username.strip()
                            st.session_state["full_name"] = reg_name.strip()
                            st.session_state["roll_no"] = reg_roll.strip()
                            st.session_state["department"] = reg_dept.strip()
                            st.success(f"🎉 {msg} Welcome, {reg_name}!")
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")
    st.stop()

# --- SIDEBAR NAVIGATION (ROLE-AWARE) ---
is_student = st.session_state.get("user_role") == "Student"
is_admin = st.session_state.get("user_role") == "Admin"
is_faculty = st.session_state.get("user_role") == "Faculty"

role_icon = "🎓" if is_student else ("👑" if is_admin else "👨‍🏫")
st.sidebar.markdown(f"### {role_icon} {st.session_state.get('full_name', st.session_state['username'])}")
st.sidebar.caption(
    f"Role: **{st.session_state['user_role']}**"
    + (f" | Roll No: **{st.session_state['roll_no']}**" if st.session_state.get("roll_no") else "")
)
st.sidebar.caption(f"Dept: **{st.session_state.get('department', 'Information Technology')}**")
st.sidebar.markdown("---")

if is_student:
    nav_options = [
        "📦 Issue Equipment",
        "📋 My Borrowed Items & History",
        "🔍 Equipment Catalog",
        "🤖 AI Lab Assistant",
        "📊 Dashboard & Analytics",
    ]
elif is_faculty:
    nav_options = [
        "📊 Dashboard & Analytics",
        "🔍 Equipment Inventory",
        "📦 Issue & Return",
        "📑 Reports & CSV Export",
        "🤖 AI Lab Assistant",
    ]
else:  # Admin
    nav_options = [
        "📊 Dashboard & Analytics",
        "🔍 Equipment Inventory",
        "📦 Issue & Return",
        "🛠️ Maintenance & Damage",
        "📑 Reports & CSV Export",
        "🤖 AI Lab Assistant",
    ]

menu = st.sidebar.radio("Navigate", nav_options)

if st.sidebar.button("Logout", use_container_width=True):
    st.session_state["authenticated"] = False
    st.session_state["user_role"] = None
    st.session_state["username"] = None
    st.session_state["full_name"] = None
    st.session_state["roll_no"] = None
    st.session_state["department"] = None
    st.rerun()

# --- M5: DASHBOARD & ANALYTICS ---
if "Dashboard" in menu:
    st.title("Laboratory Dashboard & Real-Time KPIs")

    eq_df = db.get_all_equipment()
    trans_df = db.get_active_issues()
    maint_df = db.get_maintenance_records()

    total_assets = eq_df["total_qty"].sum() if not eq_df.empty else 0
    available_assets = eq_df["available_qty"].sum() if not eq_df.empty else 0
    issued_count = len(trans_df)
    under_repair_count = (
        len(maint_df[maint_df["status"] == "Under Repair"]) if not maint_df.empty else 0
    )
    low_stock_count = len(eq_df[eq_df["available_qty"] < 3]) if not eq_df.empty else 0

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Assets", total_assets)
    k2.metric("Available Stock", available_assets)
    k3.metric("Currently Issued", issued_count)
    k4.metric("Under Repair", under_repair_count)
    k5.metric(
        "Low Stock (<3)",
        low_stock_count,
        delta=-low_stock_count if low_stock_count > 0 else 0,
        delta_color="inverse",
    )

    st.markdown("---")
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Asset Status Overview")
        if total_assets > 0:
            fig, ax = plt.subplots(figsize=(5, 4))
            labels = ["Available", "Issued", "Under Repair"]
            counts = [available_assets, issued_count, under_repair_count]
            colors = ["#28a745", "#ffc107", "#dc3545"]

            # Hide labels on very tiny slices so they don't collide
            def pct_filter(val):
                return f"{val:.1f}%" if val > 2.0 else ""

            wedges, texts, autotexts = ax.pie(
                counts,
                autopct=pct_filter,
                colors=colors,
                startangle=140,
                pctdistance=0.75,
                wedgeprops=dict(width=0.45, edgecolor="w"),  # modern donut style
            )

            # Place labels in a clean legend below the chart
            ax.legend(
                wedges,
                [f"{labels[i]} ({counts[i]})" for i in range(len(labels))],
                loc="upper center",
                bbox_to_anchor=(0.5, -0.05),
                ncol=3,
                frameon=False,
            )
            ax.axis("equal")
            st.pyplot(fig)
        else:
            st.info("No equipment data available.")

    with c2:
        st.subheader("Equipment by Category")
        if not eq_df.empty:
            fig, ax = plt.subplots(figsize=(6, 3.8))
            cat_counts = eq_df.groupby("category")["total_qty"].sum()
            cat_counts.plot(kind="bar", color="#17a2b8", ax=ax)
            ax.set_ylabel("Total Units")
            plt.xticks(rotation=25, ha="right")
            st.pyplot(fig)

# --- M2: EQUIPMENT INVENTORY & CATALOG (FULL CRUD + MULTI-FILTER) ---
elif "Equipment Catalog" in menu or "Equipment Inventory" in menu:
    if is_student:
        st.title("🔍 Laboratory Equipment Catalog")
        st.caption("Browse, search, and inspect all hardware components, microcontrollers, and sensors available across department labs.")
    else:
        st.title("Equipment Catalog & Laboratory Inventory")

    if is_admin:
        tab1, tab2, tab3, tab4 = st.tabs(
            ["View / Search", "Add Equipment", "Edit Equipment", "Delete Equipment"]
        )
    else:
        tab1, = st.tabs(["View / Search Catalog"])
    eq_df = db.get_all_equipment()

    with tab1:
        s1, s2, s3, s4 = st.columns([2, 1, 1, 1])
        search_kw = s1.text_input("Search Name / ID / Brand", key="cat_search_kw")
        filter_cat = s2.selectbox(
            "Filter Category",
            ["All"] + sorted(eq_df["category"].dropna().unique().tolist()),
            key="cat_filter_cat",
        )
        labs_list = sorted(eq_df["lab_name"].dropna().unique().tolist()) if "lab_name" in eq_df.columns else []
        filter_lab = s3.selectbox(
            "Filter Lab",
            ["All"] + labs_list,
            key="cat_filter_lab",
        )
        filter_status = s4.selectbox(
            "Filter Status",
            ["All", "Active", "Under Repair", "Retired"],
            key="cat_filter_status",
        )

        filtered_df = eq_df.copy()
        if search_kw:
            filtered_df = filtered_df[
                filtered_df["name"].str.contains(search_kw, case=False, na=False)
                | filtered_df["equipment_id"].str.contains(
                    search_kw, case=False, na=False
                )
                | filtered_df["brand"].str.contains(search_kw, case=False, na=False)
            ]
        if filter_cat != "All":
            filtered_df = filtered_df[filtered_df["category"] == filter_cat]
        if filter_lab != "All":
            filtered_df = filtered_df[filtered_df["lab_name"] == filter_lab]
        if filter_status != "All":
            filtered_df = filtered_df[filtered_df["status"] == filter_status]

        if is_student:
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Total Components", len(filtered_df))
            k2.metric("Available In Stock", int(filtered_df["available_qty"].sum()) if not filtered_df.empty else 0)
            k3.metric("Total Units Owned", int(filtered_df["total_qty"].sum()) if not filtered_df.empty else 0)
            k4.metric("Labs Represented", filtered_df["lab_name"].nunique() if not filtered_df.empty else 0)

        st.dataframe(filtered_df, use_container_width=True, hide_index=True)

        if is_student:
            st.markdown("---")
            c_info, c_action = st.columns([1.6, 1.4])
            with c_info:
                st.markdown(
                    """
                    <div style="padding: 1.1rem; border-radius: 8px; background: rgba(23, 162, 184, 0.08); border: 1px solid rgba(23, 162, 184, 0.25);">
                        <h4 style="margin: 0; color: #17a2b8;">💡 Looking to Borrow Lab Hardware?</h4>
                        <p style="margin: 0.5rem 0 0 0; font-size: 0.92rem; color: #ccc; line-height: 1.5;">
                            The <strong>Equipment Catalog</strong> is your reference directory to discover available hardware, check technical brands, and verify which lab room holds stock.<br><br>
                            To officially issue and borrow hardware for your practical, mini-project, or capstone, switch to <strong>📦 Issue Equipment</strong> in the navigation sidebar.
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with c_action:
                st.markdown("#### 🔬 Component Details & Location")
                inspect_options = [f"{r['equipment_id']} - {r['name']}" for _, r in filtered_df.iterrows()] if not filtered_df.empty else []
                if inspect_options:
                    selected_inspect = st.selectbox("Select component to inspect:", inspect_options, key="catalog_inspect_sel")
                    insp_id = selected_inspect.split(" - ")[0]
                    insp_row = filtered_df[filtered_df["equipment_id"] == insp_id].iloc[0]
                    avail = int(insp_row["available_qty"])
                    status = insp_row["status"]
                    stock_badge = f"<span style='color: #28a745; font-weight: bold;'>🟢 {avail} In Stock</span>" if avail > 0 and status == "Active" else ("<span style='color: #ffc107; font-weight: bold;'>🟡 Under Repair</span>" if status == "Under Repair" else "<span style='color: #dc3545; font-weight: bold;'>🔴 Out of Stock / Inactive</span>")
                    st.markdown(
                        f"""
                        <div style="font-size: 0.9rem; line-height: 1.7; padding: 0.85rem 1rem; border-radius: 6px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1);">
                            <div><strong>Category:</strong> {insp_row['category']}</div>
                            <div><strong>Manufacturer / Brand:</strong> {insp_row['brand']}</div>
                            <div><strong>Storage Location:</strong> 📍 {insp_row['lab_name']}</div>
                            <div><strong>Current Availability:</strong> {stock_badge} (Total units: {insp_row['total_qty']})</div>
                            <div><strong>Status:</strong> {status}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                else:
                    st.info("No components match the current filter.")

    if is_admin:
        with tab2:
            with st.form("add_form"):
                c1, c2 = st.columns(2)
                e_id = c1.text_input("Equipment ID (e.g., EQ-280)")
                e_name = c2.text_input("Equipment Name")
                e_cat = c1.selectbox(
                    "Category",
                    [
                        "Sensors & Components",
                        "Microcontrollers",
                        "Motors",
                        "Modules",
                        "Displays",
                        "Hardware",
                        "Tools",
                    ],
                )
                e_brand = c2.text_input("Brand", value="Generic")
                e_lab = c1.selectbox(
                    "Lab Name", ["IoT Lab", "Hardware Lab", "Network Lab"]
                )
                e_qty = c2.number_input("Quantity", min_value=1, step=1)
                e_status = c1.selectbox("Status", ["Active", "Under Repair", "Retired"])
                e_pdate = c2.date_input("Purchase Date").strftime("%Y-%m-%d")

                if st.form_submit_button("Add Component"):
                    if e_id and e_name:
                        try:
                            db.add_equipment(
                                e_id,
                                e_name,
                                e_cat,
                                e_brand,
                                e_lab,
                                e_qty,
                                e_status,
                                e_pdate,
                            )
                            st.success(f"Added {e_name} successfully.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

        with tab3:
            selected_id = st.selectbox(
                "Select Equipment ID to Edit", eq_df["equipment_id"].tolist()
            )
            row = eq_df[eq_df["equipment_id"] == selected_id].iloc[0]

            with st.form("edit_form"):
                e_name = st.text_input("Equipment Name", value=row["name"])
                c1, c2 = st.columns(2)
                e_cat = c1.text_input("Category", value=row["category"])
                e_brand = c2.text_input("Brand", value=row["brand"])
                e_lab = c1.selectbox(
                    "Lab Name", ["IoT Lab", "Hardware Lab", "Network Lab"], index=0
                )
                e_status = c2.selectbox(
                    "Status",
                    ["Active", "Under Repair", "Retired"],
                    index=["Active", "Under Repair", "Retired"].index(row["status"]),
                )

                c3, c4 = st.columns(2)
                t_qty = c3.number_input(
                    "Total Quantity", min_value=0, value=int(row["total_qty"])
                )
                a_qty = c4.number_input(
                    "Available Quantity", min_value=0, value=int(row["available_qty"])
                )

                if st.form_submit_button("Update Equipment"):
                    db.update_equipment(
                        selected_id,
                        e_name,
                        e_cat,
                        e_brand,
                        e_lab,
                        t_qty,
                        a_qty,
                        e_status,
                    )
                    st.success("Equipment details updated.")
                    st.rerun()

        with tab4:
            del_id = st.selectbox(
                "Select Item to Delete",
                eq_df["equipment_id"].tolist(),
                key="del_select",
            )
            if st.button("Delete Item Permanently", type="primary"):
                db.delete_equipment(del_id)
                st.success(f"Deleted {del_id}.")
                st.rerun()

# --- STUDENT: ISSUE EQUIPMENT ---
elif "Issue Equipment" in menu:
    st.title("📦 Student Equipment Issue Portal")
    st.caption("Select and issue any active laboratory component for your lab practicals or mini-projects.")

    if st.session_state.get("issue_success_alert"):
        alert_data = st.session_state["issue_success_alert"]
        st.success(
            f"🎉 **{alert_data['name']}** (`{alert_data['id']}`) issued successfully to **{alert_data['student']}** ({alert_data['roll_no']})!"
        )
        st.info(
            f"📍 **Collection Counter:** Please collect your hardware component from the **{alert_data['lab']}** counter by presenting your Student ID."
        )
        if st.button("Dismiss Notification", key="dismiss_issue_alert_btn"):
            del st.session_state["issue_success_alert"]
            st.rerun()

    # Student Identity Profile Card
    st.markdown(
        f"""
        <div style="padding: 1rem 1.25rem; border-radius: 8px; background: rgba(40, 167, 69, 0.1); border: 1px solid rgba(40, 167, 69, 0.3); margin-bottom: 1.5rem;">
            <h4 style="margin: 0; color: #28a745;">🎓 Verified Student Profile</h4>
            <p style="margin: 0.4rem 0 0 0; font-size: 0.95rem;">
                <strong>Name:</strong> {st.session_state.get('full_name')} &nbsp;|&nbsp; 
                <strong>Roll No:</strong> {st.session_state.get('roll_no')} &nbsp;|&nbsp; 
                <strong>Department:</strong> {st.session_state.get('department')}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    avail_eq = db.get_all_equipment()
    avail_eq = avail_eq[(avail_eq["available_qty"] > 0) & (avail_eq["status"] == "Active")]

    if avail_eq.empty:
        st.warning("⚠️ No equipment is currently in stock or available for issue.")
    else:
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            sel_cat = st.selectbox(
                "Filter by Category",
                ["All Categories"] + sorted(avail_eq["category"].unique().tolist()),
                key="stud_issue_cat_filter",
            )
        with f_col2:
            sel_lab = st.selectbox(
                "Filter by Lab Location",
                ["All Labs"] + sorted(avail_eq["lab_name"].unique().tolist()),
                key="stud_issue_lab_filter",
            )

        filtered_avail = avail_eq.copy()
        if sel_cat != "All Categories":
            filtered_avail = filtered_avail[filtered_avail["category"] == sel_cat]
        if sel_lab != "All Labs":
            filtered_avail = filtered_avail[filtered_avail["lab_name"] == sel_lab]

        if filtered_avail.empty:
            st.info("No items match the selected category/lab filter.")
        else:
            with st.form("student_issue_form"):
                eq_options = [
                    f"{row['equipment_id']} - {row['name']} ({row['lab_name']}, {row['available_qty']} in stock)"
                    for _, row in filtered_avail.iterrows()
                ]
                selected_item_str = st.selectbox("Select Hardware Component", eq_options)
                purpose = st.selectbox(
                    "Purpose of Borrowing",
                    [
                        "Mini Project Prototyping",
                        "Department Lab Practical Experiment",
                        "Final Year Capstone Project",
                        "Robotics / IoT Club Activity",
                        "Self Learning / Research",
                    ],
                )
                agree = st.checkbox("I agree to return this component in good condition upon project/practical completion.", value=True)

                issue_submit = st.form_submit_button("🚀 Confirm & Issue Equipment", use_container_width=True, type="primary")

                if issue_submit:
                    if not agree:
                        st.error("Please confirm acceptance of laboratory component return policy.")
                    else:
                        selected_eq_id = selected_item_str.split(" - ")[0]
                        selected_row = avail_eq[avail_eq["equipment_id"] == selected_eq_id].iloc[0]
                        ok, msg = db.issue_equipment(
                            st.session_state.get("full_name"),
                            st.session_state.get("roll_no"),
                            selected_eq_id,
                        )
                        if ok:
                            st.session_state["issue_success_alert"] = {
                                "name": selected_row["name"],
                                "id": selected_eq_id,
                                "student": st.session_state.get("full_name"),
                                "roll_no": st.session_state.get("roll_no"),
                                "lab": selected_row["lab_name"],
                            }
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")

    # Bottom summary of student's active items
    st.markdown("---")
    st.subheader("📌 Equipment Currently in Your Possession")
    s_df = db.get_student_transactions(roll_no=st.session_state.get("roll_no"), student_name=st.session_state.get("full_name"))
    active_s = s_df[s_df["status"] == "Issued"] if not s_df.empty else pd.DataFrame()
    if not active_s.empty:
        st.dataframe(active_s, use_container_width=True, hide_index=True)
    else:
        st.info("You do not have any equipment currently issued. Select an item above to issue!")

# --- STUDENT: MY BORROWED ITEMS & HISTORY ---
elif "My Borrowed Items" in menu:
    st.title("📋 My Borrowed Items & History")
    st.caption("Track all equipment currently issued to you and review past return transactions.")

    s_df = db.get_student_transactions(roll_no=st.session_state.get("roll_no"), student_name=st.session_state.get("full_name"))
    active_items = s_df[s_df["status"] == "Issued"] if not s_df.empty else pd.DataFrame()
    returned_items = s_df[s_df["status"] == "Returned"] if not s_df.empty else pd.DataFrame()

    m1, m2, m3 = st.columns(3)
    m1.metric("Currently in Possession", len(active_items))
    m2.metric("Successfully Returned", len(returned_items))
    m3.metric("Total Items Borrowed", len(s_df) if not s_df.empty else 0)

    st.markdown("---")
    st.subheader("📦 Currently Active Borrowings")
    if not active_items.empty:
        st.dataframe(active_items, use_container_width=True, hide_index=True)
        st.info(
            "ℹ️ **Hardware Return Policy:** To return borrowed components, please submit the physical hardware to the **Lab Attendant or Faculty in-charge** at the department counter. "
            "The attendant will physically inspect the equipment condition (Good / Damaged) and officially record the return in the system."
        )
    else:
        st.success("✅ You have no active equipment borrowings. All items have been returned!")

    st.markdown("---")
    st.subheader("📜 Return History & Past Transactions")
    if not returned_items.empty:
        st.dataframe(returned_items, use_container_width=True, hide_index=True)
    else:
        st.info("No past returned transactions found.")

# --- ADMIN / FACULTY: ISSUE & RETURN ---
elif "Issue & Return" in menu:
    st.title("Equipment Issue & Return Management (Admin / Faculty)")
    tab1, tab2 = st.tabs(["Issue Equipment to Student", "Process Return"])

    with tab1:
        avail_eq = db.get_all_equipment()
        avail_eq = avail_eq[(avail_eq["available_qty"] > 0) & (avail_eq["status"] == "Active")]

        with st.form("admin_issue_form"):
            s_name = st.text_input("Student Full Name")
            roll_no = st.text_input("Roll Number (e.g., 125A3125)")
            selected_eq = st.selectbox(
                "Select Component",
                (
                    avail_eq["equipment_id"] + " - " + avail_eq["name"] + " (" + avail_eq["lab_name"] + ")"
                    if not avail_eq.empty
                    else ["No Available Items"]
                ),
            )

            if st.form_submit_button("Issue Equipment", type="primary"):
                if s_name and roll_no and selected_eq != "No Available Items":
                    eq_id = selected_eq.split(" - ")[0]
                    ok, msg = db.issue_equipment(s_name, roll_no, eq_id)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.warning("Please fill out all fields.")

    with tab2:
        active_df = db.get_active_issues()
        if not active_df.empty:
            st.dataframe(active_df, use_container_width=True)
            with st.form("admin_return_form"):
                t_id = st.selectbox(
                    "Select Transaction ID to Return", active_df["transaction_id"].tolist()
                )
                condition = st.selectbox(
                    "Condition on Return", ["Good", "Damaged", "Lost"]
                )
                if st.form_submit_button("Confirm Return", type="primary"):
                    ok, msg = db.return_equipment(t_id, condition)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
        else:
            st.info("No active issued items currently.")


# --- M4: MAINTENANCE & DAMAGE MANAGEMENT ---
elif "Maintenance" in menu:
    st.title("Maintenance & Repair Tracking")

    eq_df = db.get_all_equipment()
    filter_eq = st.selectbox(
        "Filter History by Component",
        ["All Components"] + eq_df["equipment_id"].tolist(),
    )

    # Call without arguments so it works with any version of database.py
    m_df = db.get_maintenance_records()
    if not m_df.empty and "cost" in m_df.columns:
        m_df = m_df.drop(columns=["cost"])
    if filter_eq != "All Components" and not m_df.empty:
        m_df = m_df[m_df["equipment_id"] == filter_eq]

    st.dataframe(m_df, use_container_width=True)

    pending = m_df[m_df["status"] == "Under Repair"]
    if not pending.empty and st.session_state["user_role"] == "Admin":
        st.subheader("Update Repair Status")
        with st.form("repair_form"):
            r_id = st.selectbox("Repair ID", pending["repair_id"].tolist())
            technician = st.text_input("Technician / Vendor Name")
            status = st.selectbox("Status", ["Under Repair", "Repaired", "Scrapped"])

            if st.form_submit_button("Save Update"):
                db.update_repair(r_id, technician, status)
                st.success("Maintenance log updated.")
                st.rerun()

# --- M6: 6 DEPARTMENTAL REPORTS & EXPORT ---
elif "Reports" in menu:
    st.title("Departmental Audit Reports & Data Export")

    report_type = st.selectbox(
        "Choose Report Type",
        [
            "1. Master Equipment Inventory",
            "2. Currently Borrowed Items",
            "3. Complete Returned History",
            "4. Damaged / Defective Items Log",
            "5. Maintenance Summary",
            "6. Low Stock Reorder List (< 3 Units)",
        ],
    )

    conn = db.get_connection()
    if report_type.startswith("1"):
        df = db.get_all_equipment()
    elif report_type.startswith("2"):
        df = pd.read_sql("SELECT * FROM transactions WHERE status = 'Issued'", conn)
    elif report_type.startswith("3"):
        df = pd.read_sql("SELECT * FROM transactions WHERE status = 'Returned'", conn)
    elif report_type.startswith("4"):
        df = pd.read_sql(
            "SELECT * FROM transactions WHERE condition_on_return = 'Damaged'", conn
        )
    elif report_type.startswith("5"):
        df = pd.read_sql("SELECT * FROM maintenance", conn)
        if "cost" in df.columns:
            df = df.drop(columns=["cost"])
    else:
        df = pd.read_sql("SELECT * FROM equipment WHERE available_qty < 3", conn)
    conn.close()

    st.dataframe(df, use_container_width=True)
    st.download_button(
        label="Download Report as CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=f"{report_type.split('.')[1].strip().lower().replace(' ', '_')}.csv",
        mime="text/csv",
    )

# --- M7: AI LAB ASSISTANT ---
elif "AI Lab Assistant" in menu:
    import difflib

    st.title("AI Lab Assistant & Project BOM Engine")
    st.caption(
        "Natural language query engine mapped dynamically to real-time departmental inventory & stock levels."
    )

    eq_df = db.get_all_equipment()

    PROJECT_TEMPLATES = {
        "Laser Security Alarm System": {
            "description": "Optical tripwire intrusion detection system using a laser diode and photoresistor.",
            "keywords": ["laser", "security", "alarm", "tripwire", "intruder"],
            "parts": [
                ("Laser Module", "Laser Emitter"),
                ("LDR Sensor", "Optical Light Detector"),
                ("Buzzer 5 V", "Audible Alarm Siren"),
                ("Arduino Uno At Mega 328", "Main Controller"),
                ("Relay Module 5V Single", "High-Load Switch / Actuator"),
                ("Breadboard", "Prototyping Board"),
                ("Resistance 220 ohm", "Current Limiting Resistor"),
            ],
            "principle": "The Laser Module aims directly at the LDR. When an intruder breaks the beam, the photoresistor's resistance rises sharply, prompting the Arduino to trigger the 5V Buzzer and switch the Relay Module.",
        },
        "IoT Smart Home & Automation": {
            "description": "Internet of Things system to monitor environmental conditions and remotely toggle AC/DC appliances.",
            "keywords": [
                "iot",
                "smart home",
                "home automation",
                "automation",
                "appliance",
                "remote control",
            ],
            "parts": [
                ("ESP 32", "WiFi & Bluetooth Microcontroller"),
                ("Node MCU Board with Cable", "Alternative IoT Controller"),
                ("5V 4 Channel Relay Module", "Multi-Appliance Switching (AC/DC)"),
                ("DHT 11 Sensor", "Temperature & Humidity Sensor"),
                ("PIR Sensor HC 501", "Passive Infrared Motion Detector"),
                ("LCD 16X2", "Status Display"),
                ("Breadboard", "Prototyping Board"),
                ("Resistance 220 ohm", "Pull-up / Resistors"),
            ],
            "principle": "The ESP32 or NodeMCU reads data from DHT11 and PIR sensors, publishes metrics over WiFi/MQTT, and triggers the 4-channel relay to turn appliances on or off.",
        },
        "Obstacle Avoiding Robot / Autonomous Rover": {
            "description": "Autonomous mobile robot that detects obstacles ahead and steers clear of collisions.",
            "keywords": [
                "obstacle",
                "avoiding",
                "robot",
                "rover",
                "car",
                "autonomous vehicle",
                "chassis",
            ],
            "parts": [
                ("Arduino Uno At Mega 328", "Microcontroller Brain"),
                ("Ultra Sonic Sensor HCSR 04", "Distance / Obstacle Sensor"),
                ("Motor Driver L298N", "Dual H-Bridge Motor Driver"),
                ("BO motor Dual Craft", "DC Gear Motors"),
                ("White Wheels", "Traction Wheels"),
                ("Mini Servo Motor", "Sensor Rotation Turret"),
                ("3X1.5V AA Battery Holder", "Portable DC Power Supply"),
                ("Breadboard", "Wiring & Interconnects"),
            ],
            "principle": "The ultrasonic sensor pings ultrasonic waves forward. When an obstacle is detected closer than 20cm, the Arduino instructs the L298N motor driver to stop, reverse, and turn the chassis.",
        },
        "Line Follower Robot": {
            "description": "Robotic vehicle that follows a marked path on the floor using infrared reflection.",
            "keywords": ["line follower", "track", "line following", "path tracking"],
            "parts": [
                ("Arduino Uno At Mega 328", "Main Controller"),
                ("Line Follower Sensor", "Track Tracking Sensor Array"),
                ("IR Sensor", "Surface Reflectance Detector"),
                ("Motor Driver L298N", "Motor Speed & Direction Driver"),
                ("BO motor Dual Craft", "Dual Drive Motors"),
                ("White Wheels", "Chassis Wheels"),
                ("3X1.5V AA Battery Holder", "Battery Pack"),
            ],
            "principle": "Infrared emitter/photodiode pairs detect track contrast (black absorbs IR, white reflects). The Arduino reads logic levels and adjusts motor PWM speeds to stay on the line.",
        },
        "Weather & Environmental Monitoring Station": {
            "description": "Compact weather station measuring atmospheric pressure, temperature, humidity, and rainfall.",
            "keywords": [
                "weather",
                "meteorology",
                "climate",
                "temperature humidity",
                "rain",
                "bmp180",
                "barometer",
            ],
            "parts": [
                ("ESP 32", "IoT Telemetry Controller"),
                ("DHT 11 Sensor", "Temperature & Humidity Sensor"),
                ("BMP180", "Barometric Pressure & Altitude Sensor"),
                ("Water Rain Drop Sensor", "Precipitation Detector"),
                ("LCD 16X2", "Local Information Display"),
                ("I2C Module", "LCD Serial Backpack"),
                ("Breadboard", "Prototyping"),
            ],
            "principle": "Sensors sample atmospheric conditions every few seconds. The ESP32 parses calibration matrices from the BMP180, reads DHT11 digital pulses, and outputs data to the I2C LCD screen.",
        },
        "Smart Plant Irrigation System": {
            "description": "Automated watering system that hydrates plants whenever soil moisture drops below required levels.",
            "keywords": [
                "irrigation",
                "plant",
                "watering",
                "soil",
                "agriculture",
                "garden",
            ],
            "parts": [
                ("Arduino Uno At Mega 328", "Automation Controller"),
                ("Soil Moisture Sensor", "Soil Moisture Probe"),
                ("Mini Water Pump 3.7 V", "Submersible Water Pump"),
                ("Relay Module 5V Single", "Pump Actuation Switch"),
                ("Buzzer 5 V", "Low Reservoir Alert"),
                ("Breadboard", "Prototyping Board"),
                ("Resistance 220 ohm", "Resistors"),
            ],
            "principle": "The soil moisture sensor measures electrical conductivity between probe pins. When moisture drops below preset thresholds, the Arduino trips the relay to run the mini pump until moisture is restored.",
        },
        "Gas Leakage & Air Quality Alert System": {
            "description": "Hazard detection station for dangerous gas levels (LPG, Methane, Carbon Monoxide, Air Quality).",
            "keywords": [
                "gas",
                "smoke",
                "air quality",
                "leak",
                "lpg",
                "methane",
                "co2",
                "pollution",
            ],
            "parts": [
                ("Arduino Uno At Mega 328", "Main Controller"),
                ("MQ135", "Air Quality / Hazardous Gas Sensor"),
                ("MQ7 Gas Sensor", "Carbon Monoxide Sensor"),
                ("MQ4 Methane Gas", "Methane / CNG Sensor"),
                ("Buzzer 5 V", "Acoustic Warning Siren"),
                ("LCD 16X2", "Gas Concentration Display"),
                ("LED 5 MM", "Visual Warning Indicator"),
                ("Breadboard", "Circuit Board"),
            ],
            "principle": "The MQ gas sensors tin dioxide (SnO2) coating changes electrical resistance in the presence of combustible gases. The Arduino calculates PPM and immediately triggers audio and visual warnings.",
        },
        "RFID Smart Attendance & Access Control": {
            "description": "Contactless identification system for automated student attendance or digital door locking.",
            "keywords": [
                "rfid",
                "attendance",
                "access control",
                "smart card",
                "door lock",
                "identity",
            ],
            "parts": [
                ("Arduino Uno At Mega 328", "Processing Unit"),
                ("Low Frequency RFID Detector RC522", "RFID Card Reader"),
                ("RFID CARD EM18", "Passive RFID Transponder Card"),
                ("LCD 16X2", "User Message Display"),
                ("Buzzer 5 V", "Scan Confirmation Tone"),
                ("Relay Module 5V Single", "Electronic Lock Control"),
                ("Breadboard", "Prototyping"),
            ],
            "principle": "When an RFID card enters the 13.56MHz electromagnetic field, it transmits its unique tag ID to the RC522. The Arduino validates the ID against stored roll numbers and marks attendance.",
        },
        "Patient Health Monitoring (Heart Rate & SpO2)": {
            "description": "Biomedical telemetry system for tracking heart pulse, oxygen saturation, and ECG signals.",
            "keywords": [
                "health",
                "heart",
                "pulse",
                "oximeter",
                "spo2",
                "ecg",
                "patient",
                "medical",
                "vital",
            ],
            "parts": [
                ("ESP 32", "Microcontroller & WiFi Gateway"),
                (
                    "MAX 30102 Pulse Oximeter Sensor",
                    "Optical Heart Rate & SpO2 Sensor",
                ),
                ("Heart Beat Pulse Sensor", "Fingerprint Pulse Detector"),
                ("ECG Monitoring AdraXX ADD 8232", "Electrocardiogram Biosensor"),
                ("LCD 16X2", "Real-Time Vitals Display"),
                ("Buzzer 5 V", "Tachycardia / Bradycardia Alarm"),
                ("Breadboard", "Prototyping"),
            ],
            "principle": "Infrared and red light absorption through vascular tissue determines blood oxygen level (SpO2) and calculates heart rate in beats per minute (BPM), displaying stats on the screen.",
        },
        "GPS & GSM Vehicle / Asset Tracker": {
            "description": "Geographical location monitor capable of transmitting live GPS coordinates over cellular SMS/data.",
            "keywords": [
                "gps",
                "gsm",
                "tracker",
                "tracking",
                "sms",
                "location",
                "vehicle tracker",
            ],
            "parts": [
                ("Arduino Uno At Mega 328", "Microcontroller"),
                ("GPS Module Neo 6M", "Satellite Receiver"),
                ("GSM Module Sim 800L", "Cellular Radio & SMS Module"),
                ("10 K Pot", "Tuning Potentiometer"),
                ("Breadboard", "Prototyping"),
            ],
            "principle": "The Neo-6M GPS antenna receives satellite ephemeris data and computes latitude/longitude. Upon receiving an inquiry SMS or trigger, the Arduino responds with a Google Maps link via SIM800L.",
        },
        "Smart Surveillance & Edge Vision System": {
            "description": "Video surveillance station with motion-triggered capture using a Raspberry Pi camera module.",
            "keywords": [
                "camera",
                "vision",
                "surveillance",
                "opencv",
                "cctv",
                "image processing",
                "face recognition",
                "raspberry pi",
            ],
            "parts": [
                ("Raspberry Pi 3 Model B", "Single Board Edge Computer"),
                ("Raspberry Pi Camera", "HD Video Capture Sensor"),
                ("ESP 32 Cam Module", "Alternative Embedded Camera"),
                ("PIR Sensor HC 501", "Motion Activation Sensor"),
                ("Micro HDMI to HDMI Cable", "Video Display Cable"),
                ("Type C Cable", "Power Supply Cable"),
            ],
            "principle": "When the PIR sensor detects human movement, it signals the Raspberry Pi to start recording high-definition video through the camera module and archive frames.",
        },
    }

    def get_component_inventory_status(part_query, current_eq_df):
        match = current_eq_df[
            current_eq_df["name"].str.lower() == part_query.lower()
        ]
        if match.empty:
            match = current_eq_df[
                current_eq_df["name"].str.contains(part_query, case=False, na=False)
            ]
        if match.empty:
            words = [w for w in part_query.lower().split() if len(w) > 2]
            for w in words:
                sub = current_eq_df[
                    current_eq_df["name"].str.contains(w, case=False, na=False)
                ]
                if not sub.empty:
                    match = sub
                    break

        if not match.empty:
            item = match.iloc[0]
            avail = int(item["available_qty"])
            total = int(item["total_qty"])
            location = item["lab_name"]
            item_id = item["equipment_id"]
            item_name = item["name"]

            if avail > 2:
                status_badge = "🟢 In Stock (Ready to Issue)"
                is_avail = True
            elif avail > 0:
                status_badge = f"🟡 Low Stock (Only {avail} left)"
                is_avail = True
            else:
                status_badge = "🔴 Out of Stock"
                is_avail = False

            return {
                "Equipment ID": item_id,
                "Component": item_name,
                "Available Stock": f"{avail} / {total} units",
                "Lab Location": location,
                "Availability Status": status_badge,
                "is_available": is_avail,
                "avail_count": avail,
            }
        return {
            "Equipment ID": "N/A",
            "Component": part_query,
            "Available Stock": "0 units",
            "Lab Location": "Check Lab Attendant",
            "Availability Status": "⚠️ Check Lab Attendant",
            "is_available": False,
            "avail_count": 0,
        }

    def render_project_bom_view(project_title, project_info, current_eq_df):
        st.subheader(f"🎯 Project Bill of Materials: {project_title}")
        st.markdown(f"*{project_info['description']}*")

        rows = []
        total_parts = len(project_info["parts"])
        in_stock_parts = 0

        for part_name, role in project_info["parts"]:
            stat = get_component_inventory_status(part_name, current_eq_df)
            if stat["is_available"]:
                in_stock_parts += 1
            rows.append(
                {
                    "Equipment ID": stat["Equipment ID"],
                    "Component": stat["Component"],
                    "Role in Project": role,
                    "Available Stock": stat["Available Stock"],
                    "Lab Location": stat["Lab Location"],
                    "Availability Status": stat["Availability Status"],
                }
            )

        # KPI Summary cards
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Required Items", total_parts)
        k2.metric("Available in Lab", f"{in_stock_parts} / {total_parts}")
        k3.metric("Missing / Out of Stock", total_parts - in_stock_parts)
        pct = int((in_stock_parts / total_parts) * 100) if total_parts > 0 else 0
        readiness_label = "100% Ready ✅" if in_stock_parts == total_parts else f"{pct}% Ready ⚠️"
        k4.metric("Lab Readiness", readiness_label)

        missing_count = total_parts - in_stock_parts
        if missing_count > 0:
            st.error(
                f"❌ **Stock Alert:** {missing_count} required component(s) are currently **NOT available / Out of Stock** in the lab."
            )
        else:
            st.success(
                "✅ **All Components Available:** All required items for this project are currently in stock and ready to issue."
            )

        st.markdown("##### 📦 Real-Time Equipment Availability & Location")
        df_bom = pd.DataFrame(rows)
        st.dataframe(df_bom, use_container_width=True, hide_index=True)

        if "principle" in project_info:
            st.info(f"💡 **Working Principle:** {project_info['principle']}")

        if is_student:
            avail_rows = [r for r in rows if "In Stock" in r["Availability Status"] or "Low Stock" in r["Availability Status"]]
            if avail_rows:
                st.markdown("##### ⚡ Quick Issue Project Component")
                p_c1, p_c2 = st.columns([3, 1])
                with p_c1:
                    chosen_p = st.selectbox(
                        "Select in-stock component for this project to issue to your account:",
                        [f"{r['Equipment ID']} - {r['Component']} ({r['Lab Location']})" for r in avail_rows],
                        key=f"bom_quick_issue_{project_title}",
                    )
                with p_c2:
                    st.write("")
                    st.write("")
                    if st.button("🚀 Issue Component", key=f"btn_p_issue_{project_title}", type="primary", use_container_width=True):
                        p_eq_id = chosen_p.split(" - ")[0]
                        ok, msg = db.issue_equipment(st.session_state.get("full_name"), st.session_state.get("roll_no"), p_eq_id)
                        if ok:
                            st.success(f"🎉 Component issued successfully to {st.session_state.get('full_name')} ({st.session_state.get('roll_no')})!")
                            st.rerun()
                        else:
                            st.error(msg)

    import re

    def clean_query_term(text):
        t = text.strip()
        t = re.sub(r"[?!.,;:]", "", t)
        changed = True
        while changed:
            prev = t
            t = re.sub(
                r"^(do we have|is there any|are there any|can i get|can we get|do you have|is|are|tell me if|check if|check|find|show me|search for|what about|any info on|we need|i need|do we got)\s+",
                "",
                t,
                flags=re.IGNORECASE,
            ).strip()
            t = re.sub(
                r"\s+(is|are|available|in stock|in lab|in the lab|present|there|here|in department|for project|for projects)$",
                "",
                t,
                flags=re.IGNORECASE,
            ).strip()
            changed = t != prev
        return t

    def find_matching_project(prompt, templates):
        p_clean = prompt.lower()
        best_match = None
        max_score = 0
        for title, info in templates.items():
            score = 0
            for w in title.lower().split():
                if len(w) > 3 and w in p_clean:
                    score += 2
            for kw in info["keywords"]:
                if kw in p_clean:
                    score += 3
            if score > max_score:
                max_score = score
                best_match = (title, info)
        if max_score >= 3:
            return best_match
        return None

    def extract_mentioned_components(prompt, current_eq_df):
        p_clean = prompt.lower()
        matched_items = []
        sorted_eq = current_eq_df.sort_values(
            by="name", key=lambda col: col.str.len(), ascending=False
        )
        for _, row in sorted_eq.iterrows():
            name = row["name"].lower()
            eq_id = row["equipment_id"].lower()
            if eq_id in p_clean or name in p_clean:
                matched_items.append(row)
        if matched_items:
            return pd.DataFrame(matched_items).drop_duplicates(
                subset=["equipment_id"]
            )
        return pd.DataFrame()

    # --- CHATBOT SEARCH INPUT ---
    user_prompt = st.text_input(
        "Ask the AI Lab Assistant about equipment availability, component stock, storage location, or project requirements:",
        placeholder="e.g. Is drone available? / Do we have ESP32? / What equipments are needed for obstacle avoiding robot?",
    )

    st.markdown("---")

    if eq_df.empty:
        st.warning("Inventory records are empty.")
    elif user_prompt:
        p = user_prompt.strip().lower()

        matched_proj = find_matching_project(p, PROJECT_TEMPLATES)
        if matched_proj:
            title, info = matched_proj
            render_project_bom_view(title, info, eq_df)

        elif any(
            term in p
            for term in [
                "project",
                "equipments",
                "needed",
                "components needed",
                "materials",
                "bom",
                "what equipments",
            ]
        ):
            st.info(
                "🤖 **Which project would you like to check?**\n\n"
                "We have ready-to-build Bill of Materials mapped to our departmental stock. "
                "Select one of the projects below or specify the project topic in your query:"
            )
            proj_cols = st.columns(3)
            for idx, t_name in enumerate(PROJECT_TEMPLATES.keys()):
                with proj_cols[idx % 3]:
                    if st.button(t_name, key=f"btn_{idx}", use_container_width=True):
                        st.session_state["chosen_proj"] = t_name
                        st.rerun()

            if "chosen_proj" in st.session_state:
                render_project_bom_view(
                    st.session_state["chosen_proj"],
                    PROJECT_TEMPLATES[st.session_state["chosen_proj"]],
                    eq_df,
                )

        else:
            # Check if multiple components are mentioned
            comp_matches = extract_mentioned_components(p, eq_df)
            if not comp_matches.empty:
                st.subheader("🔍 Matching Equipment Availability")
                display_rows = []
                has_unavailable = False
                for _, row in comp_matches.iterrows():
                    avail = int(row["available_qty"])
                    total = int(row["total_qty"])
                    if avail > 2:
                        status_str = "🟢 Available"
                    elif avail > 0:
                        status_str = f"🟡 Low Stock ({avail} left)"
                    else:
                        status_str = "🔴 NOT Available (Out of Stock)"
                        has_unavailable = True

                    display_rows.append(
                        {
                            "Equipment ID": row["equipment_id"],
                            "Component Name": row["name"],
                            "Category": row["category"],
                            "Available Stock": f"{avail} / {total} units",
                            "Lab Location": row["lab_name"],
                            "Status": status_str,
                        }
                    )
                if has_unavailable:
                    st.error("❌ **One or more of the requested items are currently NOT available / out of stock.**")
                else:
                    st.success("✅ **All requested items found are in stock and ready to issue.**")

                st.dataframe(
                    pd.DataFrame(display_rows),
                    use_container_width=True,
                    hide_index=True,
                )

                if is_student:
                    avail_multi = comp_matches[comp_matches["available_qty"] > 0]
                    if not avail_multi.empty:
                        st.markdown("##### ⚡ Quick Issue Found Component")
                        m_c1, m_c2 = st.columns([3, 1])
                        with m_c1:
                            m_choice = st.selectbox(
                                "Select item to issue to your account:",
                                [f"{r['equipment_id']} - {r['name']} ({r['available_qty']} in {r['lab_name']})" for _, r in avail_multi.iterrows()],
                                key="multi_issue_sel",
                            )
                        with m_c2:
                            st.write("")
                            st.write("")
                            if st.button("🚀 Issue to My Account", key="multi_issue_btn", type="primary", use_container_width=True):
                                m_id = m_choice.split(" - ")[0]
                                ok, msg = db.issue_equipment(st.session_state.get("full_name"), st.session_state.get("roll_no"), m_id)
                                if ok:
                                    st.success(f"🎉 Item issued successfully to {st.session_state.get('full_name')} ({st.session_state.get('roll_no')})!")
                                    st.rerun()
                                else:
                                    st.error(msg)

            else:
                # Single component match
                all_names = eq_df["name"].tolist()
                matched_row = None

                p_norm = p.replace(" ", "").replace("-", "")
                for name in all_names:
                    name_norm = name.lower().replace(" ", "").replace("-", "")
                    if name_norm in p_norm or p_norm in name_norm:
                        matched_row = eq_df[eq_df["name"] == name].iloc[0]
                        break

                if matched_row is None:
                    for name in all_names:
                        keywords = [w for w in name.lower().split() if len(w) > 2]
                        if any(w in p for w in keywords) or name.lower() in p:
                            matched_row = eq_df[eq_df["name"] == name].iloc[0]
                            break

                if matched_row is None:
                    user_words = [
                        w
                        for w in p.replace("?", "").replace(",", "").split()
                        if len(w) > 3
                    ]
                    for word in user_words:
                        close = difflib.get_close_matches(
                            word, [n.lower() for n in all_names], n=1, cutoff=0.5
                        )
                        if close:
                            matched_row = eq_df[
                                eq_df["name"].str.lower() == close[0]
                            ].iloc[0]
                            break

                if matched_row is not None:
                    item_name = matched_row["name"]
                    avail = int(matched_row["available_qty"])
                    total = int(matched_row["total_qty"])
                    lab = matched_row["lab_name"]

                    if avail > 0:
                        status_str = "🟢 Ready to Issue" if avail > 2 else f"🟡 Low Stock ({avail} left)"
                        st.success(
                            f"✅ **Equipment Available:** **{item_name}** (`{matched_row['equipment_id']}`) is **IN STOCK** and available for issue.\n\n"
                            f"- **Available Quantity:** {avail} of {total} units\n"
                            f"- **Storage Location:** {lab}\n"
                            f"- **Category:** {matched_row['category']}\n"
                            f"- **Status:** {status_str}"
                        )
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Available Stock", f"{avail} / {total} units")
                        col2.metric("Storage Location", lab)
                        col3.metric("Status", status_str)

                        if is_student:
                            if st.button(f"🚀 Issue {item_name} to My Account", key=f"ai_quick_issue_{matched_row['equipment_id']}", type="primary"):
                                ok, msg = db.issue_equipment(st.session_state.get("full_name"), st.session_state.get("roll_no"), matched_row['equipment_id'])
                                if ok:
                                    st.success(f"🎉 {item_name} issued successfully to {st.session_state.get('full_name')} ({st.session_state.get('roll_no')})!")
                                    st.rerun()
                                else:
                                    st.error(msg)
                    else:
                        st.error(
                            f"❌ **Equipment NOT Available (Out of Stock):** **{item_name}** (`{matched_row['equipment_id']}`) is currently **NOT available** in the lab.\n\n"
                            f"- **Available Quantity:** 0 of {total} units\n"
                            f"- **Storage Location:** {lab}\n"
                            f"- **Category:** {matched_row['category']}\n"
                            f"- **Status:** 🔴 All units are currently borrowed or under repair."
                        )
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Available Stock", f"0 / {total} units")
                        col2.metric("Storage Location", lab)
                        col3.metric("Status", "Out of Stock")
                else:
                    # Equipment is NOT in inventory
                    searched_name = clean_query_term(user_prompt)
                    query_display = searched_name.title() if searched_name else user_prompt
                    st.error(
                        f"❌ **Equipment NOT Available:** **'{query_display}'** is **NOT available** in the laboratory inventory.\n\n"
                        f"This item is not stocked or registered in any departmental lab (IoT Lab, Hardware Lab, Network Lab). "
                        "Please check with the lab attendant or faculty in-charge if your project requires this equipment."
                    )


