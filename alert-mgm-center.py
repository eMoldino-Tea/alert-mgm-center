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
    .formula-box {
        background-color: #f3f4f6;
        padding: 10px;
        border-radius: 5px;
        font-family: monospace;
        font-size: 1.1rem;
        color: #111827;
        margin-top: 10px;
        border-left: 4px solid #3b82f6;
    }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR: NAVIGATION & GLOBAL SETTINGS ---
with st.sidebar:
    st.image("https://via.placeholder.com/200x60?text=EMOLDINO", use_container_width=True)
    
    st.markdown("### Application Mode")
    app_mode = st.radio("Select View:", ["User View", "eMoldino Admin Panel"])
    
    st.divider()
    
    if app_mode == "User View":
        st.markdown("### Global Notification Settings")
        st.write("Select how you want to receive alerts globally:")
        
        in_system = st.checkbox("🔔 In-System Notifications", value=True)
        mobile_push = st.checkbox("📱 Mobile Push", value=True)
        email_notif = st.checkbox("✉️ Email", value=True)
        
        st.divider()
        st.markdown("### Account")
        st.write("👤 **User:** Admin")
        st.write("🏢 **Role:** Plant Manager")

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

# ==========================================
#              USER VIEW
# ==========================================
if app_mode == "User View":
    st.markdown('<div class="main-header">Alert Management Center</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Digitalize. Streamline. Transform. | Monitor manufacturing performance and tooling conditions.</div>', unsafe_allow_html=True)

    left_panel, right_panel = st.columns([1, 3], gap="large")
    
    with left_panel:
        st.markdown("### 🎯 Data Filters")
        st.caption("Select desired filters first to define the target scope of your alerts. Leave empty to apply globally.")
        user_filters = render_filters("user", layout="vertical")
        
        st.divider()
        st.markdown("### 📥 Export Assigned Alerts")
        st.caption("Export your configured alerts summary or send it directly via email.")
        
        # Dummy data simulating the user's currently assigned alerts
        dummy_alerts_df = pd.DataFrame({
            "Alert ID": ["ALT-1024", "ALT-1025", "ALT-1026", "ALT-1027"],
            "Alert Type": ["Cycle Time", "Run Rate", "Capacity Risk", "Operation Status"],
            "Target Scope": ["Plant 1 | Tool_A", "Global (All)", "Supplier X | Product Alpha", "Div A | Plant 2"],
            "Condition": ["0% ≤ dev ≤ 5%", "80% ≤ RR ≤ 100%", "0% ≤ loss ≤ 5%", "Sensor Offline"],
            "Frequency": ["Daily", "Weekly", "Monthly", "Real time"],
            "Status": ["Active", "Active", "Inactive", "Active"]
        })
        
        export_format = st.radio("Select Export Format", ["CSV", "PDF"], horizontal=True)
        
        if export_format == "CSV":
            export_data = dummy_alerts_df.to_csv(index=False).encode('utf-8')
            file_extension = "csv"
            mime_type = "text/csv"
        else:
            # A minimal valid dummy PDF byte string for sample purposes
            # In a production environment, you would use a library like `fpdf` or `reportlab` to generate this.
            export_data = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 57 >>\nstream\nBT /F1 24 Tf 100 700 Td (Alerts Summary Report) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000213 00000 n \ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n321\n%%EOF"
            file_extension = "pdf"
            mime_type = "application/pdf"
        
        st.download_button(
            label=f"⬇️ Download {export_format} Report",
            data=export_data,
            file_name=f"assigned_alerts_{datetime.datetime.now().strftime('%Y%m%d')}.{file_extension}",
            mime=mime_type,
            use_container_width=True
        )
        
        with st.popover("✉️ Send to Email", use_container_width=True):
            st.write("Send report to email")
            email_input = st.text_input("Email Address", value="admin.plant@emoldino.com")
            
            # Format selection also applies to the email attachment idea
            st.caption(f"Attachment: assigned_alerts.{file_extension}")
            
            if st.button("Send Now", type="primary", use_container_width=True):
                st.success(f"Report successfully sent to {email_input}!")

    with right_panel:
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "⏱️ Cycle Time", 
            "📈 Run Rate", 
            "⚠️ Capacity Risk", 
            "⚙️ Tooling End of Life", 
            "📡 Operation Status"
        ])

        # --- 1. CYCLE TIME ---
        with tab1:
            st.subheader("Cycle Time Alerts")
            st.write("Alerts based on deviation from approved cycle time (ACT).")
            
            ct_enabled = st.toggle("Enable Cycle Time Alerts", value=True, key="ct_toggle")
            
            if ct_enabled:
                with st.container(border=True):
                    st.markdown("##### 🎚️ Level & Threshold Definition")
                    st.write("Define variables X and Y to set the continuous ranges:")
                    
                    cx1, cx2 = st.columns(2)
                    with cx1:
                        x_ct = st.number_input("Value X (%)", value=5, min_value=0, key="ct_x")
                    with cx2:
                        y_ct = st.number_input("Value Y (%)", value=15, min_value=x_ct+1, key="ct_y")
                    
                    cl1, cl2 = st.columns(2)
                    with cl1:
                        st.markdown("**Level 1 Condition**")
                        st.markdown(f'<div class="formula-box">0% ≤ deviation ≤ {x_ct}%</div>', unsafe_allow_html=True)
                    with cl2:
                        st.markdown("**Level 2 Condition**")
                        st.markdown(f'<div class="formula-box">{x_ct}% &lt; deviation ≤ {y_ct}%</div>', unsafe_allow_html=True)
                    
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
                    st.markdown("##### 🎚️ Level & Threshold Definition")
                    rx1, rx2, rx3 = st.columns(3)
                    with rx1:
                        x_rr = st.number_input("Value X (%)", value=80, key="rr_x")
                    with rx2:
                        y_rr = st.number_input("Value Y (%)", value=100, key="rr_y")
                    with rx3:
                        z_rr = st.number_input("Value Z (%)", value=50, key="rr_z")
                    
                    rl1, rl2 = st.columns(2)
                    with rl1:
                        st.markdown("**Level 1 Condition**")
                        st.markdown(f'<div class="formula-box">{x_rr}% ≤ RR ≤ {y_rr}%</div>', unsafe_allow_html=True)
                    with rl2:
                        st.markdown("**Level 2 Condition**")
                        st.markdown(f'<div class="formula-box">{z_rr}% ≤ RR &lt; {x_rr}%</div>', unsafe_allow_html=True)

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
                    st.markdown("##### 🎚️ Target & Threshold Definition")
                    
                    # Dynamic input based on feedback constraint
                    if cr_condition == "Lost parts vs Target Capacity":
                        st.markdown("**Target Configuration**")
                        target_cap = st.number_input("Target Capacity Output (%)", value=90, min_value=1, max_value=100, help="Define the percentage to enable calculation of lost parts.")
                        st.info(f"Calculations will be evaluated against **{target_cap}%** capacity output.")
                        st.write("---")

                    cx1, cx2 = st.columns(2)
                    with cx1:
                        x_cr = st.number_input("Value X (%)", value=5, min_value=0, key="cr_x")
                    with cx2:
                        y_cr = st.number_input("Value Y (%)", value=15, min_value=x_cr+1, key="cr_y")
                    
                    cl1, cl2 = st.columns(2)
                    with cl1:
                        st.markdown("**Level 1 Condition**")
                        st.markdown(f'<div class="formula-box">0% ≤ loss ≤ {x_cr}%</div>', unsafe_allow_html=True)
                    with cl2:
                        st.markdown("**Level 2 Condition**")
                        st.markdown(f'<div class="formula-box">{x_cr}% &lt; loss ≤ {y_cr}%</div>', unsafe_allow_html=True)

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
                    st.markdown("##### 🎚️ Level & Threshold Definition")
                    ex1, ex2, ex3 = st.columns(3)
                    with ex1:
                        x_eol = st.number_input("Value X (%)", value=80, key="eol_x")
                    with ex2:
                        y_eol = st.number_input("Value Y (%)", value=90, key="eol_y")
                    with ex3:
                        z_eol = st.number_input("Value Z (%)", value=100, key="eol_z")
                    
                    el1, el2 = st.columns(2)
                    with el1:
                        st.markdown("**Level 1 Condition**")
                        st.markdown(f'<div class="formula-box">{x_eol}% ≤ accumulated shots ≤ {y_eol}% of max</div>', unsafe_allow_html=True)
                    with el2:
                        st.markdown("**Level 2 Condition**")
                        st.markdown(f'<div class="formula-box">{y_eol}% &lt; accumulated shots ≤ {z_eol}% of max</div>', unsafe_allow_html=True)

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
                    st.markdown("##### 🎚️ Status-Based Alerts")
                    c1, c2 = st.columns(2)
                    with c1:
                        st.multiselect("Trigger when tools remain in:", 
                                       ["Sensor offline", "Inactive", "Sensor detached"],
                                       default=["Sensor offline"])
                    with c2:
                        st.selectbox("Alert Frequency", ["Daily", "Weekly", "Monthly", "Real time"], index=3, key="os_freq")
                        
                    st.markdown("##### ⚡ Real-Time Event Alerts")
                    st.checkbox("🚨 Tooling starts producing (Tool in press starts producing)", value=True)
                    st.checkbox("🚨 Tooling goes out of the machine (Tool is removed from press)", value=True)
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
        
        st.markdown("##### 🎯 Step 1: Configure Target Scope (Filters)")
        st.caption("Select all filters or a subset for this alert.")
        admin_filters = render_filters("admin", layout="horizontal")
            
        st.divider()
        
        st.markdown("##### 🎚️ Step 2: Select Alert Type")
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

    st.markdown("### 📋 Programmed Alerts Log")
    st.caption("A track record of all alerts set up by eMoldino administrators.")
    
    if st.session_state.admin_log.empty:
        st.info("No alerts have been programmed yet in this session.")
    else:
        st.dataframe(st.session_state.admin_log, use_container_width=True, hide_index=True)