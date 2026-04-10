import streamlit as st
import pandas as pd

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Alert Management Center | Emoldino",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR: GLOBAL SETTINGS ---
with st.sidebar:
    st.image("https://via.placeholder.com/200x60?text=EMOLDINO", use_container_width=True)
    st.markdown("### Global Notification Settings")
    st.write("Select how you want to receive alerts globally:")
    
    in_system = st.checkbox("🔔 In-System Notifications", value=True)
    mobile_push = st.checkbox("📱 Mobile Push", value=True)
    email_notif = st.checkbox("✉️ Email", value=True)
    
    st.divider()
    st.markdown("### Account")
    st.write("👤 **User:** Admin")
    st.write("🏢 **Role:** Plant Manager")

# --- MAIN CONTENT ---
st.markdown('<div class="main-header">Alert Management Center</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Digitalize. Streamline. Transform. | Monitor manufacturing performance and tooling conditions.</div>', unsafe_allow_html=True)

# --- TABS FOR ALERT TYPES ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "⏱️ Cycle Time", 
    "📈 Run Rate", 
    "⚠️ Capacity Risk", 
    "⚙️ Tooling End of Life", 
    "📡 Operation Status"
])

# Helper function to generate dynamic levels
def render_levels(alert_name, default_levels=2, suffix="%"):
    num_levels = st.number_input(f"Number of Levels for {alert_name}", min_value=1, max_value=5, value=default_levels, step=1)
    
    cols = st.columns(num_levels)
    for i in range(num_levels):
        with cols[i]:
            st.markdown(f"**Level {i+1}**")
            min_val = st.number_input(f"Min {suffix}", key=f"{alert_name}_min_{i}", value=i*5)
            max_val = st.number_input(f"Max {suffix}", key=f"{alert_name}_max_{i}", value=(i+1)*5)
            st.caption(f"{min_val}{suffix} ≤ value {'<' if i < num_levels-1 else '≤'} {max_val}{suffix}")

# --- 1. CYCLE TIME ---
with tab1:
    st.subheader("Cycle Time Alerts")
    st.write("Alerts based on deviation from approved cycle time (ACT).")
    
    ct_enabled = st.toggle("Enable Cycle Time Alerts", value=True, key="ct_toggle")
    
    if ct_enabled:
        with st.container(border=True):
            render_levels("Cycle Time Deviation", 2, "%")
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
            render_levels(f"Run Rate ({rr_condition})", 2, "%")
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
            render_levels(f"Capacity Risk ({cr_condition})", 2, "% loss")
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
            render_levels("Accumulated Shots", 2, "% of Max")
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
        st.markdown("#### Status-Based Alerts")
        with st.container(border=True):
            c1, c2 = st.columns(2)
            with c1:
                st.multiselect("Trigger when tools remain in:", 
                               ["Sensor offline", "Inactive", "Sensor detached"],
                               default=["Sensor offline"])
            with c2:
                st.selectbox("Alert Frequency", ["Daily", "Weekly", "Monthly"], key="os_freq")
                
        st.markdown("#### Real-Time Event Alerts")
        with st.container(border=True):
            st.checkbox("🚨 Tooling starts producing (Tool in press starts producing)", value=True)
            st.checkbox("🚨 Tooling goes out of the machine (Tool is removed from press)", value=True)
            st.caption("*Real-time alerts are triggered immediately upon event detection.*")
            
        if st.button("Save Operation Status Settings", type="primary"):
            st.success("Operation Status alert settings saved successfully!")