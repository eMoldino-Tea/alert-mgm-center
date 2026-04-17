import streamlit as st
import pandas as pd
import datetime

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Alert Management Center | eMoldino Service",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SESSION STATE FOR ADMIN LOGGING ---
if 'admin_log' not in st.session_state:
    st.session_state.admin_log = pd.DataFrame(columns=[
        "Timestamp", "Server", "User", "Alert Type", "Target Scope (Filters)", "Configuration details"
    ])

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

# --- PURE PYTHON PDF GENERATOR (ZERO DEPENDENCIES) ---
def generate_pure_python_pdf(df):
    """Generates a valid PDF byte string from a DataFrame without external libraries."""
    cols_to_print = ["Alert ID", "Alert Type", "Plant", "Tooling / Part", "Level 1 Condition", "Status"]
    widths = [12, 18, 12, 20, 22, 10]
    
    lines = []
    lines.append("eMoldino - Alert Management Center")
    lines.append("Assigned Alerts Configuration Summary")
    lines.append(f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    
    # Format header
    header = "".join([cols_to_print[i].ljust(widths[i]) for i in range(len(cols_to_print))])
    lines.append(header)
    lines.append("-" * sum(widths))
    
    # Format rows
    for _, row in df.iterrows():
        row_str = "".join([str(row[cols_to_print[i]])[:widths[i]-1].ljust(widths[i]) for i in range(len(cols_to_print))])
        lines.append(row_str)
        
    # Build raw PDF stream
    stream_data = "BT\n/F1 11 Tf\n30 540 Td\n15 TL\n"
    for line in lines:
        clean_line = line.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
        stream_data += f"({clean_line}) Tj\nT*\n"
    stream_data += "ET"
    
    stream_bytes = stream_data.encode('latin-1', 'replace')
    
    # Build PDF Objects
    objects = [
        b"%PDF-1.4\n",
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 842 595] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n",
        f"4 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n".encode('ascii') + stream_bytes + b"\nendstream\nendobj\n",
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>\nendobj\n"
    ]
    
    # Compile file structure & XREF table
    pdf_content = bytearray()
    xref_offsets = []
    
    for obj in objects:
        if obj.startswith(b"%PDF"):
            pdf_content.extend(obj)
        else:
            xref_offsets.append(len(pdf_content))
            pdf_content.extend(obj)
            
    xref_start = len(pdf_content)
    pdf_content.extend(b"xref\n0 6\n0000000000 65535 f \n")
    for offset in xref_offsets:
        pdf_content.extend(f"{offset:010d} 00000 n \n".encode('ascii'))
        
    pdf_content.extend(f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF".encode('ascii'))
    return bytes(pdf_content)

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

def log_admin_action(alert_type, filters, selected_server, selected_user, details="Configured successfully"):
    active_filters = {k: v for k, v in filters.items() if v}
    filter_str = " | ".join([f"{k}: {', '.join(v)}" for k, v in active_filters.items()])
    if not filter_str:
        filter_str = "Global (No filters applied)"
        
    new_log = pd.DataFrame([{
        "Timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Server": selected_server,
        "User": selected_user,
        "Alert Type": alert_type,
        "Target Scope (Filters)": filter_str,
        "Configuration details": details
    }])
    st.session_state.admin_log = pd.concat([new_log, st.session_state.admin_log], ignore_index=True)
    st.success(f"Successfully programmed '{alert_type}' alert for {selected_user}!")

# ==========================================
#         SIDEBAR: ADMIN & FILTERS
# ==========================================
with st.sidebar:
    st.image("https://via.placeholder.com/200x60?text=EMOLDINO", use_container_width=True)
    st.markdown("### User Assignment")
    selected_server = st.selectbox("Target Server", ["JLR Server", "GM Server", "Paccar Server"])
    
    mock_users = {
        "JLR Server": ["John Doe (john.doe@jlr.com)", "Jane Smith (jane.smith@jlr.com)"],
        "GM Server": ["Mike Johnson (mjohnson@gm.com)", "Sarah Connor (sconnor@gm.com)"],
        "Paccar Server": ["David Lee (d.lee@paccar.com)", "Emma Wilson (e.wilson@paccar.com)"]
    }
    selected_user = st.selectbox("Select User", mock_users[selected_server])
    
    st.divider()
    st.markdown("### Target Data Filters")
    user_filters = render_filters("admin_filters")

# ==========================================
#              MAIN CONTENT
# ==========================================

# Top Header & Export Button
header_col, export_col = st.columns([5, 1])

with header_col:
    st.markdown('<div class="main-header">Alert Configuration Management</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">eMoldino Service Center | Manage alert configurations centrally.</div>', unsafe_allow_html=True)
    
with export_col:
    st.write("")
    st.write("")
    
    with st.popover("📥 Export Config", use_container_width=True):
        st.caption(f"Export or email configuration summary for **{selected_user.split(' ')[0]}**.")
        
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
        else:
            export_data = generate_pure_python_pdf(dummy_alerts_df)
            file_extension = "pdf"
            mime_type = "application/pdf"
            
        st.download_button(
            label=f"⬇️ Download {export_format}",
            data=export_data,
            file_name=f"assigned_alerts_{datetime.datetime.now().strftime('%Y%m%d')}.{file_extension}",
            mime=mime_type,
            use_container_width=True
        )
        
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
            log_admin_action("Cycle Time", user_filters, selected_server, selected_user)

# --- 2. RUN RATE ---
with tab2:
    st.subheader("Run Rate Alerts")
    st.write("Alerts based on Run Rate Efficiency and Stability.")
    
    rr_enabled = st.toggle("Enable Run Rate Alerts", value=True, key="rr_toggle")
    
    if rr_enabled:
        rr_tab1, rr_tab2 = st.tabs(["📉 Low Run Rate Efficiency", "⚖️ Low Run Rate Stability"])
        
        # Helper to render Run Rate logic dynamically for both tabs
        def render_run_rate_logic(rr_type, prefix):
            with st.container(border=True):
                st.markdown("##### 'No Alert' Zone")
                st.write(f"Alerts will be suppressed when {rr_type.lower()} stays above this value.")
                no_alert_zone = st.number_input("No Alert Zone (Above %)", min_value=1, max_value=100, value=85, key=f"{prefix}_no_alert")
                st.info(f"🟢 Production is considered **Healthy** when {rr_type.lower()} is **≥ {no_alert_zone}%**.")
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
                log_admin_action(f"Run Rate ({rr_type})", user_filters, selected_server, selected_user)

        with rr_tab1:
            render_run_rate_logic("Run Rate Efficiency", "eff")
        with rr_tab2:
            render_run_rate_logic("Run Rate Stability", "stab")

# --- 3. CAPACITY RISK ---
with tab3:
    st.subheader("Capacity Risk Alerts")
    st.write("Alerts based on lost parts vs capacity goals.")
    
    cr_enabled = st.toggle("Enable Capacity Risk Alerts", value=True, key="cr_toggle")
    
    if cr_enabled:
        cr_tab1, cr_tab2 = st.tabs(["📉 Lost parts vs Optimal Capacity", "🎯 Lost parts vs Target Capacity"])
        
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
                log_admin_action(f"Capacity Risk ({cr_type})", user_filters, selected_server, selected_user)

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
            
            util_limits, days_limits = [], []
            
            for i in range(eol_num):
                st.markdown(f"**Level {i+1} Definition**")
                cols = st.columns(2)
                
                with cols[0]:
                    if show_util:
                        prev_u = 0 if i == 0 else util_limits[i-1]
                        val_u = st.number_input(f"Level {i+1} Utilization Limit (%)", min_value=prev_u + 1, max_value=200, value=min(200, prev_u + 10), key=f"eol_u_{i}")
                        util_limits.append(val_u)
                
                with cols[1]:
                    if show_days:
                        # Days count backwards (e.g., alert when 30 days left, then 10 days left)
                        prev_d = 365 if i == 0 else days_limits[i-1]
                        c_max = max(0, prev_d - 1)
                        val_d = st.number_input(f"Level {i+1} Remaining Days Limit", min_value=0, max_value=c_max, value=max(0, c_max - 15), key=f"eol_d_{i}")
                        days_limits.append(val_d)
            
            st.markdown("##### Alert Conditions Summary")
            eol_disp_cols = st.columns(eol_num)
            for i in range(eol_num):
                with eol_disp_cols[i]:
                    conds = []
                    if show_util:
                        lower_u = 0 if i == 0 else util_limits[i-1]
                        conds.append(f"Utilization reaches **{lower_u}% to {util_limits[i]}%**")
                    if show_days:
                        upper_d = 365 if i == 0 else days_limits[i-1]
                        conds.append(f"Remaining days fall to **{days_limits[i]} to {upper_d} days**")
                    
                    txt = f"**Level {i+1}**\n\nTriggers when:\n\n" + " \n\n**OR**\n\n ".join(conds)
                    display_level_box(i, txt)

            st.divider()
            eol_freq = st.selectbox("Alert Frequency", ["Daily", "Weekly", "Monthly"], key="eol_freq")
            
        if st.button("Save Tooling EOL Settings", type="primary"):
            log_admin_action("Tooling End of Life", user_filters, selected_server, selected_user, details=f"Mode: {eol_mode}")

# --- 5. OPERATION STATUS ---
with tab5:
    st.subheader("Operational Status Alerts")
    st.write("Alerts for real-time status changes and machine connectivity.")
    
    os_enabled = st.toggle("Enable Operation Status Alerts", value=True, key="os_toggle")
    
    if os_enabled:
        with st.container(border=True):
            st.markdown("##### Real-Time Event Alerts")
            
            st.checkbox("🟢 Tool Starts Producing", 
                        value=True, 
                        disabled=True, 
                        help="Triggered by a run interval threshold indicating the start of a new production run. This is defined and integrated directly within the Run Rate application.")
            st.caption("ℹ️ *'Tool Starts Producing' is managed and configured directly through the Run Rate system logic.*")
            
            st.write("")
            
            st.checkbox("🔴 Tool Stops", 
                        value=False, 
                        disabled=True, 
                        help="Triggered via Tool Movement Detection (TMD). Will be enabled once the TMD feature is fully implemented.")
            st.caption("ℹ️ *'Tool Stops' capability is pending Tool Movement Detection (TMD) module availability.*")
            
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
            log_admin_action("Operation Status", user_filters, selected_server, selected_user)

# ==========================================
#        ADMIN LOG DISPLAY
# ==========================================
st.divider()
st.markdown("### 📋 Programmed Alerts Log")
st.caption("Audit trail of all configurations applied by administrators during this session.")

if st.session_state.admin_log.empty:
    st.info("No alerts have been configured yet in this session.")
else:
    st.dataframe(st.session_state.admin_log, use_container_width=True, hide_index=True)