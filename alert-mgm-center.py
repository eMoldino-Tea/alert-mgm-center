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
        "Timestamp", "Server", "User", "Alert Type", "Monitored Tools/Projects"
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

# --- REUSABLE SCOPE FUNCTION ---
def render_target_scope(key_prefix):
    st.markdown("##### 🎯 Target Scope Configuration")
    st.caption("Alerts will only trigger for the selected dimensions below. Leave empty to apply globally.")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.multiselect("OEM Business Division", ["Div A", "Div B", "Div C"], key=f"{key_prefix}_oem")
        st.multiselect("Supplier", ["Supplier X", "Supplier Y", "Supplier Z"], key=f"{key_prefix}_sup")
        st.multiselect("Plant", ["Plant 1", "Plant 2", "Plant 3"], key=f"{key_prefix}_plt")
    with c2:
        st.multiselect("Tooling Type", ["Injection", "Stamping", "Die Casting"], key=f"{key_prefix}_type")
        st.multiselect("Product", ["Product Alpha", "Product Beta"], key=f"{key_prefix}_prod")
        st.multiselect("Part", ["Part 101", "Part 102", "Part 103"], key=f"{key_prefix}_part")
    with c3:
        st.multiselect("Specific Tools", ["Tool_A", "Tool_B", "Tool_C", "Tool_D"], key=f"{key_prefix}_tool")
    st.divider()

# ==========================================
#              USER VIEW
# ==========================================
if app_mode == "User View":
    st.markdown('<div class="main-header">Alert Management Center</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Digitalize. Streamline. Transform. | Monitor manufacturing performance and tooling conditions.</div>', unsafe_allow_html=True)

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
                render_target_scope("ct")
                
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
                st.success("Cycle Time alert settings saved successfully!")

    # --- 2. RUN RATE ---
    with tab2:
        st.subheader("Run Rate Alerts")
        st.write("Alerts based on Run Rate Efficiency and Stability.")
        
        rr_enabled = st.toggle("Enable Run Rate Alerts", value=True, key="rr_toggle")
        
        if rr_enabled:
            rr_condition = st.radio("Trigger Condition", ["Low Run Rate Efficiency", "Low Run Rate Stability"], horizontal=True)
            
            with st.container(border=True):
                render_target_scope("rr")
                
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
                st.success("Run Rate alert settings saved successfully!")

    # --- 3. CAPACITY RISK ---
    with tab3:
        st.subheader("Capacity Risk Alerts")
        st.write("Alerts based on lost parts vs optimal or target capacity.")
        
        cr_enabled = st.toggle("Enable Capacity Risk Alerts", value=True, key="cr_toggle")
        
        if cr_enabled:
            cr_condition = st.radio("Trigger Condition", ["Lost parts vs Optimal Capacity", "Lost parts vs Target Capacity"], horizontal=True)
            
            with st.container(border=True):
                render_target_scope("cr")
                
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
                st.success("Capacity Risk alert settings saved successfully!")

    # --- 4. TOOLING END OF LIFE ---
    with tab4:
        st.subheader("Tooling End of Life Alerts")
        st.write("Alerts for tools approaching their forecasted maximum shot count.")
        
        eol_enabled = st.toggle("Enable Tooling End of Life Alerts", value=True, key="eol_toggle")
        
        if eol_enabled:
            with st.container(border=True):
                render_target_scope("eol")
                
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
                st.success("Tooling End of Life settings saved successfully!")

    # --- 5. OPERATION STATUS ---
    with tab5:
        st.subheader("Tooling Operation Status Alerts")
        st.write("Alerts for real-time status changes and offline sensors.")
        
        os_enabled = st.toggle("Enable Operation Status Alerts", value=True, key="os_toggle")
        
        if os_enabled:
            with st.container(border=True):
                render_target_scope("os")
                
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
                st.success("Operation Status alert settings saved successfully!")

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
        st.subheader("2. Alert Definition")
        col_type, col_tools = st.columns(2)
        
        with col_type:
            selected_alert = st.selectbox("Select Alert Type to Program", 
                                          ["Cycle Time", "Run Rate", "Capacity Risk", "Tooling End of Life", "Operation Status"])
        with col_tools:
            selected_tools = st.multiselect("Specific Tools / Projects to Monitor", 
                                            ["Tool_A_2024", "Tool_B_2024", "Project_Titan", "Project_Apollo"],
                                            default=["Tool_A_2024"])
            
        if st.button("Program Alert for User", type="primary"):
            if len(selected_tools) == 0:
                st.error("Please select at least one Tool or Project.")
            else:
                # Add to log
                new_log = pd.DataFrame([{
                    "Timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Server": selected_server,
                    "User": selected_user,
                    "Alert Type": selected_alert,
                    "Monitored Tools/Projects": ", ".join(selected_tools)
                }])
                st.session_state.admin_log = pd.concat([new_log, st.session_state.admin_log], ignore_index=True)
                st.success(f"Successfully programmed {selected_alert} alert for {selected_user}!")

    st.markdown("### 📋 Programmed Alerts Log")
    st.caption("A track record of all alerts set up by eMoldino administrators.")
    
    if st.session_state.admin_log.empty:
        st.info("No alerts have been programmed yet in this session.")
    else:
        st.dataframe(st.session_state.admin_log, use_container_width=True, hide_index=True)