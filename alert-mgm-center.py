import streamlit as st
import pandas as pd
import datetime
import os
import tempfile

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

# Initialize mock client alerts for the new Client Portal
if 'client_alerts_db' not in st.session_state:
    # Building a scalable mock dataset covering all requested logic scenarios
    mock_data = [
        {"Alert ID": "ALT-1001", "Alert Name": "Cycle Time Deviation - Tool A", "Date/Time": "2026-04-27 10:15:00", "Frequency": "Hourly", "Tool": "Tool_A", "Part": "Part 101", "Supplier": "Supplier X", "Plant": "Plant 1", "Tooling Type": "Injection", "OEM Division": "Div A", "Severity": "Level 2", "Alert Type": "Cycle Time", "Metric_1": "12.5%", "Metric_2": ""},
        {"Alert ID": "ALT-1002", "Alert Name": "Low Eff - Supplier Y", "Date/Time": "2026-04-26 08:00:00", "Frequency": "Daily", "Tool": "Tool_B", "Part": "Part 102", "Supplier": "Supplier Y", "Plant": "Plant 2", "Tooling Type": "Stamping", "OEM Division": "Div B", "Severity": "Level 1", "Alert Type": "Low Run Rate - Shot Efficiency", "Metric_1": "72%", "Metric_2": ""},
        {"Alert ID": "ALT-1003", "Alert Name": "Low Stab - Plant 1", "Date/Time": "2026-04-25 14:30:00", "Frequency": "Weekly", "Tool": "Tool_C", "Part": "Part 103", "Supplier": "Supplier X", "Plant": "Plant 1", "Tooling Type": "Die Casting", "OEM Division": "Div A", "Severity": "Level 2", "Alert Type": "Low Run Rate - Time Stability", "Metric_1": "65%", "Metric_2": ""},
        {"Alert ID": "ALT-1004", "Alert Name": "Cap Risk Optimal - Tool D", "Date/Time": "2026-04-27 09:00:00", "Frequency": "Daily", "Tool": "Tool_D", "Part": "Product Alpha", "Supplier": "Supplier Z", "Plant": "Plant 3", "Tooling Type": "Injection", "OEM Division": "Div C", "Severity": "Level 1", "Alert Type": "Capacity Risk (Optimal)", "Metric_1": "8.4%", "Metric_2": ""},
        {"Alert ID": "ALT-1005", "Alert Name": "Cap Risk Target - Tool A", "Date/Time": "2026-04-24 11:20:00", "Frequency": "Monthly", "Tool": "Tool_A", "Part": "Part 101", "Supplier": "Supplier X", "Plant": "Plant 1", "Tooling Type": "Injection", "OEM Division": "Div A", "Severity": "Level 2", "Alert Type": "Capacity Risk (Target)", "Metric_1": "11.2%", "Metric_2": ""},
        {"Alert ID": "ALT-1006", "Alert Name": "EOL Util - Tool B", "Date/Time": "2026-04-27 16:45:00", "Frequency": "Daily", "Tool": "Tool_B", "Part": "Part 102", "Supplier": "Supplier Y", "Plant": "Plant 2", "Tooling Type": "Stamping", "OEM Division": "Div B", "Severity": "Level 1", "Alert Type": "Tooling EOL (Utilization)", "Metric_1": "92%", "Metric_2": ""},
        {"Alert ID": "ALT-1007", "Alert Name": "EOL Days - Tool C", "Date/Time": "2026-04-26 09:15:00", "Frequency": "Weekly", "Tool": "Tool_C", "Part": "Part 103", "Supplier": "Supplier X", "Plant": "Plant 1", "Tooling Type": "Die Casting", "OEM Division": "Div A", "Severity": "Level 2", "Alert Type": "Tooling EOL (Remaining Days)", "Metric_1": "14 days", "Metric_2": ""},
        {"Alert ID": "ALT-1008", "Alert Name": "EOL Combo - Tool D", "Date/Time": "2026-04-27 10:00:00", "Frequency": "Daily", "Tool": "Tool_D", "Part": "Product Alpha", "Supplier": "Supplier Z", "Plant": "Plant 3", "Tooling Type": "Injection", "OEM Division": "Div C", "Severity": "Level 2", "Alert Type": "Tooling EOL (Combination)", "Metric_1": "96%", "Metric_2": "8 days"},
        {"Alert ID": "ALT-1009", "Alert Name": "Tool Producing Started", "Date/Time": "2026-04-27 07:30:00", "Frequency": "Real time", "Tool": "Tool_A", "Part": "Part 101", "Supplier": "Supplier X", "Plant": "Plant 1", "Tooling Type": "Injection", "OEM Division": "Div A", "Severity": "Event", "Alert Type": "Operation Status (Tool Producing)", "Metric_1": "2026-04-27 07:30:00", "Metric_2": ""},
        {"Alert ID": "ALT-1010", "Alert Name": "Tool Stopped Unexpectedly", "Date/Time": "2026-04-27 13:45:00", "Frequency": "Real time", "Tool": "Tool_B", "Part": "Part 102", "Supplier": "Supplier Y", "Plant": "Plant 2", "Tooling Type": "Stamping", "OEM Division": "Div B", "Severity": "Event", "Alert Type": "Operation Status (Tool Stops)", "Metric_1": "2026-04-27 13:45:00", "Metric_2": ""},
        {"Alert ID": "ALT-1011", "Alert Name": "Sensor Offline Alert", "Date/Time": "2026-04-26 22:10:00", "Frequency": "Real time", "Tool": "Tool_C", "Part": "Part 103", "Supplier": "Supplier X", "Plant": "Plant 1", "Tooling Type": "Die Casting", "OEM Division": "Div A", "Severity": "Status", "Alert Type": "Operation Status (Sensor Offline)", "Metric_1": "2026-04-26 22:10:00", "Metric_2": ""},
    ]
    st.session_state.client_alerts_db = pd.DataFrame(mock_data)

if 'client_portal_view' not in st.session_state:
    st.session_state.client_portal_view = "list"
if 'selected_alert_id' not in st.session_state:
    st.session_state.selected_alert_id = None

# --- CUSTOM STYLING ---
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E3A8A;
        margin-bottom: 0px;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #6B7280;
        margin-bottom: 2rem;
    }
    .level-box {
        padding: 15px;
        border-radius: 8px;
        margin-top: 10px;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 20px;
        margin-bottom: 15px;
    }
    .metric-title {
        color: #64748B;
        font-size: 0.95rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 5px;
    }
    .metric-value {
        color: #0F172A;
        font-size: 1.8rem;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --- HELPER TO DISPLAY COLORED LEVEL BOXES ---
def display_level_box(level_idx, markdown_text):
    if level_idx == 0:
        st.info(markdown_text)
    elif level_idx == 1:
        st.warning(markdown_text)
    else:
        st.error(markdown_text)

# --- EXECUTIVE POWER-BI STYLE PDF GENERATOR ---
def generate_fpdf_report(df):
    
    def clean(text):
        """Helper to sanitize special unicode characters (like ≤) for FPDF latin-1 encoding"""
        text = str(text).replace('≤', '<=').replace('≥', '>=')
        return text.encode('latin-1', 'replace').decode('latin-1')
        
    class PDF(FPDF):
        def header(self):
            # Report Header - Executive Style
            self.set_fill_color(30, 58, 138) # Dark Blue
            self.rect(0, 0, 297, 20, 'F')
            self.set_y(6)
            self.set_font('Arial', 'B', 16)
            self.set_text_color(255, 255, 255)
            self.cell(10)
            self.cell(150, 8, clean('eMoldino Alert Management | Executive Dashboard'), 0, 0, 'L')
            self.set_font('Arial', '', 10)
            self.cell(120, 8, clean(f'Generated: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}'), 0, 1, 'R')
            self.ln(10)

        def kpi_card(self, x, y, w, h, title, value, subtitle):
            """Draws a clean KPI summary card"""
            self.set_xy(x, y)
            self.set_fill_color(248, 250, 252) # Slate 50
            self.set_draw_color(203, 213, 225) # Slate 300
            self.rect(x, y, w, h, 'DF')
            
            self.set_xy(x, y + 4)
            self.set_font('Arial', 'B', 10)
            self.set_text_color(100, 116, 139) # Slate 500
            self.cell(w, 5, clean(title), 0, 1, 'C')
            
            self.set_xy(x, y + 12)
            self.set_font('Arial', 'B', 24)
            self.set_text_color(30, 58, 138) # eMoldino Blue
            self.cell(w, 10, clean(value), 0, 1, 'C')
            
            self.set_xy(x, y + 24)
            self.set_font('Arial', '', 9)
            self.set_text_color(148, 163, 184) # Slate 400
            self.cell(w, 5, clean(subtitle), 0, 1, 'C')

    # Initialize PDF in Landscape mode
    pdf = PDF('L', 'mm', 'A4')
    pdf.add_page()
    
    # Generate Matplotlib Charts
    temp_files = []
    
    # Chart 1: Donut Chart (Alerts by Category)
    fig1, ax1 = plt.subplots(figsize=(4.5, 4.5))
    labels = ['Cycle Time', 'Run Rate', 'Cap Risk', 'EOL', 'Op Status']
    sizes = [19, 30, 12, 16, 28]
    colors = ['#1e3a8a', '#3b82f6', '#60a5fa', '#93c5fd', '#bfdbfe']
    ax1.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors,
            wedgeprops=dict(width=0.4, edgecolor='white', linewidth=2), textprops={'fontsize': 9})
    plt.title('Alert Distribution by Category', fontweight='bold', color='#1e40af', pad=10)
    plt.tight_layout()
    tmp1 = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    plt.savefig(tmp1.name, format='png', transparent=True, dpi=150)
    plt.close(fig1)
    temp_files.append(tmp1.name)

    # Chart 2: Stacked Bar Chart (Alert Severity Breakdown)
    fig2, ax2 = plt.subplots(figsize=(5, 4.5))
    categories = ['Cycle', 'Run Rate', 'Cap Risk', 'EOL']
    level1 = [14, 22, 9, 12]
    level2 = [5, 8, 3, 4]
    ax2.bar(categories, level1, label='Level 1', color='#60a5fa', width=0.6)
    ax2.bar(categories, level2, bottom=level1, label='Level 2', color='#1e3a8a', width=0.6)
    ax2.legend(loc='upper right', frameon=False)
    ax2.spines['top'].set_visible(False)
    ax2.spines['right'].set_visible(False)
    ax2.spines['left'].set_color('#cbd5e1')
    ax2.spines['bottom'].set_color('#cbd5e1')
    plt.title('Severity Breakdown per Category', fontweight='bold', color='#1e40af', pad=10)
    plt.tight_layout()
    tmp2 = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    plt.savefig(tmp2.name, format='png', transparent=True, dpi=150)
    plt.close(fig2)
    temp_files.append(tmp2.name)

    # Chart 3: Pie Chart (Operation Status)
    fig3, ax3 = plt.subplots(figsize=(4.5, 4.5))
    status_labels = ['Inactive', 'Offline', 'Detached']
    status_sizes = [19, 7, 2]
    status_colors = ['#94a3b8', '#f87171', '#facc15']
    ax3.pie(status_sizes, labels=status_labels, autopct='%1.1f%%', startangle=140, colors=status_colors,
            wedgeprops=dict(edgecolor='white', linewidth=2), textprops={'fontsize': 9})
    plt.title('Operation Status Breakdown', fontweight='bold', color='#1e40af', pad=10)
    plt.tight_layout()
    tmp3 = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    plt.savefig(tmp3.name, format='png', transparent=True, dpi=150)
    plt.close(fig3)
    temp_files.append(tmp3.name)

    # --- Draw Dashboard Layout ---
    # Top KPI Cards
    pdf.kpi_card(15, 30, 85, 35, "TOTAL ACTIVE ALERTS", "105", "+12% vs Last Month")
    pdf.kpi_card(106, 30, 85, 35, "TOOLS IN LEVEL 1", "57", "Needs Monitoring")
    pdf.kpi_card(197, 30, 85, 35, "TOOLS IN LEVEL 2", "20", "Requires Immediate Action")

    # Chart Backgrounds
    pdf.set_fill_color(255, 255, 255)
    pdf.set_draw_color(226, 232, 240)
    pdf.rect(15, 75, 85, 110, 'DF')
    pdf.rect(106, 75, 85, 110, 'DF')
    pdf.rect(197, 75, 85, 110, 'DF')

    # Place Charts
    pdf.image(tmp1.name, x=15, y=85, w=85)
    pdf.image(tmp2.name, x=105, y=85, w=85)
    pdf.image(tmp3.name, x=197, y=85, w=85)

    # ==========================================
    # PAGE 2: ACTIVE CONFIGURATIONS SUMMARY
    # ==========================================
    pdf.add_page()
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(0, 10, "ACTIVE ALERTS DIRECTORY", 0, 1, 'L')
    pdf.ln(2)
    
    # Table Header
    pdf.set_font('Arial', 'B', 9)
    pdf.set_fill_color(30, 58, 138)
    pdf.set_text_color(255, 255, 255)
    
    cols = ["Alert ID", "Alert Type", "Plant", "Tooling / Part", "Level 1 Cond", "Status"]
    col_widths = [30, 40, 30, 60, 80, 30] # Fits Landscape (270mm total)
    
    for i in range(len(cols)):
        pdf.cell(col_widths[i], 8, clean(cols[i]), 1, 0, 'C', 1)
    pdf.ln()
    
    # Table Rows
    pdf.set_font('Arial', '', 8)
    pdf.set_text_color(0, 0, 0)
    
    for _, row in df.iterrows():
        pdf.cell(col_widths[0], 8, clean(str(row["Alert ID"])[:20]), 1)
        pdf.cell(col_widths[1], 8, clean(str(row["Alert Type"])[:25]), 1)
        pdf.cell(col_widths[2], 8, clean(str(row["Plant"])[:20]), 1)
        pdf.cell(col_widths[3], 8, clean(str(row["Tooling / Part"])[:40]), 1)
        pdf.cell(col_widths[4], 8, clean(str(row["Level 1 Condition"])[:50]), 1)
        pdf.cell(col_widths[5], 8, clean(str(row["Status"])), 1)
        pdf.ln()
        
    try:
        output = bytes(pdf.output())
    except TypeError:
        output = pdf.output(dest='S').encode('latin-1')

    # Clean up temp image files
    for tmp_file in temp_files:
        try:
            os.remove(tmp_file)
        except OSError:
            pass

    return output

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
        
        # Multiselect for grouping users under a server
        selected_users = st.multiselect("Select User(s)", mock_users[selected_server], default=[mock_users[selected_server][0]])
        st.caption("You can select multiple users to apply the same configuration to an entire group.")
        
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
            
            # Dummy data simulating the user's currently assigned alerts
            dummy_alerts_df = pd.DataFrame({
                "Alert ID": ["ALT-1024", "ALT-1025", "ALT-1026", "ALT-1027", "ALT-1028"],
                "Alert Type": ["Cycle Time", "Run Rate", "Capacity Risk", "Tooling EOL", "Operation Status"],
                "OEM Division": ["Div A", "All", "Div B", "All", "Div C"],
                "Supplier": ["Supplier X", "All", "Supplier Y", "Supplier Z", "All"],
                "Plant": ["Plant 1", "All", "Plant 2", "All", "Plant 3"],
                "Tooling / Part": ["Tool_A", "All", "Product Alpha", "Part 101", "Tool_C"],
                "Level 1 Condition": ["0% ≤ dev ≤ 5%", "80% ≤ RR ≤ 100%", "0% ≤ loss ≤ 5%", "80% ≤ shots ≤ 90%", "Sensor Offline"],
                "Status": ["Active", "Active", "Inactive", "Active", "Active"],
            })

            export_format = st.radio("Format", ["CSV", "PDF"], horizontal=True, label_visibility="collapsed")
            
            if export_format == "CSV":
                export_data = dummy_alerts_df.to_csv(index=False).encode('utf-8')
                file_extension = "csv"
                mime_type = "text/csv"
                
                st.download_button(
                    label="⬇️ Download CSV",
                    data=export_data,
                    file_name=f"assigned_alerts_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
                    mime=mime_type,
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
                        val = st.number_input(f"Level {i+1} Limit (±%)", 
                                              min_value=c_min, 
                                              max_value=200, 
                                              value=def_val, 
                                              key=f"ct_limit_{i}")
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
            
            # Helper to render Run Rate logic dynamically for both tabs
            def render_run_rate_logic(rr_type, prefix):
                with st.container(border=True):
                    st.markdown("##### 'No Alert' Zone")
                    st.write(f"Alerts will be suppressed when {rr_type.lower()} stays above this value.")
                    no_alert_zone = st.number_input("No Alert Zone (Above %)", min_value=1, max_value=100, value=85, key=f"{prefix}_no_alert")
                    st.info(f"Production is considered **Healthy** when {rr_type.lower()} is **≥ {no_alert_zone}%**.")
                    st.divider()

                    st.markdown("##### Configuration: Number of Levels")
                    rr_num = st.number_input("How many alert levels do you want to configure?", min_value=1, max_value=5, value=2, key=f"{prefix}_num_levels")
                    
                    st.markdown("##### Threshold Boundaries")
                    st.write("Set the limit for each level as performance drops.")
                    
                    rr_limits = []
                    prev_val = no_alert_zone
                    rr_cols = st.columns(rr_num)
                    
                    for i in range(rr_num):
                        with rr_cols[i]:
                            c_max = max(0, prev_val - 1)
                            def_val = max(0, min(c_max, prev_val - 15))
                            val = st.number_input(f"Level {i+1} Limit (%)", 
                                                  min_value=0, 
                                                  max_value=c_max, 
                                                  value=def_val, 
                                                  key=f"{prefix}_limit_{i}")
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

            with rr_tab1:
                render_run_rate_logic("Run Rate Shot Efficiency", "eff")
            with rr_tab2:
                render_run_rate_logic("Run Rate Time Stability", "stab")

    # --- 3. CAPACITY RISK ---
    with tab3:
        st.subheader("Capacity Risk Alerts")
        st.write("Alerts based on lost parts vs capacity goals.")
        
        cr_enabled = st.toggle("Enable Capacity Risk Alerts", value=True, key="cr_toggle")
        
        if cr_enabled:
            cr_tab1, cr_tab2 = st.tabs(["Lost parts vs Optimal Capacity", "Lost parts vs Target Capacity"])
            
            def render_capacity_logic(cr_type, prefix, is_target=False):
                with st.container(border=True):
                    if is_target:
                        st.markdown("##### Target Definition")
                        target_cap = st.number_input("Target Capacity Output (%)", value=90, min_value=1, max_value=100, help="Define the target to calculate lost parts.", key=f"{prefix}_target")
                        st.info(f"Calculations will be evaluated against **{target_cap}%** capacity output.")
                        st.divider()

                    st.markdown("##### Configuration: Number of Levels")
                    cr_num = st.number_input("How many alert levels do you want to configure?", min_value=1, max_value=5, value=2, key=f"{prefix}_num_levels")
                    
                    st.markdown("##### Threshold Boundaries")
                    st.write("Set the upper limit for capacity loss per level.")
                    
                    cr_limits = []
                    prev_val = 0
                    cr_cols = st.columns(cr_num)
                    
                    for i in range(cr_num):
                        with cr_cols[i]:
                            c_min = min(100, prev_val + 1)
                            def_val = min(100, max(c_min, prev_val + 10))
                            val = st.number_input(f"Level {i+1} Limit (%)", 
                                                  min_value=c_min, 
                                                  max_value=100, 
                                                  value=def_val, 
                                                  key=f"{prefix}_limit_{i}")
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

            with cr_tab1:
                render_capacity_logic("Optimal Capacity", "opt")
            with cr_tab2:
                render_capacity_logic("Target Capacity", "tgt", is_target=True)

    # --- 4. TOOLING END OF LIFE ---
    with tab4:
        st.subheader("Tooling End of Life Alerts")
        st.write("Alerts for tools approaching their forecasted maximum tool life.")
        
        eol_enabled = st.toggle("Enable Tooling End of Life Alerts", value=True, key="eol_toggle")
        
        if eol_enabled:
            with st.container(border=True):
                st.markdown("##### Configuration Mode")
                eol_mode = st.radio("Choose how End of Life alerts should be evaluated:", 
                                    ["Utilization Rate (%)", "Remaining Days", "Combination (Whichever comes first)"], 
                                    horizontal=True)
                
                show_util = eol_mode in ["Utilization Rate (%)", "Combination (Whichever comes first)"]
                show_days = eol_mode in ["Remaining Days", "Combination (Whichever comes first)"]
                
                st.divider()
                st.markdown("##### Configuration: Number of Levels")
                eol_num = st.number_input("How many alert levels do you want to configure?", min_value=1, max_value=5, value=2, key="eol_num_levels")
                
                st.markdown("##### Threshold Boundaries")
                
                util_limits, days_limits = [], []
                
                if show_util:
                    st.write("**Utilization Rate (%) Limits**")
                    st.write("Set the base starting percentage, followed by the upper limits for each level.")
                    
                    base_start = st.number_input("Start Monitoring At (% of forecasted max shot)", min_value=0, max_value=99, value=80, key="eol_base")
                    
                    prev_val = base_start
                    eol_cols = st.columns(eol_num)
                    
                    for i in range(eol_num):
                        with eol_cols[i]:
                            c_min = min(200, prev_val + 1)
                            def_val = min(200, max(c_min, prev_val + 10))
                            val = st.number_input(f"Level {i+1} Upper Limit (%)", 
                                                  min_value=c_min, 
                                                  max_value=200, 
                                                  value=def_val, 
                                                  key=f"eol_limit_{i}")
                            util_limits.append(val)
                            prev_val = val
                    st.write("")
                    
                if show_days:
                    st.write("**Remaining Days Limits**")
                    st.write("Set the limits for each level. Days count backwards (e.g., alert when 30 days left, then 15 days left).")
                    
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
                            conds.append(f"Shots are between **{lower}% and {upper}%** of forecasted max shot.\n\n`{lower}% {op} shots ≤ {upper}%`")
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
        st.write("Alerts for real-time status changes and machine connectivity.")
        
        os_enabled = st.toggle("Enable Operation Status Alerts", value=True, key="os_toggle")
        
        if os_enabled:
            with st.container(border=True):
                st.markdown("##### Real-Time Event Alerts")
                
                st.checkbox("Tool Starts Producing", 
                            value=True, 
                            help="Triggered by a run interval threshold indicating the start of a new production run. This is defined and integrated directly within the Run Rate application.")
                st.caption("*'Tool Starts Producing' is managed and configured directly through the Run Rate system logic.*")
                
                st.write("")
                
                st.checkbox("Tool Stops", 
                            value=False, 
                            help="Triggered via Tool Movement Detection (TMD). Will be enabled once the TMD feature is fully implemented.")
                st.caption("*'Tool Stops' capability is pending Tool Movement Detection (TMD) module availability.*")
                
                st.divider()

                st.markdown("##### Connectivity & Status-Based Alerts")
                c1, c2 = st.columns(2)
                with c1:
                    st.multiselect("Trigger when tools remain in:", 
                                   ["Sensor offline", "Inactive", "Sensor detached"],
                                   default=["Sensor offline"])
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
        # Filter controls for the dashboard
        st.markdown("##### 🔍 Filter Configurations")
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            server_filter = st.multiselect("Filter by Server", options=st.session_state.admin_log['Server'].unique(), default=[])
        with f_col2:
            alert_filter = st.multiselect("Filter by Alert Type", options=st.session_state.admin_log['Alert Type'].unique(), default=[])
        
        st.divider()
        
        # Apply filtering
        display_df = st.session_state.admin_log
        if server_filter:
            display_df = display_df[display_df['Server'].isin(server_filter)]
        if alert_filter:
            display_df = display_df[display_df['Alert Type'].isin(alert_filter)]
            
        st.dataframe(
            display_df, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Timestamp": st.column_config.DatetimeColumn("Date & Time", format="YYYY-MM-DD h:mm A"),
                "Server": st.column_config.TextColumn("Target Server"),
                "Users": st.column_config.TextColumn("Assigned User Groups"),
                "Alert Type": st.column_config.TextColumn("Alert Type"),
                "Target Scope (Filters)": st.column_config.TextColumn("Filters Applied")
            }
        )

# ==========================================
#        CLIENT ALERTS PORTAL
# ==========================================
elif page == "Client Alerts Portal":
    
    # Manage View State (List vs Detail)
    def set_view(view_mode, alert_id=None):
        st.session_state.client_portal_view = view_mode
        st.session_state.selected_alert_id = alert_id

    # ---------------------------------------------------------
    # MAIN LISTING PAGE
    # ---------------------------------------------------------
    if st.session_state.client_portal_view == "list":
        st.markdown('<div class="main-header">My Active Alerts</div>', unsafe_allow_html=True)
        st.markdown('<div class="sub-header">Review, filter, and drill-down into triggered alerts relevant to your assigned scope.</div>', unsafe_allow_html=True)
        
        df = st.session_state.client_alerts_db.copy()
        
        # Apply filters from the sidebar
        if client_filters.get("OEM"): 
            df = df[df['OEM Division'].isin(client_filters["OEM"])]
        if client_filters.get("Supplier"): 
            df = df[df['Supplier'].isin(client_filters["Supplier"])]
        if client_filters.get("Plant"): 
            df = df[df['Plant'].isin(client_filters["Plant"])]
        if client_filters.get("Tooling Type"): 
            df = df[df['Tooling Type'].isin(client_filters["Tooling Type"])]
        if client_filters.get("Part"): 
            df = df[df['Part'].isin(client_filters["Part"])]
        if client_filters.get("Tooling"): 
            df = df[df['Tool'].isin(client_filters["Tooling"])]
        
        # Search bar 
        search_query = st.text_input("🔍 Search (Tool, Part, Name)")
        if search_query:
            df = df[df.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)]

        st.write(f"**Total Active Alerts in Scope: {len(df)}**")
        st.write("")
        
        # Helper function to format the trigger values
        def format_trigger_value(row):
            val = str(row['Metric_1'])
            if pd.notna(row['Metric_2']) and str(row['Metric_2']).strip():
                val += f" | {row['Metric_2']}"
            return val
            
        # Helper function to render the structured hierarchy tables
        def render_alert_hierarchy(tab_df, tab_name):
            if tab_df.empty:
                st.info("No alerts found for this category with the current filters.")
                return
            
            # Interactive Frequency Filter
            available_freqs = sorted(tab_df['Frequency'].unique())
            selected_freqs = st.multiselect(
                f"Filter by Alert Frequency", 
                options=available_freqs, 
                default=available_freqs, 
                key=f"freq_filter_{tab_name}"
            )
            
            filtered_df = tab_df[tab_df['Frequency'].isin(selected_freqs)].copy()
            
            if filtered_df.empty:
                st.info("No alerts match the selected frequency.")
                return
                
            filtered_df['Exact calculation/value'] = filtered_df.apply(format_trigger_value, axis=1)
            
            # Map mock data columns to the requested table columns
            display_cols = {
                "Tool": "Tooling ID",
                "Part": "Part ID (Part Name)",
                "OEM Division": "OEM Business Division",
                "Supplier": "Supplier",
                "Plant": "Plant",
                "Tooling Type": "Tooling Type",
                "Severity": "Severity",
                "Exact calculation/value": "Exact calculation/value",
                "Alert ID": "Alert ID" # Kept for drill-down reference
            }
            
            # Display Tables group exactly by Severity (as requested)
            for sev in sorted(filtered_df['Severity'].unique()):
                st.markdown(f"#### 📌 {sev}")
                sev_df = filtered_df[filtered_df['Severity'] == sev]
                
                out_df = sev_df[list(display_cols.keys())].rename(columns=display_cols)
                st.dataframe(out_df, use_container_width=True, hide_index=True)
                st.write("")

        # Create separate tabs for each Alert Type
        cat_tabs = st.tabs(["Cycle Time", "Run Rate", "Capacity Risk", "Tooling End of Life", "Operation Status"])
        
        with cat_tabs[0]:
            render_alert_hierarchy(df[df['Alert Type'] == 'Cycle Time'], "Cycle Time")
        with cat_tabs[1]:
            render_alert_hierarchy(df[df['Alert Type'].str.contains('Run Rate')], "Run Rate")
        with cat_tabs[2]:
            render_alert_hierarchy(df[df['Alert Type'].str.contains('Capacity Risk')], "Capacity Risk")
        with cat_tabs[3]:
            render_alert_hierarchy(df[df['Alert Type'].str.contains('EOL')], "EOL")
        with cat_tabs[4]:
            render_alert_hierarchy(df[df['Alert Type'].str.contains('Operation Status')], "Operation Status")
        
        st.divider()
        st.markdown("#### 📄 Drill-down into Alert Details")
        st.write("Select an Alert ID to view its dedicated detail page with exact triggering calculations.")
        
        select_col, btn_col, empty_col = st.columns([3, 1, 6])
        with select_col:
            selected_id = st.selectbox("Select Alert ID", df['Alert ID'].tolist(), label_visibility="collapsed")
        with btn_col:
            if st.button("View Details", type="primary", use_container_width=True):
                set_view("detail", selected_id)
                st.rerun()

    # ---------------------------------------------------------
    # INDIVIDUAL ALERT DETAIL PAGE
    # ---------------------------------------------------------
    elif st.session_state.client_portal_view == "detail":
        if st.button("🔙 Back to Alerts List"):
            set_view("list")
            st.rerun()
            
        # Fetch the selected alert data
        alert_data = st.session_state.client_alerts_db[st.session_state.client_alerts_db['Alert ID'] == st.session_state.selected_alert_id].iloc[0]
        
        st.write("")
        st.markdown(f"<h2>{alert_data['Alert Name']} <span style='color: #64748B; font-size: 1.5rem;'>({alert_data['Alert ID']})</span></h2>", unsafe_allow_html=True)
        
        # Severity Badge
        sev = alert_data['Severity']
        color = "#EF4444" if "Level 2" in sev else "#F59E0B" if "Level 1" in sev else "#3B82F6"
        st.markdown(f"<div style='background-color: {color}; color: white; padding: 4px 12px; border-radius: 20px; display: inline-block; font-weight: bold; font-size: 0.9rem; margin-bottom: 20px;'>Severity: {sev}</div>", unsafe_allow_html=True)
        
        # Top Metrics Cards (General Info)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"<div class='metric-card'><div class='metric-title'>Date & Time</div><div style='font-size: 1.2rem; font-weight: bold;'>{alert_data['Date/Time']}</div></div>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div class='metric-card'><div class='metric-title'>Frequency</div><div style='font-size: 1.2rem; font-weight: bold;'>{alert_data['Frequency']}</div></div>", unsafe_allow_html=True)
        with c3:
            st.markdown(f"<div class='metric-card'><div class='metric-title'>Tooling Type</div><div style='font-size: 1.2rem; font-weight: bold;'>{alert_data['Tooling Type']}</div></div>", unsafe_allow_html=True)
        with c4:
            st.markdown(f"<div class='metric-card'><div class='metric-title'>OEM Division</div><div style='font-size: 1.2rem; font-weight: bold;'>{alert_data['OEM Division']}</div></div>", unsafe_allow_html=True)

        # Entity Details
        st.markdown("#### 🏭 Entity Details")
        e1, e2, e3, e4 = st.columns(4)
        e1.metric("Target Tool", alert_data['Tool'])
        e2.metric("Associated Part", alert_data['Part'])
        e3.metric("Plant Location", alert_data['Plant'])
        e4.metric("Supplier", alert_data['Supplier'])
        
        st.divider()

        # DYNAMIC LOGIC DISPLAY ZONE
        st.markdown(f"#### 📊 Trigger Analytics: {alert_data['Alert Type']}")
        
        a_type = alert_data['Alert Type']
        m1 = alert_data['Metric_1']
        m2 = alert_data['Metric_2']
        
        # 1. Cycle Time
        if a_type == "Cycle Time":
            st.info("The tool is operating significantly outside the approved cycle time parameters.")
            st.markdown(f"<div class='metric-card'><div class='metric-title'>% Deviation vs Approved Cycle Time</div><div class='metric-value' style='color: #EF4444;'>{m1}</div></div>", unsafe_allow_html=True)
            
        # 2. Run Rate
        elif a_type == "Low Run Rate - Shot Efficiency":
            st.info("The tool is failing to achieve the expected output efficiency during scheduled operation hours.")
            st.markdown(f"<div class='metric-card'><div class='metric-title'>Current Run Rate Shot Efficiency</div><div class='metric-value' style='color: #F59E0B;'>{m1}</div></div>", unsafe_allow_html=True)
            
        elif a_type == "Low Run Rate - Time Stability":
            st.info("The tool's cycle times are highly unstable, affecting production predictability.")
            st.markdown(f"<div class='metric-card'><div class='metric-title'>Current Run Rate Time Stability</div><div class='metric-value' style='color: #F59E0B;'>{m1}</div></div>", unsafe_allow_html=True)
            
        # 3. Capacity Risk
        elif "Capacity Risk (Optimal)" in a_type:
            st.info("Calculating lost parts specifically against the optimal maximum theoretical capacity.")
            st.markdown(f"<div class='metric-card'><div class='metric-title'>% of Lost Parts Against Optimal Capacity</div><div class='metric-value' style='color: #EF4444;'>{m1}</div></div>", unsafe_allow_html=True)
            
        elif "Capacity Risk (Target)" in a_type:
            st.info("Calculating lost parts against your predefined targeted capacity baseline.")
            st.markdown(f"<div class='metric-card'><div class='metric-title'>% of Lost Parts Against Target Capacity</div><div class='metric-value' style='color: #EF4444;'>{m1}</div></div>", unsafe_allow_html=True)
            
        # 4. Tooling End of Life
        elif "EOL (Utilization)" in a_type:
            st.warning("Tool is approaching its maximum forecasted physical shot limit.")
            st.markdown(f"<div class='metric-card'><div class='metric-title'>Current Tool Life Used</div><div class='metric-value' style='color: #EF4444;'>{m1}</div></div>", unsafe_allow_html=True)
            
        elif "EOL (Remaining Days)" in a_type:
            st.warning("Tool life is severely depleted based on current running trajectory.")
            st.markdown(f"<div class='metric-card'><div class='metric-title'>Estimated Remaining Tool Life</div><div class='metric-value' style='color: #EF4444;'>{m1}</div></div>", unsafe_allow_html=True)
            
        elif "EOL (Combination)" in a_type:
            st.warning("Tool requires maintenance or replacement. A combination threshold has been breached.")
            cc1, cc2 = st.columns(2)
            with cc1:
                st.markdown(f"<div class='metric-card'><div class='metric-title'>Current Tool Life Used</div><div class='metric-value' style='color: #EF4444;'>{m1}</div></div>", unsafe_allow_html=True)
            with cc2:
                st.markdown(f"<div class='metric-card'><div class='metric-title'>Estimated Remaining Tool Life</div><div class='metric-value' style='color: #EF4444;'>{m2}</div></div>", unsafe_allow_html=True)
                
        # 5. Operation Status
        elif "Tool Producing" in a_type:
            st.success("A new continuous production run interval was verified by the system.")
            st.markdown(f"<div class='metric-card'><div class='metric-title'>Exact Start Timestamp</div><div class='metric-value' style='color: #10B981;'>{m1}</div></div>", unsafe_allow_html=True)
            
        elif "Tool Stops" in a_type:
            st.error("The tool was abruptly removed from the press based on TMD diagnostics.")
            st.markdown(f"<div class='metric-card'><div class='metric-title'>Exact Stop Timestamp</div><div class='metric-value' style='color: #EF4444;'>{m1}</div></div>", unsafe_allow_html=True)
            
        else: # Offline, Inactive, Detached
            st.error("A critical connectivity or sensor status change was detected.")
            st.markdown(f"<div class='metric-card'><div class='metric-title'>Status Change Timestamp</div><div class='metric-value' style='color: #EF4444;'>{m1}</div></div>", unsafe_allow_html=True)