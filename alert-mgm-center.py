import streamlit as st
import pandas as pd
import datetime

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Alert Management Center | Emoldino",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SESSION STATE FOR ADMIN LOGGING ---
if 'admin_log' not in st.session_state:
    st.session_state.admin_log = pd.DataFrame(columns=[
        "Timestamp", "Server", "User", "Alert Type", "Target Scope (Filters)"
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
def render_filters(key_prefix, layout="vertical"):
    if layout == "vertical":
        oem = st.multiselect("OEM Business Division", ["Div A", "Div B", "Div C"], key=f"{key_prefix}_oem")
        sup = st.multiselect("Supplier", ["Supplier X", "Supplier Y", "Supplier Z"], key=f"{key_prefix}_sup")
        plt = st.multiselect("Plant", ["Plant 1", "Plant 2", "Plant 3"], key=f"{key_prefix}_plt")
        prod = st.multiselect("Product", ["Product Alpha", "Product Beta"], key=f"{key_prefix}_prod")
        ttype = st.multiselect("Tooling Type", ["Injection", "Stamping", "Die Casting"], key=f"{key_prefix}_type")
        part = st.multiselect("Part", ["Part 101", "Part 102", "Part 103"], key=f"{key_prefix}_part")
        tool = st.multiselect("Tooling", ["Tool_A", "Tool_B", "Tool_C", "Tool_D"], key=f"{key_prefix}_tool")
    else:
        c1, c2, c3 = st.columns(3)
        with c1:
            oem = st.multiselect("OEM Business Division", ["Div A", "Div B", "Div C"], key=f"{key_prefix}_oem")
            sup = st.multiselect("Supplier", ["Supplier X", "Supplier Y", "Supplier Z"], key=f"{key_prefix}_sup")
            plt = st.multiselect("Plant", ["Plant 1", "Plant 2", "Plant 3"], key=f"{key_prefix}_plt")
        with c2:
            prod = st.multiselect("Product", ["Product Alpha", "Product Beta"], key=f"{key_prefix}_prod")
            ttype = st.multiselect("Tooling Type", ["Injection", "Stamping", "Die Casting"], key=f"{key_prefix}_type")
            part = st.multiselect("Part", ["Part 101", "Part 102", "Part 103"], key=f"{key_prefix}_part")
        with c3:
            tool = st.multiselect("Tooling", ["Tool_A", "Tool_B", "Tool_C", "Tool_D"], key=f"{key_prefix}_tool")
            
    return {"OEM": oem, "Supplier": sup, "Plant": plt, "Product": prod, "Tooling Type": ttype, "Part": part, "Tooling": tool}

# --- SIDEBAR: NAVIGATION & GLOBAL SETTINGS ---
with st.sidebar:
    
    st.markdown("### Application Mode")
    app_mode = st.radio("Select View:", ["User View", "eMoldino Admin Panel"])
    
    st.divider()
    
    if app_mode == "User View":
        st.markdown("### Data Filters")
        st.caption("Select desired filters first to define the target scope of your alerts. Leave empty to apply globally.")
        user_filters = render_filters("user", layout="vertical")

# ==========================================
#              USER VIEW
# ==========================================
if app_mode == "User View":
    st.markdown('<div class="main-header">Alert Management Center</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Digitalize. Streamline. Transform. | Monitor manufacturing performance and tooling conditions.</div>', unsafe_allow_html=True)

    left_panel, right_panel = st.columns([1, 3], gap="large")
    
    with left_panel:
        st.markdown("### Export Assigned Alerts")
        st.caption("Export your configured alerts summary or send it directly via email.")
        
        # Comprehensive Data Design simulating the user's currently assigned alerts
        dummy_alerts_df = pd.DataFrame({
            "Alert ID": ["ALT-1024", "ALT-1025", "ALT-1026", "ALT-1027", "ALT-1028"],
            "Alert Type": ["Cycle Time", "Run Rate", "Capacity Risk", "Tooling EOL", "Operation Status"],
            "OEM Division": ["Div A", "All", "Div B", "All", "Div C"],
            "Supplier": ["Supplier X", "All", "Supplier Y", "Supplier Z", "All"],
            "Plant": ["Plant 1", "All", "Plant 2", "All", "Plant 3"],
            "Tooling / Part": ["Tool_A", "All", "Product Alpha", "Part 101", "Tool_C"],
            "Level 1 Condition": ["0% ≤ dev ≤ 5%", "80% ≤ RR ≤ 100%", "0% ≤ loss ≤ 5%", "80% ≤ shots ≤ 90%", "Sensor Offline"],
            "Level 2 Condition": ["5% < dev ≤ 15%", "50% ≤ RR < 80%", "5% < loss ≤ 15%", "90% < shots ≤ 100%", "Inactive/Detached"],
            "Frequency": ["Daily", "Weekly", "Monthly", "Weekly", "Real time"],
            "Status": ["Active", "Active", "Inactive", "Active", "Active"],
            "Last Modified": ["2026-04-10", "2026-04-12", "2026-04-14", "2026-04-15", "2026-04-16"]
        })
        
        with st.expander("Preview Export Data"):
            st.dataframe(dummy_alerts_df, use_container_width=True)

        export_format = st.radio("Select Export Format", ["CSV", "PDF"], horizontal=True)
        
        if export_format == "CSV":
            export_data = dummy_alerts_df.to_csv(index=False).encode('utf-8')
            file_extension = "csv"
            mime_type = "text/csv"
        else:
            # Generate PDF using the new built-in pure Python function!
            export_data = generate_pure_python_pdf(dummy_alerts_df)
            file_extension = "pdf"
            mime_type = "application/pdf"
            
        st.download_button(
            label=f"Download {export_format} Report",
            data=export_data,
            file_name=f"assigned_alerts_{datetime.datetime.now().strftime('%Y%m%d')}.{file_extension}",
            mime=mime_type,
            use_container_width=True
        )
        
        with st.popover("Send to Email", use_container_width=True):
            st.write("Send report to email")
            email_input = st.text_input("Email Address", value="admin.plant@emoldino.com")
            
            if 'file_extension' in locals():
                st.caption(f"Attachment: assigned_alerts.{file_extension}")
            
            if st.button("Send Now", type="primary", use_container_width=True):
                st.success(f"Report successfully sent to {email_input}!")

    with right_panel:
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
            st.write("Alerts based on deviation from approved cycle time (ACT).")
            
            ct_enabled = st.toggle("Enable Cycle Time Alerts", value=True, key="ct_toggle")
            
            if ct_enabled:
                with st.container(border=True):
                    st.markdown("##### Configuration: Number of Levels")
                    ct_num = st.number_input("How many alert levels do you want to configure?", min_value=1, max_value=5, value=2, key="ct_num_levels")
                    
                    st.markdown("##### Threshold Boundaries")
                    st.write("Set the upper limit for each level. The system prevents overlapping to avoid errors.")
                    
                    ct_limits = []
                    prev_val = 0
                    ct_cols = st.columns(ct_num)
                    
                    for i in range(ct_num):
                        with ct_cols[i]:
                            val = st.number_input(f"Level {i+1} Upper Limit (%)", 
                                                  min_value=prev_val + 1, 
                                                  max_value=200, 
                                                  value=prev_val + 5, 
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
                            txt = f"**Level {i+1}**\n\nTriggers when deviation is between **{lower}% and {upper}%**.\n\n`{lower}% {op} deviation ≤ {upper}%`"
                            display_level_box(i, txt)
                    
                    st.divider()
                    ct_freq = st.selectbox("Alert Frequency", ["Hourly", "Daily", "Weekly", "Monthly"], key="ct_freq")
                    
                if st.button("Save Cycle Time Settings", type="primary"):
                    st.success("Cycle Time alert settings saved successfully for the selected filters!")

        # --- 2. RUN RATE ---
        with tab2:
            st.subheader("Run Rate Alerts")
            st.write("Alerts based on Run Rate Efficiency and Stability.")
            
            rr_enabled = st.toggle("Enable Run Rate Alerts", value=True, key="rr_toggle")
            
            if rr_enabled:
                rr_condition = st.radio("Trigger Condition", ["Low Run Rate Efficiency", "Low Run Rate Stability"], horizontal=True)
                
                with st.container(border=True):
                    st.markdown("##### Configuration: Number of Levels")
                    rr_num = st.number_input("How many alert levels do you want to configure?", min_value=1, max_value=5, value=2, key="rr_num_levels")
                    
                    st.markdown("##### Threshold Boundaries")
                    st.write("Set the lower limit for each level as performance drops.")
                    
                    rr_limits = []
                    prev_val = 100
                    rr_cols = st.columns(rr_num)
                    
                    for i in range(rr_num):
                        with rr_cols[i]:
                            # Ensure the next level is lower than the previous level
                            val = st.number_input(f"Level {i+1} Lower Limit (%)", 
                                                  min_value=0, 
                                                  max_value=prev_val - 1, 
                                                  value=max(0, prev_val - 15), 
                                                  key=f"rr_limit_{i}")
                            rr_limits.append(val)
                            prev_val = val
                    
                    st.markdown("##### Alert Conditions Summary")
                    rr_disp_cols = st.columns(rr_num)
                    for i in range(rr_num):
                        with rr_disp_cols[i]:
                            upper = 100 if i == 0 else rr_limits[i-1]
                            lower = rr_limits[i]
                            op = "≤" if i == 0 else "<"
                            txt = f"**Level {i+1}**\n\nTriggers when rate drops between **{lower}% and {upper}%**.\n\n`{lower}% ≤ rate {op} {upper}%`"
                            display_level_box(i, txt)

                    st.divider()
                    rr_freq = st.selectbox("Alert Frequency", ["Daily", "Weekly", "Monthly"], key="rr_freq")
                    
                if st.button("Save Run Rate Settings", type="primary"):
                    st.success("Run Rate alert settings saved successfully for the selected filters!")

        # --- 3. CAPACITY RISK ---
        with tab3:
            st.subheader("Capacity Risk Alerts")
            st.write("Alerts based on lost parts vs optimal or target capacity.")
            
            cr_enabled = st.toggle("Enable Capacity Risk Alerts", value=True, key="cr_toggle")
            
            if cr_enabled:
                cr_condition = st.radio("Trigger Condition", ["Lost parts vs Optimal Capacity", "Lost parts vs Target Capacity"], horizontal=True)
                
                with st.container(border=True):
                    if cr_condition == "Lost parts vs Target Capacity":
                        st.markdown("##### Target Definition")
                        target_cap = st.number_input("Target Capacity Output (%)", value=90, min_value=1, max_value=100, help="Define the percentage to enable calculation of lost parts.")
                        st.info(f"Calculations will be evaluated against **{target_cap}%** capacity output.")
                        st.write("---")

                    st.markdown("##### Configuration: Number of Levels")
                    cr_num = st.number_input("How many alert levels do you want to configure?", min_value=1, max_value=5, value=2, key="cr_num_levels")
                    
                    st.markdown("##### Threshold Boundaries")
                    st.write("Set the upper limit for capacity loss per level.")
                    
                    cr_limits = []
                    prev_val = 0
                    cr_cols = st.columns(cr_num)
                    
                    for i in range(cr_num):
                        with cr_cols[i]:
                            val = st.number_input(f"Level {i+1} Upper Limit (%)", 
                                                  min_value=prev_val + 1, 
                                                  max_value=100, 
                                                  value=min(100, prev_val + 10), 
                                                  key=f"cr_limit_{i}")
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
                    cr_freq = st.selectbox("Alert Frequency", ["Daily", "Weekly", "Monthly"], key="cr_freq")
                    
                if st.button("Save Capacity Risk Settings", type="primary"):
                    st.success("Capacity Risk alert settings saved successfully for the selected filters!")

        # --- 4. TOOLING END OF LIFE ---
        with tab4:
            st.subheader("Tooling End of Life Alerts")
            st.write("Alerts for tools approaching their forecasted maximum shot count.")
            
            eol_enabled = st.toggle("Enable Tooling End of Life Alerts", value=True, key="eol_toggle")
            
            if eol_enabled:
                with st.container(border=True):
                    st.markdown("##### Configuration: Number of Levels")
                    eol_num = st.number_input("How many alert levels do you want to configure?", min_value=1, max_value=5, value=2, key="eol_num_levels")
                    
                    st.markdown("##### Threshold Boundaries")
                    st.write("Set the base starting percentage, followed by the upper limits for each level.")
                    
                    base_start = st.number_input("Start Monitoring At (% of max shots)", min_value=0, max_value=99, value=80, key="eol_base")
                    
                    eol_limits = []
                    prev_val = base_start
                    eol_cols = st.columns(eol_num)
                    
                    for i in range(eol_num):
                        with eol_cols[i]:
                            val = st.number_input(f"Level {i+1} Upper Limit (%)", 
                                                  min_value=prev_val + 1, 
                                                  max_value=200, 
                                                  value=min(200, prev_val + 10), 
                                                  key=f"eol_limit_{i}")
                            eol_limits.append(val)
                            prev_val = val
                    
                    st.markdown("##### Alert Conditions Summary")
                    eol_disp_cols = st.columns(eol_num)
                    for i in range(eol_num):
                        with eol_disp_cols[i]:
                            lower = base_start if i == 0 else eol_limits[i-1]
                            upper = eol_limits[i]
                            op = "≤" if i == 0 else "<"
                            txt = f"**Level {i+1}**\n\nTriggers when shots are between **{lower}% and {upper}%** of maximum.\n\n`{lower}% {op} shots ≤ {upper}%`"
                            display_level_box(i, txt)

                    st.divider()
                    eol_freq = st.selectbox("Alert Frequency", ["Daily", "Weekly", "Monthly"], key="eol_freq")
                    
                if st.button("Save Tooling EOL Settings", type="primary"):
                    st.success("Tooling End of Life settings saved successfully for the selected filters!")

        # --- 5. OPERATION STATUS ---
        with tab5:
            st.subheader("Tooling Operation Status Alerts")
            st.write("Alerts for real-time status changes and offline sensors.")
            
            os_enabled = st.toggle("Enable Operation Status Alerts", value=True, key="os_toggle")
            
            if os_enabled:
                with st.container(border=True):
                    st.markdown("##### Status-Based Alerts")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.multiselect("Trigger when tools remain in:", 
                                       ["Sensor offline", "Inactive", "Sensor detached"],
                                       default=["Sensor offline"])
                    with c2:
                        st.selectbox("Alert Frequency", ["Daily", "Weekly", "Monthly", "Real time"], index=3, key="os_freq")
                        
                    st.divider()
                    st.markdown("##### Real-Time Event Alerts")
                    st.checkbox("Tooling starts producing (Tool in press starts producing)", value=True)
                    st.checkbox("Tooling goes out of the machine (Tool is removed from press)", value=True)
                    st.caption("*Real-time alerts are triggered immediately upon event detection.*")
                    
                if st.button("Save Operation Status Settings", type="primary"):
                    st.success("Operation Status alert settings saved successfully for the selected filters!")

# ==========================================
#          eMOLDINO ADMIN PANEL
# ==========================================
elif app_mode == "eMoldino Admin Panel":
    st.markdown('<div class="main-header">eMoldino Central Admin Panel</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Set up and program alerts on behalf of users across different servers.</div>', unsafe_allow_html=True)
    
    with st.container(border=True):
        st.subheader("1. User Selection")
        col_svr, col_usr = st.columns(2)
        with col_svr:
            selected_server = st.selectbox("Target Server", ["JLR Server", "GM Server", "Paccar Server"])
        
        # Mock users based on server selection
        mock_users = {
            "JLR Server": ["John Doe (john.doe@jlr.com)", "Jane Smith (jane.smith@jlr.com)"],
            "GM Server": ["Mike Johnson (mjohnson@gm.com)", "Sarah Connor (sconnor@gm.com)"],
            "Paccar Server": ["David Lee (d.lee@paccar.com)", "Emma Wilson (e.wilson@paccar.com)"]
        }
        
        with col_usr:
            selected_user = st.selectbox("Select User", mock_users[selected_server])

    with st.container(border=True):
        st.subheader("2. Alert Definition Flow")
        
        st.markdown("##### Step 1: Configure Target Scope (Filters)")
        st.caption("Select all filters or a subset for this alert.")
        admin_filters = render_filters("admin", layout="horizontal")
            
        st.divider()
        
        st.markdown("##### Step 2: Select Alert Type")
        selected_alert = st.selectbox("Select Alert Type to Program", 
                                      ["Cycle Time", "Run Rate", "Capacity Risk", "Tooling End of Life", "Operation Status"])
            
        if st.button("Program Alert for User", type="primary"):
            # Format the selected filters for logging
            active_filters = {k: v for k, v in admin_filters.items() if v}
            filter_str = " | ".join([f"{k}: {', '.join(v)}" for k, v in active_filters.items()])
            
            if not filter_str:
                filter_str = "Global (No filters applied)"
            
            # Add to log
            new_log = pd.DataFrame([{
                "Timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Server": selected_server,
                "User": selected_user,
                "Alert Type": selected_alert,
                "Target Scope (Filters)": filter_str
            }])
            st.session_state.admin_log = pd.concat([new_log, st.session_state.admin_log], ignore_index=True)
            st.success(f"Successfully programmed '{selected_alert}' alert for {selected_user}!")

    st.markdown("### Programmed Alerts Log")
    st.caption("A track record of all alerts set up by eMoldino administrators.")
    
    if st.session_state.admin_log.empty:
        st.info("No alerts have been programmed yet in this session.")
    else:
        st.dataframe(st.session_state.admin_log, use_container_width=True, hide_index=True)