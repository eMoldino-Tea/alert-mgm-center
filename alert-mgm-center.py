import streamlit as st
import pandas as pd
import datetime
import os
import tempfile
import random

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Alert Management Center | eMoldino Service",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- GRACEFUL LIBRARY IMPORTS ---
try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False

try:
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# --- SESSION STATE INITIALIZATION ---
if 'admin_log' not in st.session_state:
    st.session_state.admin_log = pd.DataFrame(columns=[
        "Timestamp", "Server", "Users", "Alert Type", "Target Scope (Filters)", "Configuration details"
    ])

# Initialize robust mock client alerts to perfectly populate the 3-Tier chart visualizations
if 'client_alerts_db' not in st.session_state:
    mock_data = []
    distributions = [
        ("Cycle Time", [("Level 1", 45, "4%"), ("Level 2", 14, "10%"), ("Level 3", 5, "18%")]),
        ("Low Run Rate - Shot Efficiency", [("Level 1", 50, "80%"), ("Level 2", 22, "70%"), ("Level 3", 8, "55%")]),
        ("Low Run Rate - Time Stability", [("Level 1", 60, "82%"), ("Level 2", 15, "65%"), ("Level 3", 4, "50%")]),
        ("Capacity Risk (Optimal)", [("Level 1", 80, "4%"), ("Level 2", 12, "10%"), ("Level 3", 3, "18%")]),
        ("Capacity Risk (Target)", [("Level 1", 75, "3%"), ("Level 2", 18, "8%"), ("Level 3", 7, "15%")]),
        ("Tooling EOL (Utilization)", [("Level 1", 40, "75%"), ("Level 2", 10, "85%"), ("Level 3", 5, "95%")]),
        ("Operation Status (Sensor Offline)", [("Status", 7, "2026-04-28 08:00:00")]),
        ("Operation Status (Sensor Detached)", [("Status", 2, "2026-04-28 09:00:00")]),
        ("Operation Status (Inactive)", [("Status", 19, "2026-04-28 10:00:00")])
    ]
    
    alert_id_counter = 1000
    for a_type, dist in distributions:
        for row_config in dist:
            sev = row_config[0]
            count = row_config[1]
            metric = row_config[2]
            for _ in range(count):
                mock_data.append({
                    "Alert ID": f"ALT-{alert_id_counter}",
                    "Alert Name": f"{a_type.split('(')[0].strip()} Alert",
                    "Date/Time": (datetime.datetime(2026, 4, 28, 10, 0) - datetime.timedelta(days=random.randint(0, 5), hours=random.randint(1,20))).strftime("%Y-%m-%d %H:%M:%S"),
                    "Frequency": random.choice(["Hourly", "Daily", "Weekly", "Monthly"]),
                    "Tool": f"Tool_{random.choice('ABCDEFGH')}",
                    "Part": f"Part 10{random.randint(1,9)}",
                    "Supplier": random.choice(["Supplier X", "Supplier Y", "Supplier Z"]),
                    "Plant": random.choice(["Plant 1", "Plant 2", "Plant 3"]),
                    "Tooling Type": random.choice(["Injection", "Stamping", "Die Casting"]),
                    "OEM Division": random.choice(["Div A", "Div B", "Div C"]),
                    "Severity": sev,
                    "Alert Type": a_type,
                    "Metric_1": metric,
                    "Metric_2": "",
                    "Status": "Open",
                    "Owner": "Unassigned"
                })
                alert_id_counter += 1
    st.session_state.client_alerts_db = pd.DataFrame(mock_data)

if 'client_portal_view' not in st.session_state:
    st.session_state.client_portal_view = "list"
if 'selected_alert_id' not in st.session_state:
    st.session_state.selected_alert_id = None

# --- CUSTOM STYLING ---
st.markdown("""
    <style>
    .main-header { font-size: 2.5rem; font-weight: bold; color: #1E3A8A; margin-bottom: 0px; }
    .sub-header { font-size: 1.2rem; color: #6B7280; margin-bottom: 2rem; }
    .level-box { padding: 15px; border-radius: 8px; margin-top: 10px; }
    .metric-card { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 20px; margin-bottom: 15px; }
    .metric-title { color: #64748B; font-size: 0.95rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 5px; }
    .metric-value { color: #0F172A; font-size: 1.8rem; font-weight: bold; }
    
    /* Action Command Center Cards */
    .action-card { background-color: white; border-top: 4px solid #EF4444; border-left: 1px solid #E2E8F0; border-right: 1px solid #E2E8F0; border-bottom: 1px solid #E2E8F0; border-radius: 8px; padding: 20px; margin-bottom: 15px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
    .action-card-warning { border-top: 4px solid #F59E0B; }
    .risk-score-badge { float: right; background-color: #FEE2E2; color: #991B1B; padding: 4px 10px; border-radius: 20px; font-weight: bold; font-size: 0.9rem; }
    .risk-score-warning { background-color: #FEF3C7; color: #92400E; }
    .card-tool { font-size: 1.3rem; font-weight: bold; color: #1E293B; margin-bottom: 5px;}
    .card-context { font-size: 0.95rem; color: #475569; margin-bottom: 15px; }
    </style>
""", unsafe_allow_html=True)

# --- HELPER TO DISPLAY COLORED LEVEL BOXES ---
def display_level_box(level_idx, markdown_text):
    if level_idx == 0: st.info(markdown_text)
    elif level_idx == 1: st.warning(markdown_text)
    else: st.error(markdown_text)

# --- RISK ENGINE ---
def calculate_risk_index(row):
    """Calculates a 1-100 Risk Score based on Severity, Impact, and Time Unresolved"""
    score = 10
    
    # 1. Severity Weight
    if row['Severity'] == "Level 3": score += 40
    elif row['Severity'] == "Level 2": score += 20
    elif row['Severity'] == "Level 1": score += 10
    elif row['Severity'] in ["Event", "Status"]: score += 15
    
    # 2. Impact Weight
    if "Capacity Risk" in row['Alert Type']: score += 30
    elif "Run Rate" in row['Alert Type']: score += 20
    elif "Cycle Time" in row['Alert Type']: score += 15
    elif "EOL" in row['Alert Type']: score += 10
    elif "Operation Status" in row['Alert Type']: score += 20
    
    # 3. Time Decay (Simulated by extracting days from timestamp)
    days_old = (datetime.datetime(2026, 4, 28, 10, 0) - pd.to_datetime(row['Date/Time'])).days
    score += (days_old * 3)
    
    return min(int(score), 99) # Cap at 99

# --- EXECUTIVE POWER-BI STYLE PDF GENERATOR ---
def generate_fpdf_report(df):
    def clean(text):
        text = str(text).replace('≤', '<=').replace('≥', '>=')
        return text.encode('latin-1', 'replace').decode('latin-1')
        
    class PDF(FPDF):
        def header(self):
            self.set_fill_color(30, 58, 138)
            self.rect(0, 0, 297, 20, 'F')
            self.set_y(6)
            self.set_font('Arial', 'B', 16)
            self.set_text_color(255, 255, 255)
            self.cell(10)
            self.cell(150, 8, clean('eMoldino Alert Management | Executive Summary'), 0, 0, 'L')
            self.set_font('Arial', '', 10)
            self.cell(120, 8, clean(f'Generated: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}'), 0, 1, 'R')
            self.ln(10)
            
    pdf = PDF('L', 'mm', 'A4')
    pdf.add_page()
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(0, 10, "ACTIVE ALERTS DIRECTORY", 0, 1, 'L')
    pdf.ln(2)
    
    pdf.set_font('Arial', 'B', 9)
    pdf.set_fill_color(30, 58, 138)
    pdf.set_text_color(255, 255, 255)
    
    cols = ["Alert Name", "Alert Type", "Plant", "Tooling / Part", "Level 1 Cond", "Status"]
    col_widths = [30, 40, 30, 60, 80, 30] 
    
    for i in range(len(cols)):
        pdf.cell(col_widths[i], 8, clean(cols[i]), 1, 0, 'C', 1)
    pdf.ln()
    
    pdf.set_font('Arial', '', 8)
    pdf.set_text_color(0, 0, 0)
    
    for _, row in df.iterrows():
        pdf.cell(col_widths[0], 8, clean(str(row["Alert Name"])[:20]), 1)
        pdf.cell(col_widths[1], 8, clean(str(row["Alert Type"])[:25]), 1)
        pdf.cell(col_widths[2], 8, clean(str(row["Plant"])[:20]), 1)
        pdf.cell(col_widths[3], 8, clean(str(row["Tooling / Part"])[:40]), 1)
        pdf.cell(col_widths[4], 8, clean(str(row["Level 1 Condition"])[:50]), 1)
        pdf.cell(col_widths[5], 8, clean(str(row["Status"])), 1)
        pdf.ln()
        
    try:
        return bytes(pdf.output())
    except TypeError:
        return pdf.output(dest='S').encode('latin-1')

# --- REUSABLE FILTER FUNCTION ---
def render_filters(key_prefix):
    st.caption("Select desired filters first to define the target scope. Leave empty to apply globally.")
    oem = st.multiselect("OEM Business Division", ["Div A", "Div B", "Div C"], key=f"{key_prefix}_oem")
    sup = st.multiselect("Supplier", ["Supplier X", "Supplier Y", "Supplier Z"], key=f"{key_prefix}_sup")
    plt = st.multiselect("Plant", ["Plant 1", "Plant 2", "Plant 3"], key=f"{key_prefix}_plt")
    prod = st.multiselect("Product", ["Product Alpha", "Product Beta"], key=f"{key_prefix}_prod")
    ttype = st.multiselect("Tooling Type", ["Injection", "Stamping", "Die Casting"], key=f"{key_prefix}_type")
    part = st.multiselect("Part", ["Part 101", "Part 102", "Part 103"], key=f"{key_prefix}_part")
    tool = st.multiselect("Tooling", ["Tool_A", "Tool_B", "Tool_C", "Tool_D"], key=f"{key_prefix}_tool")
            
    return {"OEM": oem, "Supplier": sup, "Plant": plt, "Product": prod, "Tooling Type": ttype, "Part": part, "Tooling": tool}

def log_admin_action(alert_type, filters, selected_server, selected_users, details="Configured successfully"):
    if not selected_users:
        st.error("⚠️ Please select at least one user from the User Assignment panel before saving.")
        return
    active_filters = {k: v for k, v in filters.items() if v}
    filter_str = " | ".join([f"{k}: {', '.join(v)}" for k, v in active_filters.items()])
    if not filter_str:
        filter_str = "Global (No filters applied)"
    users_str = ", ".join(selected_users)
    new_log = pd.DataFrame([{
        "Timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Server": selected_server,
        "Users": users_str,
        "Alert Type": alert_type,
        "Target Scope (Filters)": filter_str,
        "Configuration details": details
    }])
    st.session_state.admin_log = pd.concat([new_log, st.session_state.admin_log], ignore_index=True)
    st.success(f"Successfully programmed '{alert_type}' alert for {len(selected_users)} user(s) on {selected_server}!")

# ==========================================
#         SIDEBAR: NAVIGATION & FILTERS
# ==========================================
with st.sidebar:
    st.markdown("### Navigation")
    page = st.radio("Go to:", ["Configuration Management", "Global Dashboard", "Client Alerts Portal"])
    st.divider()

    if page == "Configuration Management":
        st.markdown("### User Assignment")
        selected_server = st.selectbox("Target Server", ["JLR Server", "GM Server", "Paccar Server"])
        
        mock_users = {
            "JLR Server": ["Alex Carter (alex.carter@jlr.com)", "Jane Smith (jane.smith@jlr.com)", "Mark Davis (m.davis@jlr.com)"],
            "GM Server": ["Mike Johnson (mjohnson@gm.com)", "Sarah Connor (sconnor@gm.com)", "Tom Wilson (twilson@gm.com)"],
            "Paccar Server": ["David Lee (d.lee@paccar.com)", "Emma Wilson (e.wilson@paccar.com)", "Chris Taylor (ctaylor@paccar.com)"]
        }
        selected_users = st.multiselect("Select User(s)", mock_users[selected_server], default=[mock_users[selected_server][0]])
        st.divider()
        st.markdown("### Target Data Filters")
        user_filters = render_filters("admin_filters")

    elif page == "Client Alerts Portal":
        st.markdown("### Target Data Filters")
        client_filters = render_filters("client_filters")

# ==========================================
#              MAIN CONTENT
# ==========================================

if page == "Configuration Management":
    # Top Header & Export Button
    header_col, export_col = st.columns([5, 1])

    with header_col:
        st.markdown('<div class="main-header">Alert Configuration Management</div>', unsafe_allow_html=True)
        st.markdown('<div class="sub-header">eMoldino Service Center | Manage alert configurations centrally.</div>', unsafe_allow_html=True)
        
    with export_col:
        st.write("")
        st.write("")
        
        with st.popover("📥 Export Config", use_container_width=True):
            st.caption(f"Export or email configuration summary for **{len(selected_users)} selected user(s)**.")
            
            dummy_alerts_df = pd.DataFrame({
                "Alert Name": ["Cycle Time Dev Tool A", "Low Run Rate Tool B", "Capacity Risk Tool D", "EOL Tool C", "Status Sensor Offline"],
                "Alert Type": ["Cycle Time", "Run Rate", "Capacity Risk", "Tooling EOL", "Operation Status"],
                "Plant": ["Plant 1", "All", "Plant 2", "All", "Plant 3"],
                "Tooling / Part": ["Tool_A", "All", "Product Alpha", "Part 101", "Tool_C"],
                "Level 1 Condition": ["0% ≤ dev ≤ 5%", "80% ≤ RR ≤ 100%", "0% ≤ loss ≤ 5%", "80% ≤ shots ≤ 90%", "Sensor Offline"],
                "Status": ["Active", "Active", "Inactive", "Active", "Active"],
            })

            export_format = st.radio("Format", ["CSV", "PDF"], horizontal=True, label_visibility="collapsed")
            
            if export_format == "CSV":
                export_data = dummy_alerts_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="⬇️ Download CSV",
                    data=export_data,
                    file_name=f"assigned_alerts_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            else:
                if FPDF_AVAILABLE and MATPLOTLIB_AVAILABLE:
                    export_data = generate_fpdf_report(dummy_alerts_df)
                    st.download_button(
                        label="⬇️ Download PDF Report",
                        data=export_data,
                        file_name=f"assigned_alerts_{datetime.datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                else:
                    st.warning("⚠️ FPDF or Matplotlib library missing. Run `pip install fpdf matplotlib`.")
            
            st.divider()
            st.write("✉️ Send to Email")
            email_input = st.text_input("Email Address", value="admin.plant@emoldino.com", label_visibility="collapsed")
            
            if st.button("Send Now", type="primary", use_container_width=True):
                st.success(f"Sent to {email_input}!")

    # Tabs taking full width
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Cycle Time", 
        "Run Rate", 
        "Capacity Risk", 
        "Tooling End of Life", 
        "Operation Status"
    ])

    # --- 1. CYCLE TIME ---
    with tab1:
        st.subheader("Cycle Time Alerts")
        st.write("Alerts based on absolute deviation (±%) from target cycle time to detect both slow and fast production anomalies.")
        ct_enabled = st.toggle("Enable Cycle Time Alerts", value=True, key="ct_toggle")
        if ct_enabled:
            with st.container(border=True):
                st.markdown("##### Configuration: Number of Levels")
                ct_num = st.number_input("How many alert levels do you want to configure?", min_value=1, max_value=5, value=2, key="ct_num_levels")
                st.markdown("##### Deviation Threshold Boundaries")
                st.write("Set the deviation limits for each level.")
                ct_limits = []
                prev_val = 0
                ct_cols = st.columns(ct_num)
                for i in range(ct_num):
                    with ct_cols[i]:
                        c_min = min(200, prev_val + 1)
                        def_val = min(200, max(c_min, prev_val + 5))
                        val = st.number_input(f"Level {i+1} Limit (±%)", min_value=c_min, max_value=200, value=def_val, key=f"ct_limit_{i}")
                        ct_limits.append(val)
                        prev_val = val
                st.markdown("##### Alert Conditions Summary")
                ct_disp_cols = st.columns(ct_num)
                for i in range(ct_num):
                    with ct_disp_cols[i]:
                        lower = 0 if i == 0 else ct_limits[i-1]
                        upper = ct_limits[i]
                        op = "≤" if i == 0 else "<"
                        txt = f"**Level {i+1}**\n\nTriggers when absolute deviation is between **{lower}% and {upper}%**.\n\n`(CT exceeds Target by ±{lower}% to ±{upper}%)`"
                        display_level_box(i, txt)
                st.divider()
                ct_freq = st.selectbox("Alert Frequency", ["Hourly", "Daily", "Weekly", "Monthly"], key="ct_freq")
            if st.button("Save Cycle Time Settings", type="primary"):
                log_admin_action("Cycle Time", user_filters, selected_server, selected_users)

    # --- 2. RUN RATE ---
    with tab2:
        st.subheader("Run Rate Alerts")
        st.write("Alerts based on Run Rate Shot Efficiency and Time Stability.")
        rr_enabled = st.toggle("Enable Run Rate Alerts", value=True, key="rr_toggle")
        if rr_enabled:
            rr_tab1, rr_tab2 = st.tabs(["Low Run Rate Shot Efficiency", "Low Run Rate Time Stability"])
            def render_run_rate_logic(rr_type, prefix):
                with st.container(border=True):
                    st.markdown("##### 'No Alert' Zone")
                    no_alert_zone = st.number_input("No Alert Zone (Above %)", min_value=1, max_value=100, value=85, key=f"{prefix}_no_alert")
                    st.info(f"Production is considered **Healthy** when {rr_type.lower()} is **≥ {no_alert_zone}%**.")
                    st.divider()
                    st.markdown("##### Configuration: Number of Levels")
                    rr_num = st.number_input("How many alert levels do you want to configure?", min_value=1, max_value=5, value=2, key=f"{prefix}_num_levels")
                    st.markdown("##### Threshold Boundaries")
                    rr_limits = []
                    prev_val = no_alert_zone
                    rr_cols = st.columns(rr_num)
                    for i in range(rr_num):
                        with rr_cols[i]:
                            c_max = max(0, prev_val - 1)
                            def_val = max(0, min(c_max, prev_val - 15))
                            val = st.number_input(f"Level {i+1} Limit (%)", min_value=0, max_value=c_max, value=def_val, key=f"{prefix}_limit_{i}")
                            rr_limits.append(val)
                            prev_val = val
                    st.markdown("##### Alert Conditions Summary")
                    rr_disp_cols = st.columns(rr_num)
                    for i in range(rr_num):
                        with rr_disp_cols[i]:
                            upper = no_alert_zone if i == 0 else rr_limits[i-1]
                            lower = rr_limits[i]
                            op = "≤" if i == 0 else "<"
                            txt = f"**Level {i+1}**\n\nTriggers when rate drops between **{lower}% and {upper}%**.\n\n`{lower}% ≤ rate {op} {upper}%`"
                            display_level_box(i, txt)
                    st.divider()
                    rr_freq = st.selectbox("Alert Frequency", ["Daily", "Weekly", "Monthly"], key=f"{prefix}_freq")
                if st.button(f"Save {rr_type} Settings", type="primary", key=f"{prefix}_save"):
                    log_admin_action(f"Run Rate ({rr_type})", user_filters, selected_server, selected_users)

            with rr_tab1: render_run_rate_logic("Run Rate Shot Efficiency", "eff")
            with rr_tab2: render_run_rate_logic("Run Rate Time Stability", "stab")

    # --- 3. CAPACITY RISK ---
    with tab3:
        st.subheader("Capacity Risk Alerts")
        cr_enabled = st.toggle("Enable Capacity Risk Alerts", value=True, key="cr_toggle")
        if cr_enabled:
            cr_tab1, cr_tab2 = st.tabs(["Lost parts vs Optimal Capacity", "Lost parts vs Target Capacity"])
            def render_capacity_logic(cr_type, prefix, is_target=False):
                with st.container(border=True):
                    if is_target:
                        target_cap = st.number_input("Target Capacity Output (%)", value=90, min_value=1, max_value=100, key=f"{prefix}_target")
                        st.info(f"Calculations will be evaluated against **{target_cap}%** capacity output.")
                        st.divider()
                    cr_num = st.number_input("How many alert levels do you want to configure?", min_value=1, max_value=5, value=2, key=f"{prefix}_num_levels")
                    st.markdown("##### Threshold Boundaries")
                    cr_limits = []
                    prev_val = 0
                    cr_cols = st.columns(cr_num)
                    for i in range(cr_num):
                        with cr_cols[i]:
                            c_min = min(100, prev_val + 1)
                            def_val = min(100, max(c_min, prev_val + 10))
                            val = st.number_input(f"Level {i+1} Limit (%)", min_value=c_min, max_value=100, value=def_val, key=f"{prefix}_limit_{i}")
                            cr_limits.append(val)
                            prev_val = val
                    st.markdown("##### Alert Conditions Summary")
                    cr_disp_cols = st.columns(cr_num)
                    for i in range(cr_num):
                        with cr_disp_cols[i]:
                            lower = 0 if i == 0 else cr_limits[i-1]
                            upper = cr_limits[i]
                            op = "≤" if i == 0 else "<"
                            txt = f"**Level {i+1}**\n\nTriggers when capacity loss is between **{lower}% and {upper}%**.\n\n`{lower}% {op} loss ≤ {upper}%`"
                            display_level_box(i, txt)
                    st.divider()
                    cr_freq = st.selectbox("Alert Frequency", ["Daily", "Weekly", "Monthly"], key=f"{prefix}_freq")
                if st.button(f"Save {cr_type} Settings", type="primary", key=f"{prefix}_save"):
                    log_admin_action(f"Capacity Risk ({cr_type})", user_filters, selected_server, selected_users)

            with cr_tab1: render_capacity_logic("Optimal Capacity", "opt")
            with cr_tab2: render_capacity_logic("Target Capacity", "tgt", is_target=True)

    # --- 4. TOOLING END OF LIFE ---
    with tab4:
        st.subheader("Tooling End of Life Alerts")
        eol_enabled = st.toggle("Enable Tooling End of Life Alerts", value=True, key="eol_toggle")
        if eol_enabled:
            with st.container(border=True):
                eol_mode = st.radio("Choose how End of Life alerts should be evaluated:", ["Utilization Rate (%)", "Remaining Days", "Combination (Whichever comes first)"], horizontal=True)
                show_util = eol_mode in ["Utilization Rate (%)", "Combination (Whichever comes first)"]
                show_days = eol_mode in ["Remaining Days", "Combination (Whichever comes first)"]
                st.divider()
                eol_num = st.number_input("How many alert levels do you want to configure?", min_value=1, max_value=5, value=2, key="eol_num_levels")
                st.markdown("##### Threshold Boundaries")
                util_limits, days_limits = [], []
                if show_util:
                    base_start = st.number_input("Start Monitoring At (% of forecasted max shot)", min_value=0, max_value=99, value=80, key="eol_base")
                    prev_val = base_start
                    eol_cols = st.columns(eol_num)
                    for i in range(eol_num):
                        with eol_cols[i]:
                            c_min = min(200, prev_val + 1)
                            def_val = min(200, max(c_min, prev_val + 10))
                            val = st.number_input(f"Level {i+1} Upper Limit (%)", min_value=c_min, max_value=200, value=def_val, key=f"eol_limit_{i}")
                            util_limits.append(val)
                            prev_val = val
                    st.write("")
                if show_days:
                    prev_d = 365
                    days_cols = st.columns(eol_num)
                    for i in range(eol_num):
                        with days_cols[i]:
                            c_max = max(0, prev_d - 1)
                            val_d = st.number_input(f"Level {i+1} Remaining Days Limit", min_value=0, max_value=c_max, value=max(0, c_max - 15), key=f"eol_d_{i}")
                            days_limits.append(val_d)
                            prev_d = val_d
                st.markdown("##### Alert Conditions Summary")
                eol_disp_cols = st.columns(eol_num)
                for i in range(eol_num):
                    with eol_disp_cols[i]:
                        conds = []
                        if show_util:
                            lower = base_start if i == 0 else util_limits[i-1]
                            upper = util_limits[i]
                            op = "≤" if i == 0 else "<"
                            conds.append(f"Shots are between **{lower}% and {upper}%** of max shot.\n\n`{lower}% {op} shots ≤ {upper}%`")
                        if show_days:
                            upper_d = 365 if i == 0 else days_limits[i-1]
                            lower_d = days_limits[i]
                            conds.append(f"Remaining days fall between **{upper_d} and {lower_d} days**.")
                        txt = f"**Level {i+1}**\n\nTriggers when:\n\n" + "\n\n**OR**\n\n".join(conds)
                        display_level_box(i, txt)
                st.divider()
                eol_freq = st.selectbox("Alert Frequency", ["Daily", "Weekly", "Monthly"], key="eol_freq")
            if st.button("Save Tooling EOL Settings", type="primary"):
                log_admin_action("Tooling End of Life", user_filters, selected_server, selected_users, details=f"Mode: {eol_mode}")

    # --- 5. OPERATION STATUS ---
    with tab5:
        st.subheader("Operational Status Alerts")
        os_enabled = st.toggle("Enable Operation Status Alerts", value=True, key="os_toggle")
        if os_enabled:
            with st.container(border=True):
                st.markdown("##### Real-Time Event Alerts")
                st.checkbox("Tool Starts Producing", value=True)
                st.write("")
                st.checkbox("Tool Stops", value=False)
                st.divider()
                st.markdown("##### Connectivity & Status-Based Alerts")
                c1, c2 = st.columns(2)
                with c1:
                    st.multiselect("Trigger when tools remain in:", ["Sensor offline", "Inactive", "Sensor detached"], default=["Sensor offline"])
                with c2:
                    st.selectbox("Alert Frequency", ["Daily", "Weekly", "Monthly", "Real time"], index=3, key="os_freq")
            if st.button("Save Operation Status Settings", type="primary"):
                log_admin_action("Operation Status", user_filters, selected_server, selected_users)

# ==========================================
#        GLOBAL CONFIGURATIONS DASHBOARD
# ==========================================
elif page == "Global Dashboard":
    st.markdown('<div class="main-header">Global Configurations Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">A comprehensive view of all active alert configurations across all servers and user groups.</div>', unsafe_allow_html=True)
    st.write("")

    if st.session_state.admin_log.empty:
        st.info("No configurations have been applied yet in this session.")
    else:
        st.markdown("##### 🔍 Filter Configurations")
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            server_filter = st.multiselect("Filter by Server", options=st.session_state.admin_log['Server'].unique(), default=[])
        with f_col2:
            alert_filter = st.multiselect("Filter by Alert Type", options=st.session_state.admin_log['Alert Type'].unique(), default=[])
        st.divider()
        display_df = st.session_state.admin_log
        if server_filter: display_df = display_df[display_df['Server'].isin(server_filter)]
        if alert_filter: display_df = display_df[display_df['Alert Type'].isin(alert_filter)]
        st.dataframe(display_df, use_container_width=True, hide_index=True)

# ==========================================
#        CLIENT ALERTS PORTAL
# ==========================================
elif page == "Client Alerts Portal":
    
    def set_view(view_mode, alert_id=None):
        st.session_state.client_portal_view = view_mode
        st.session_state.selected_alert_id = alert_id

    # ---------------------------------------------------------
    # MAIN LISTING PAGE & COMMAND CENTER
    # ---------------------------------------------------------
    if st.session_state.client_portal_view == "list":
        st.markdown('<div class="main-header">Alerts Command Center</div>', unsafe_allow_html=True)
        st.markdown('<div class="sub-header">Triage critical issues, identify supply chain bottlenecks, and track proactive watchlists.</div>', unsafe_allow_html=True)
        
        df = st.session_state.client_alerts_db.copy()
        
        # Calculate dynamic risk score for workflow
        df['Risk Score'] = df.apply(calculate_risk_index, axis=1)
        df = df.sort_values(by='Risk Score', ascending=False)
        
        if client_filters.get("OEM"): df = df[df['OEM Division'].isin(client_filters["OEM"])]
        if client_filters.get("Supplier"): df = df[df['Supplier'].isin(client_filters["Supplier"])]
        if client_filters.get("Plant"): df = df[df['Plant'].isin(client_filters["Plant"])]
        if client_filters.get("Tooling Type"): df = df[df['Tooling Type'].isin(client_filters["Tooling Type"])]
        if client_filters.get("Part"): df = df[df['Part'].isin(client_filters["Part"])]
        if client_filters.get("Tooling"): df = df[df['Tool'].isin(client_filters["Tooling"])]
        
        search_query = st.text_input("🔍 Search (Tool, Part, Name)")
        if search_query:
            df = df[df.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)]

        st.write("")
        
        def format_trigger_value(row):
            val = str(row['Metric_1'])
            if pd.notna(row['Metric_2']) and str(row['Metric_2']).strip():
                val += f" | {row['Metric_2']}"
            return val
            
        def render_alert_hierarchy(tab_df, tab_name):
            if tab_df.empty:
                st.info("No alerts found for this category with the current filters.")
                return
            
            available_freqs = sorted(tab_df['Frequency'].unique().tolist())
            selected_freqs = st.multiselect("Filter by Alert Frequency", options=available_freqs, default=available_freqs, key=f"freq_filter_{tab_name}")
            filtered_df = tab_df[tab_df['Frequency'].isin(selected_freqs)].copy()
            if filtered_df.empty:
                st.info("No alerts match the selected frequency.")
                return
                
            base_cols = {"Tool": "Tooling ID", "Part": "Part ID (Part Name)", "OEM Division": "OEM Business Division", "Supplier": "Supplier", "Plant": "Plant", "Tooling Type": "Tooling Type", "Severity": "Severity"}
            for sev in sorted(filtered_df['Severity'].unique(), reverse=True):
                st.markdown(f"#### 📌 {sev}")
                sev_df = filtered_df[filtered_df['Severity'] == sev]
                
                for a_type in sorted(sev_df['Alert Type'].unique()):
                    type_df = sev_df[sev_df['Alert Type'] == a_type].copy()
                    display_cols = base_cols.copy()
                    
                    if a_type == "Cycle Time": display_cols["Metric_1"] = "% of deviation"
                    elif a_type == "Low Run Rate - Shot Efficiency": display_cols["Metric_1"] = "Run Rate Shot Efficiency"
                    elif a_type == "Low Run Rate - Time Stability": display_cols["Metric_1"] = "Run Rate Time Stability"
                    elif "Capacity Risk" in a_type: display_cols["Metric_1"] = "% of loss"
                    elif a_type == "Tooling EOL (Utilization)": display_cols["Metric_1"] = "Utilization Rate"
                    elif a_type == "Tooling EOL (Remaining Days)": display_cols["Metric_1"] = "Remaining Life (Days)"
                    elif a_type == "Tooling EOL (Combination)":
                        display_cols["Metric_1"] = "Utilization Rate (%)"
                        display_cols["Metric_2"] = "Remaining Life (days)"
                    elif a_type == "Operation Status (Tool Producing)": display_cols["Metric_1"] = "Date & Time"
                    elif a_type == "Operation Status (Tool Stops)": display_cols["Metric_1"] = "Tool Stops"
                    else:
                        status_val = a_type.replace("Operation Status (", "").replace(")", "")
                        type_df["Tooling Status"] = status_val
                        display_cols["Tooling Status"] = "Tooling Status"
                        display_cols["Metric_1"] = "Date & Time"
                    
                    out_df = type_df[list(display_cols.keys())].rename(columns=display_cols)
                    if len(sev_df['Alert Type'].unique()) > 1: st.markdown(f"##### {a_type}")
                    st.dataframe(out_df, use_container_width=True, hide_index=True)
                st.write("")

        # Helper functions for the custom graph-based dashboards
        sev_colors = {'Level 1': '#FACC15', 'Level 2': '#F59E0B', 'Level 3': '#EF4444', 'Event': '#8B5CF6', 'Status': '#64748B'}
        status_colors = {'Sensor Offline': '#F87171', 'Sensor Detached': '#FACC15', 'Inactive': '#94A3B8'}

        def render_matplot_bar(df_subset, title):
            fig, ax = plt.subplots(figsize=(5, 3.5))
            categories = ['Level 1', 'Level 2', 'Level 3']
            counts = df_subset['Severity'].value_counts() if not df_subset.empty else pd.Series(dtype=int)
            plot_data = [counts.get(cat, 0) for cat in categories]
            colors = [sev_colors.get(cat, '#3B82F6') for cat in categories]
            
            bars = ax.bar(categories, plot_data, color=colors, width=0.5)
            for bar in bars:
                yval = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2, yval + 0.5, int(yval), ha='center', va='bottom', fontsize=10, fontweight='bold')
            
            ax.set_title(title, fontsize=11, fontweight='bold', color='#1E40AF', pad=10)
            ax.set_ylabel("Tool Count", fontsize=9)
            ax.set_ylim(0, max(plot_data) * 1.2 if max(plot_data) > 0 else 10)
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color('#CBD5E1')
            ax.spines['bottom'].set_color('#CBD5E1')
            plt.tight_layout()
            st.pyplot(fig)

        def render_matplot_donut(counts_series, title, color_map):
            fig, ax = plt.subplots(figsize=(4.5, 4.5))
            if counts_series.empty or counts_series.sum() == 0:
                ax.text(0.5, 0.5, 'No Active Alerts', ha='center', va='center', color='#94A3B8')
                ax.axis('off')
            else:
                colors = [color_map.get(x, '#3B82F6') for x in counts_series.index]
                ax.pie(counts_series.values, labels=counts_series.index, autopct='%1.0f%%', startangle=90, colors=colors,
                       wedgeprops=dict(width=0.4, edgecolor='white', linewidth=2), textprops={'fontsize': 10})
            ax.set_title(title, fontsize=11, fontweight='bold', color='#1E40AF', pad=10)
            plt.tight_layout()
            st.pyplot(fig)

        # 6 Main Tabs for the Client Portal
        cat_tabs = st.tabs([
            "Overview Dashboard",
            "Cycle Time", 
            "Run Rate", 
            "Capacity Risk", 
            "Tooling End of Life", 
            "Operation Status"
        ])

        with cat_tabs[0]: # Dashboard Overview
            st.markdown("### 📊 Executive Command Center")
            st.write("High-level summary of active alerts matching your current filters.")

            # --- 1. Core KPIs ---
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.markdown(f"<div class='metric-card'><div class='metric-title'>Total Active Alerts</div><div class='metric-value'>{len(df)}</div></div>", unsafe_allow_html=True)
            kpi2.markdown(f"<div class='metric-card'><div class='metric-title'>Impacted Tools</div><div class='metric-value'>{df['Tool'].nunique()}</div></div>", unsafe_allow_html=True)
            kpi3.markdown(f"<div class='metric-card'><div class='metric-title'>Impacted Plants</div><div class='metric-value'>{df['Plant'].nunique()}</div></div>", unsafe_allow_html=True)
            kpi4.markdown(f"<div class='metric-card'><div class='metric-title'>Impacted Suppliers</div><div class='metric-value'>{df['Supplier'].nunique()}</div></div>", unsafe_allow_html=True)

            st.divider()

            # --- 2. ACT NOW: Triage Banner ---
            st.markdown("### 🚨 Act Now: Critical Priorities")
            st.write("Top issues sorted by proprietary Risk Index (Severity + Financial Impact + Unresolved Time).")
            
            top_alerts = df.head(3)
            if top_alerts.empty:
                st.success("No active alerts currently require your attention.")
            else:
                cols = st.columns(3)
                for idx, (_, alert) in enumerate(top_alerts.iterrows()):
                    with cols[idx]:
                        card_class = "action-card"
                        badge_class = "risk-score-badge"
                        if alert['Risk Score'] < 75:
                            card_class += " action-card-warning"
                            badge_class += " risk-score-warning"
                            
                        st.markdown(f"""
                        <div class="{card_class}">
                            <div class="{badge_class}">🔥 Risk: {alert['Risk Score']}/100</div>
                            <div style="color: #64748B; font-size: 0.85rem; font-weight: bold; text-transform: uppercase;">{alert['Alert Type']}</div>
                            <div class="card-tool">{alert['Tool']} ({alert['Plant']})</div>
                            <div class="card-context"><b>Trigger Metric:</b> {alert['Metric_1']}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        b1, b2 = st.columns(2)
                        if b1.button("Assign", key=f"assign_{alert['Alert ID']}", use_container_width=True):
                            st.toast(f"Assigned {alert['Alert ID']} to Site Manager.")
                        if b2.button("Acknowledge", key=f"ack_{alert['Alert ID']}", use_container_width=True):
                            st.toast(f"Acknowledged {alert['Alert ID']}.")
            
            st.divider()

            # --- 3. Heatmap & Watchlist ---
            col_heatmap, col_watchlist = st.columns([3, 2])
            with col_heatmap:
                st.markdown("### 📍 Impact Heatmap (By Supplier)")
                st.write("Identify systemic bottlenecks affecting specific suppliers.")
                if not df.empty and MATPLOTLIB_AVAILABLE:
                    sup_risk = df.groupby('Supplier')['Risk Score'].sum().sort_values(ascending=True)
                    fig_heat, ax_heat = plt.subplots(figsize=(6, 4))
                    colors = ['#EF4444' if score > 500 else '#F59E0B' if score > 200 else '#3B82F6' for score in sup_risk]
                    bars = ax_heat.barh(sup_risk.index, sup_risk.values, color=colors, height=0.6)
                    for bar in bars:
                        width = bar.get_width()
                        ax_heat.text(width + 5, bar.get_y() + bar.get_height()/2, f"Total Risk: {int(width)}", ha='left', va='center', fontsize=9, fontweight='bold', color='#475569')
                    ax_heat.spines['top'].set_visible(False)
                    ax_heat.spines['right'].set_visible(False)
                    ax_heat.spines['left'].set_visible(False)
                    ax_heat.spines['bottom'].set_visible(False)
                    ax_heat.xaxis.set_visible(False)
                    plt.tight_layout()
                    st.pyplot(fig_heat)
                else:
                    st.info("Insufficient data for heatmap.")

            with col_watchlist:
                st.markdown("### 🔭 Proactive Watchlist")
                st.write("Degrading trends and tools approaching end-of-life.")
                watchlist_df = df[(df['Severity'] == 'Level 2') | (df['Alert Type'].str.contains('EOL'))].sort_values(by='Date/Time', ascending=False).head(5)
                if watchlist_df.empty:
                    st.success("No proactive warnings detected.")
                else:
                    for _, w_alert in watchlist_df.iterrows():
                        icon = "⏳" if "EOL" in w_alert['Alert Type'] else "📉"
                        st.markdown(f"""
                        <div style="background-color: #F8FAFC; border-left: 3px solid #F59E0B; padding: 10px 15px; margin-bottom: 8px; border-radius: 4px;">
                            <div style="font-weight: bold; color: #1E293B;">{icon} {w_alert['Tool']} - {w_alert['Alert Type']}</div>
                            <div style="font-size: 0.85rem; color: #64748B;">{w_alert['Supplier']} | Metric: {w_alert['Metric_1']}</div>
                        </div>
                        """, unsafe_allow_html=True)
            
            st.divider()

            # --- 4. Alert Distribution Dashboards (The 6 Graphs) ---
            st.markdown("### 📈 Alert Distribution Breakdowns")
            st.write("Detailed threshold analysis across the 6 major alert logic categories.")
            
            c1, c2 = st.columns(2)
            with c1:
                ct_df = df[df['Alert Type'] == 'Cycle Time']
                if MATPLOTLIB_AVAILABLE: render_matplot_bar(ct_df, "Cycle Time Deviations")
                with st.expander("Definitions & Thresholds"):
                    st.markdown("- **Level 1:** > 0% and ≤ 5% deviation\n- **Level 2:** > 5% and ≤ 15% deviation\n- **Level 3:** > 15% deviation")
                
                rr_stab_df = df[df['Alert Type'] == 'Low Run Rate - Time Stability']
                if MATPLOTLIB_AVAILABLE: render_matplot_bar(rr_stab_df, "Low Run Rate Time Stability")
                with st.expander("Definitions & Thresholds"):
                    st.markdown("- **Level 1:** 75% ≤ rate < 85%\n- **Level 2:** 60% ≤ rate < 75%\n- **Level 3:** < 60%")

                cr_tgt_df = df[df['Alert Type'] == 'Capacity Risk (Target)']
                if MATPLOTLIB_AVAILABLE: render_matplot_bar(cr_tgt_df, "Loss vs. Target Capacity")
                with st.expander("Definitions & Thresholds"):
                    st.markdown("- **Level 1:** > 0% and ≤ 5% loss\n- **Level 2:** > 5% and ≤ 10% loss\n- **Level 3:** > 10% loss")

                os_target_cats = ['Sensor Offline', 'Sensor Detached', 'Inactive']
                os_df = df[df['Alert Type'].apply(lambda x: any(cat in x for cat in os_target_cats))]
                os_counts = os_df['Alert Type'].apply(lambda x: x.replace("Operation Status (", "").replace(")", "")).value_counts()
                os_aligned = pd.Series({cat: os_counts.get(cat, 0) for cat in os_target_cats})
                os_aligned = os_aligned[os_aligned > 0] 
                if MATPLOTLIB_AVAILABLE: render_matplot_donut(os_aligned, "Operation Status", status_colors)
                with st.expander("Definitions & Categories"):
                    st.markdown("- **Sensor Offline:** Sensor heartbeat lost.\n- **Sensor Detached:** Physical detachment detected.\n- **Inactive:** Tool idle beyond threshold.")

            with c2:
                rr_eff_df = df[df['Alert Type'] == 'Low Run Rate - Shot Efficiency']
                if MATPLOTLIB_AVAILABLE: render_matplot_bar(rr_eff_df, "Low Run Rate Shot Efficiency")
                with st.expander("Definitions & Thresholds"):
                    st.markdown("- **Level 1:** 75% ≤ rate < 85%\n- **Level 2:** 60% ≤ rate < 75%\n- **Level 3:** < 60%")

                cr_opt_df = df[df['Alert Type'] == 'Capacity Risk (Optimal)']
                if MATPLOTLIB_AVAILABLE: render_matplot_bar(cr_opt_df, "Loss vs. Optimal Capacity")
                with st.expander("Definitions & Thresholds"):
                    st.markdown("- **Level 1:** > 0% and ≤ 5% loss\n- **Level 2:** > 5% and ≤ 10% loss\n- **Level 3:** > 10% loss")

                eol_df = df[df['Alert Type'].str.contains('EOL')]
                categories = ['Level 1', 'Level 2', 'Level 3']
                eol_counts = eol_df['Severity'].value_counts()
                eol_counts_aligned = pd.Series({cat: eol_counts.get(cat, 0) for cat in categories})
                eol_counts_aligned = eol_counts_aligned[eol_counts_aligned > 0]
                if MATPLOTLIB_AVAILABLE: render_matplot_donut(eol_counts_aligned, "Tooling End of Life", sev_colors)
                with st.expander("Definitions & Thresholds"):
                    st.markdown("- **Level 1:** Utilization 70%-80% OR Remaining ≤ 45 days\n- **Level 2:** Utilization 80%-90% OR Remaining ≤ 30 days\n- **Level 3:** Utilization > 90% OR Remaining ≤ 10 days")

            st.divider()

            # --- 5. Smart Triage Queue ---
            st.markdown("### 📋 Smart Triage Queue")
            st.write("Complete ledger of active alerts, interactively sorted by the Priority Risk Index.")
            
            if not df.empty:
                triage_df = df.copy()
                triage_df['Trigger Info'] = triage_df.apply(format_trigger_value, axis=1)
                workflow_cols = ['Risk Score', 'Alert ID', 'Alert Name', 'Tool', 'Supplier', 'Severity', 'Status', 'Owner']
                triage_display = triage_df[workflow_cols].copy()
                
                st.data_editor(
                    triage_display,
                    column_config={
                        "Risk Score": st.column_config.ProgressColumn("Priority (1-100)", help="Calculated Risk Index", format="%d", min_value=0, max_value=100),
                        "Status": st.column_config.SelectboxColumn("Workflow Status", help="Update resolution status.", options=["Open", "Investigating", "Parts Ordered", "Resolved"], required=True),
                        "Owner": st.column_config.TextColumn("Assigned To")
                    },
                    hide_index=True,
                    use_container_width=True
                )
            else:
                st.info("No active alerts to triage.")

        with cat_tabs[1]: # Cycle Time
            render_alert_hierarchy(df[df['Alert Type'] == 'Cycle Time'], "Cycle Time")
            
        with cat_tabs[2]: # Run Rate
            st.markdown("### Run Rate Shot Efficiency")
            render_alert_hierarchy(df[df['Alert Type'] == 'Low Run Rate - Shot Efficiency'], "Run Rate Shot Efficiency")
            st.divider()
            st.markdown("### Run Rate Time Stability")
            render_alert_hierarchy(df[df['Alert Type'] == 'Low Run Rate - Time Stability'], "Run Rate Time Stability")
            
        with cat_tabs[3]: # Capacity Risk
            st.markdown("### Loss Parts vs Optimal Capacity")
            render_alert_hierarchy(df[df['Alert Type'] == 'Capacity Risk (Optimal)'], "Optimal Capacity")
            st.divider()
            st.markdown("### Loss Parts vs Target Capacity")
            render_alert_hierarchy(df[df['Alert Type'] == 'Capacity Risk (Target)'], "Target Capacity")
            
        with cat_tabs[4]: # Tooling EOL
            render_alert_hierarchy(df[df['Alert Type'].str.contains('EOL')], "EOL")
            
        with cat_tabs[5]: # Operation Status
            render_alert_hierarchy(df[df['Alert Type'].str.contains('Operation Status')], "Operation Status")
        
        st.divider()
        st.markdown("#### 📄 Drill-down into Alert Details")
        st.write("Select an Alert to view its dedicated detail page with exact triggering calculations.")
        
        select_col, btn_col, empty_col = st.columns([3, 1, 6])
        with select_col:
            alert_mapping = dict(zip(df['Alert ID'], df['Alert Name']))
            selected_id = st.selectbox("Select Alert", options=list(alert_mapping.keys()), format_func=lambda x: alert_mapping[x], label_visibility="collapsed")
        with btn_col:
            if st.button("View Details", type="primary", use_container_width=True):
                set_view("detail", selected_id)
                st.rerun()

    # ---------------------------------------------------------
    # INDIVIDUAL ALERT DETAIL PAGE
    # ---------------------------------------------------------
    elif st.session_state.client_portal_view == "detail":
        if st.button("🔙 Back to Alerts Dashboard"):
            set_view("list")
            st.rerun()
            
        alert_data = st.session_state.client_alerts_db[st.session_state.client_alerts_db['Alert ID'] == st.session_state.selected_alert_id].iloc[0]
        
        st.write("")
        st.markdown(f"<h2>{alert_data['Alert Name']}</h2>", unsafe_allow_html=True)
        
        sev = alert_data['Severity']
        color = "#EF4444" if "Level 3" in sev else "#F59E0B" if "Level 2" in sev else "#FACC15" if "Level 1" in sev else "#3B82F6"
        st.markdown(f"<div style='background-color: {color}; color: white; padding: 4px 12px; border-radius: 20px; display: inline-block; font-weight: bold; font-size: 0.9rem; margin-bottom: 20px;'>Severity: {sev}</div>", unsafe_allow_html=True)
        
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.markdown(f"<div class='metric-card'><div class='metric-title'>Date & Time</div><div style='font-size: 1.2rem; font-weight: bold;'>{alert_data['Date/Time']}</div></div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div class='metric-card'><div class='metric-title'>Frequency</div><div style='font-size: 1.2rem; font-weight: bold;'>{alert_data['Frequency']}</div></div>", unsafe_allow_html=True)
        with c3: st.markdown(f"<div class='metric-card'><div class='metric-title'>Tooling Type</div><div style='font-size: 1.2rem; font-weight: bold;'>{alert_data['Tooling Type']}</div></div>", unsafe_allow_html=True)
        with c4: st.markdown(f"<div class='metric-card'><div class='metric-title'>OEM Division</div><div style='font-size: 1.2rem; font-weight: bold;'>{alert_data['OEM Division']}</div></div>", unsafe_allow_html=True)

        st.markdown("#### 🏭 Entity Details")
        e1, e2, e3, e4 = st.columns(4)
        e1.metric("Target Tool", alert_data['Tool'])
        e2.metric("Associated Part", alert_data['Part'])
        e3.metric("Plant Location", alert_data['Plant'])
        e4.metric("Supplier", alert_data['Supplier'])
        
        st.divider()

        st.markdown(f"#### 📊 Trigger Analytics: {alert_data['Alert Type']}")
        
        a_type = alert_data['Alert Type']
        m1 = alert_data['Metric_1']
        m2 = alert_data['Metric_2']
        
        if a_type == "Cycle Time":
            st.info("The tool is operating significantly outside the approved cycle time parameters.")
            st.markdown(f"<div class='metric-card'><div class='metric-title'>% Deviation vs Approved Cycle Time</div><div class='metric-value' style='color: #EF4444;'>{m1}</div></div>", unsafe_allow_html=True)
        elif a_type == "Low Run Rate - Shot Efficiency":
            st.info("The tool is failing to achieve the expected output efficiency during scheduled operation hours.")
            st.markdown(f"<div class='metric-card'><div class='metric-title'>Current Run Rate Shot Efficiency</div><div class='metric-value' style='color: #F59E0B;'>{m1}</div></div>", unsafe_allow_html=True)
        elif a_type == "Low Run Rate - Time Stability":
            st.info("The tool's cycle times are highly unstable, affecting production predictability.")
            st.markdown(f"<div class='metric-card'><div class='metric-title'>Current Run Rate Time Stability</div><div class='metric-value' style='color: #F59E0B;'>{m1}</div></div>", unsafe_allow_html=True)
        elif "Capacity Risk (Optimal)" in a_type:
            st.info("Calculating lost parts specifically against the optimal maximum theoretical capacity.")
            st.markdown(f"<div class='metric-card'><div class='metric-title'>% of Lost Parts Against Optimal Capacity</div><div class='metric-value' style='color: #EF4444;'>{m1}</div></div>", unsafe_allow_html=True)
        elif "Capacity Risk (Target)" in a_type:
            st.info("Calculating lost parts against your predefined targeted capacity baseline.")
            st.markdown(f"<div class='metric-card'><div class='metric-title'>% of Lost Parts Against Target Capacity</div><div class='metric-value' style='color: #EF4444;'>{m1}</div></div>", unsafe_allow_html=True)
        elif "EOL (Utilization)" in a_type:
            st.warning("Tool is approaching its maximum forecasted physical shot limit.")
            st.markdown(f"<div class='metric-card'><div class='metric-title'>Current Tool Life Used</div><div class='metric-value' style='color: #EF4444;'>{m1}</div></div>", unsafe_allow_html=True)
        elif "EOL (Remaining Days)" in a_type:
            st.warning("Tool life is severely depleted based on current running trajectory.")
            st.markdown(f"<div class='metric-card'><div class='metric-title'>Estimated Remaining Tool Life</div><div class='metric-value' style='color: #EF4444;'>{m1}</div></div>", unsafe_allow_html=True)
        elif "EOL (Combination)" in a_type:
            st.warning("Tool requires maintenance or replacement. A combination threshold has been breached.")
            cc1, cc2 = st.columns(2)
            with cc1: st.markdown(f"<div class='metric-card'><div class='metric-title'>Current Tool Life Used</div><div class='metric-value' style='color: #EF4444;'>{m1}</div></div>", unsafe_allow_html=True)
            with cc2: st.markdown(f"<div class='metric-card'><div class='metric-title'>Estimated Remaining Tool Life</div><div class='metric-value' style='color: #EF4444;'>{m2}</div></div>", unsafe_allow_html=True)
        elif "Tool Producing" in a_type:
            st.success("A new continuous production run interval was verified by the system.")
            st.markdown(f"<div class='metric-card'><div class='metric-title'>Exact Start Timestamp</div><div class='metric-value' style='color: #10B981;'>{m1}</div></div>", unsafe_allow_html=True)
        elif "Tool Stops" in a_type:
            st.error("The tool was abruptly removed from the press based on TMD diagnostics.")
            st.markdown(f"<div class='metric-card'><div class='metric-title'>Exact Stop Timestamp</div><div class='metric-value' style='color: #EF4444;'>{m1}</div></div>", unsafe_allow_html=True)
        else: 
            st.error("A critical connectivity or sensor status change was detected.")
            st.markdown(f"<div class='metric-card'><div class='metric-title'>Status Change Timestamp</div><div class='metric-value' style='color: #EF4444;'>{m1}</div></div>", unsafe_allow_html=True)