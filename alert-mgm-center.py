import streamlit as st
import pandas as pd
import datetime
import os
import tempfile
import random
import io
import zipfile
import altair as alt
import matplotlib
matplotlib.use('Agg') # Enforce headless plotting for PDF generation

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

# --- GLOBAL MOCK DATA ---
MOCK_USERS = {
    "JLR Server": ["Alex Carter (alex.carter@jlr.com)", "Jane Smith (jane.smith@jlr.com)", "Mark Davis (m.davis@jlr.com)", "Rachel Green (rachel.g@jlr.com)", "Tom Hardy (tom.h@jlr.com)", "Oliver Twist (oliver.t@jlr.com)"],
    "GM Server": ["Mike Johnson (mjohnson@gm.com)", "Sarah Connor (sconnor@gm.com)", "Tom Wilson (twilson@gm.com)", "Nancy Drew (nancy.d@gm.com)", "Peter Parker (peter.p@gm.com)", "Bruce Banner (bruce.b@gm.com)"],
    "Paccar Server": ["David Lee (d.lee@paccar.com)", "Emma Wilson (e.wilson@paccar.com)", "Chris Taylor (ctaylor@paccar.com)", "Clark Kent (clark.k@paccar.com)", "Diana Prince (diana.p@paccar.com)", "Barry Allen (barry.a@paccar.com)"]
}

# --- SESSION STATE INITIALIZATION ---
# Re-init if Config ID is missing from a previous session load, or if outdated columns exist
if 'admin_log' not in st.session_state or "Config ID" not in st.session_state.admin_log.columns or "Configuration details" in st.session_state.admin_log.columns or "Config Payload" not in st.session_state.admin_log.columns:
    st.session_state.admin_log = pd.DataFrame(columns=[
        "Config ID", "Timestamp", "Server", "Users", "Alert Type", "Target Scope (Filters)", "Config Payload"
    ])

# Initialize robust mock client alerts to perfectly populate the 3-Tier chart visualizations
if 'client_alerts_db' not in st.session_state:
    mock_data = []
    distributions = [
        ("Cycle Time", [("Level 1", 45, "8%"), ("Level 2", 14, "12%"), ("Level 3", 5, "18%")]),
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
    .main-header { font-size: 2.5rem; font-weight: bold; color: #1E3A8A; margin-bottom: 2rem; }
    .sub-header { font-size: 1.2rem; color: #6B7280; margin-bottom: 2rem; }
    .level-box { padding: 15px; border-radius: 8px; margin-top: 10px; }
    .metric-card { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 20px; margin-bottom: 15px; }
    .metric-title { color: #64748B; font-size: 0.95rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 5px; }
    .metric-value { color: #0F172A; font-size: 1.8rem; font-weight: bold; }
    
    /* Action Command Center Cards */
    .action-card { background-color: white; border-top: 4px solid #EF4444; border-left: 1px solid #E2E8F0; border-right: 1px solid #E2E8F0; border-bottom: 1px solid #E2E8F0; border-radius: 8px; padding: 20px; margin-bottom: 5px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); transition: all 0.2s ease; cursor: pointer; }
    .action-card:hover { box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); transform: translateY(-2px); border-top-color: #D97706; }
    .action-card-warning { border-top: 4px solid #F59E0B; }
    .risk-score-badge { float: right; background-color: #FEE2E2; color: #991B1B; padding: 4px 10px; border-radius: 20px; font-weight: bold; font-size: 0.9rem; }
    .risk-score-warning { background-color: #FEF3C7; color: #92400E; }
    .card-tool { font-size: 1.3rem; font-weight: bold; color: #1E293B; margin-bottom: 5px;}
    .card-context { font-size: 0.95rem; color: #475569; margin-bottom: 0px; }
    
    /* Clean robust overlay logic */
    .act-now-card {
        height: 130px !important;
        margin-bottom: 0px !important;
    }
    .st-key-act_now_btn_0, .st-key-act_now_btn_1, .st-key-act_now_btn_2 {
        margin-top: -146px !important;
        position: relative !important;
        z-index: 999 !important;
    }
    .st-key-act_now_btn_0 button, .st-key-act_now_btn_1 button, .st-key-act_now_btn_2 button {
        height: 130px !important;
        width: 100% !important;
        background: transparent !important;
        border: 2px solid transparent !important;
        color: transparent !important;
        box-shadow: none !important;
        cursor: pointer !important;
        border-radius: 8px !important;
    }
    .st-key-act_now_btn_0 button:hover, .st-key-act_now_btn_1 button:hover, .st-key-act_now_btn_2 button:hover {
        border-color: #D97706 !important;
        background-color: rgba(217, 119, 6, 0.05) !important;
    }
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
    
    if row['Severity'] == "Level 3": score += 40
    elif row['Severity'] == "Level 2": score += 20
    elif row['Severity'] == "Level 1": score += 10
    elif row['Severity'] in ["Event", "Status"]: score += 15
    
    if "Capacity Risk" in row['Alert Type']: score += 30
    elif "Run Rate" in row['Alert Type']: score += 20
    elif "Cycle Time" in row['Alert Type']: score += 15
    elif "EOL" in row['Alert Type']: score += 10
    elif "Operation Status" in row['Alert Type']: score += 20
    
    days_old = (datetime.datetime(2026, 4, 28, 10, 0) - pd.to_datetime(row['Date/Time'])).days
    score += (days_old * 3)
    
    return min(int(score), 99) 

# --- EXECUTIVE PDF GENERATOR (ADMIN) ---
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

# --- CLIENT EXPORT ENGINE (ZIP & PDF) ---
def format_df_for_client_export(df_sub, a_type):
    """Maps the columns exactly to the UI tables, dropping Alert ID."""
    base_cols = {"Tool": "Tooling ID", "Part": "Part ID (Part Name)", "OEM Division": "OEM Business Division", "Supplier": "Supplier", "Plant": "Plant", "Tooling Type": "Tooling Type", "Severity": "Severity"}
    display_cols = base_cols.copy()
    
    type_df = df_sub.copy()
    if a_type == "Cycle Time":
        display_cols["Metric_1"] = "% of Deviation"
    elif a_type == "Low Run Rate - Shot Efficiency":
        display_cols["Metric_1"] = "Run Rate Shot Efficiency"
    elif a_type == "Low Run Rate - Time Stability":
        display_cols["Metric_1"] = "Run Rate Time Stability"
    elif "Capacity Risk" in a_type:
        display_cols["Metric_1"] = "% of Loss"
    elif "EOL" in a_type:
        display_cols["Metric_1"] = "Utilization Rate"
        if a_type in ["Tooling EOL (Remaining Days)", "Tooling EOL (Combination)"]:
            display_cols["Metric_2"] = "Remaining Life (Days)"
    elif "Operation Status" in a_type:
        if "Severity" in display_cols:
            del display_cols["Severity"]

    display_cols["Date/Time"] = "Date & Time"
    
    final_cols = {k: v for k, v in display_cols.items() if k in type_df.columns}
    out_df = type_df[list(final_cols.keys())].rename(columns=final_cols)
    
    if 'Alert ID' in out_df.columns:
        out_df = out_df.drop(columns=['Alert ID'])
        
    return out_df

def generate_client_csv_zip(df):
    """Generates a strictly structured ZIP archive categorized by Alert Type directories."""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        
        # 1. Cycle Time
        ct_df = df[df['Alert Type'] == 'Cycle Time']
        if not ct_df.empty: zip_file.writestr("Cycle Time/Cycle Time.csv", format_df_for_client_export(ct_df, 'Cycle Time').to_csv(index=False))
            
        # 2. Run Rate
        rr_eff = df[df['Alert Type'] == 'Low Run Rate - Shot Efficiency']
        if not rr_eff.empty: zip_file.writestr("Low Run Rate – Shot Efficiency/Low Run Rate – Shot Efficiency.csv", format_df_for_client_export(rr_eff, 'Low Run Rate - Shot Efficiency').to_csv(index=False))
        rr_stab = df[df['Alert Type'] == 'Low Run Rate - Time Stability']
        if not rr_stab.empty: zip_file.writestr("Low Run Rate – Time Stability/Low Run Rate – Time Stability.csv", format_df_for_client_export(rr_stab, 'Low Run Rate - Time Stability').to_csv(index=False))
            
        # 3. Capacity Risk
        cr_opt = df[df['Alert Type'] == 'Capacity Risk (Optimal)']
        if not cr_opt.empty: zip_file.writestr("Loss Parts vs Optimal Capacity/Loss Parts vs Optimal Capacity.csv", format_df_for_client_export(cr_opt, 'Capacity Risk (Optimal)').to_csv(index=False))
        cr_tgt = df[df['Alert Type'] == 'Capacity Risk (Target)']
        if not cr_tgt.empty: zip_file.writestr("Loss Parts vs Target Capacity/Loss Parts vs Target Capacity.csv", format_df_for_client_export(cr_tgt, 'Capacity Risk (Target)').to_csv(index=False))
        
        # 4. Tooling EOL
        eol_df = df[df['Alert Type'].str.contains('EOL')]
        if not eol_df.empty: zip_file.writestr("Tooling End of Life/Tooling End of Life.csv", format_df_for_client_export(eol_df, 'Tooling EOL (Combination)').to_csv(index=False))

        # 5. Operation Status
        os_producing = df[df['Alert Type'] == 'Operation Status (Tool Producing)']
        if not os_producing.empty: zip_file.writestr("Tool Starts Producing/Tool Starts Producing.csv", format_df_for_client_export(os_producing, 'Operation Status (Tool Producing)').to_csv(index=False))
        os_stops = df[df['Alert Type'] == 'Operation Status (Tool Stops)']
        if not os_stops.empty: zip_file.writestr("Tool Stops/Tool Stops.csv", format_df_for_client_export(os_stops, 'Operation Status (Tool Stops)').to_csv(index=False))
        os_inactive = df[df['Alert Type'] == 'Operation Status (Inactive)']
        if not os_inactive.empty: zip_file.writestr("Inactive Tool/Inactive Tool.csv", format_df_for_client_export(os_inactive, 'Operation Status (Inactive)').to_csv(index=False))
        os_offline = df[df['Alert Type'] == 'Operation Status (Sensor Offline)']
        if not os_offline.empty: zip_file.writestr("Sensor Offline Tool/Sensor Offline Tool.csv", format_df_for_client_export(os_offline, 'Operation Status (Sensor Offline)').to_csv(index=False))
        os_detached = df[df['Alert Type'] == 'Operation Status (Sensor Detached)']
        if not os_detached.empty: zip_file.writestr("Sensor Detached Tool/Sensor Detached Tool.csv", format_df_for_client_export(os_detached, 'Operation Status (Sensor Detached)').to_csv(index=False))

    return zip_buffer.getvalue()

def generate_client_dashboard_pdf(df):
    """Reconstructs the Overview Dashboard completely offline using FPDF and Matplotlib"""
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
            self.cell(150, 8, clean('eMoldino Alert Center | Executive Dashboard'), 0, 0, 'L')
            self.set_font('Arial', '', 10)
            self.cell(120, 8, clean(f'Generated: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}'), 0, 1, 'R')
            self.ln(10)
            
        def kpi_card(self, x, y, w, h, title, value):
            self.set_xy(x, y)
            self.set_fill_color(248, 250, 252)
            self.set_draw_color(203, 213, 225)
            self.rect(x, y, w, h, 'DF')
            self.set_xy(x, y + 4)
            self.set_font('Arial', 'B', 9)
            self.set_text_color(100, 116, 139)
            self.cell(w, 5, clean(title), 0, 1, 'C')
            self.set_xy(x, y + 12)
            self.set_font('Arial', 'B', 22)
            self.set_text_color(30, 58, 138)
            self.cell(w, 10, clean(value), 0, 1, 'C')

    pdf = PDF('L', 'mm', 'A4')
    pdf.add_page()
    
    # 1. KPI Cards
    pdf.kpi_card(15, 30, 60, 25, "TOTAL ACTIVE ALERTS", str(len(df)))
    pdf.kpi_card(82, 30, 60, 25, "IMPACTED TOOLS", str(df['Tool'].nunique()))
    pdf.kpi_card(149, 30, 60, 25, "IMPACTED PLANTS", str(df['Plant'].nunique()))
    pdf.kpi_card(216, 30, 60, 25, "IMPACTED SUPPLIERS", str(df['Supplier'].nunique()))

    # 2. Generate Matplotlib Charts Headlessly
    temp_files = []
    sev_colors = {'Level 1': '#FACC15', 'Level 2': '#F59E0B', 'Level 3': '#EF4444'}
    status_colors = {'Sensor Offline': '#F87171', 'Sensor Detached': '#FACC15', 'Inactive': '#94A3B8'}

    def save_matplot_bar(df_subset, title):
        fig, ax = plt.subplots(figsize=(4, 3))
        categories = ['Level 1', 'Level 2', 'Level 3']
        counts = df_subset['Severity'].value_counts() if not df_subset.empty else pd.Series(dtype=int)
        plot_data = [counts.get(cat, 0) for cat in categories]
        colors = [sev_colors.get(cat, '#3B82F6') for cat in categories]
        bars = ax.bar(categories, plot_data, color=colors, width=0.5)
        for bar in bars:
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, yval + 0.1, int(yval), ha='center', va='bottom', fontsize=8, fontweight='bold')
        ax.set_title(title, fontsize=10, fontweight='bold', color='#1E40AF', pad=10)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#CBD5E1')
        ax.spines['bottom'].set_color('#CBD5E1')
        plt.tight_layout()
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        plt.savefig(tmp.name, format='png', transparent=True, dpi=150)
        plt.close(fig)
        temp_files.append(tmp.name)
        return tmp.name

    def save_matplot_donut(df_subset, title, categories, color_map, is_status=False):
        fig, ax = plt.subplots(figsize=(4, 3))
        if is_status: counts = df_subset['Alert Type'].apply(lambda x: x.replace("Operation Status (", "").replace(")", "")).value_counts()
        else: counts = df_subset['Severity'].value_counts()
        data = pd.Series({cat: counts.get(cat, 0) for cat in categories})
        data = data[data > 0]
        if data.empty:
            ax.text(0.5, 0.5, 'No Alerts', ha='center', va='center')
            ax.axis('off')
        else:
            colors = [color_map.get(x, '#3B82F6') for x in data.index]
            ax.pie(data.values, labels=data.index, autopct='%1.0f%%', startangle=90, colors=colors, wedgeprops=dict(width=0.4, edgecolor='white', linewidth=1), textprops={'fontsize': 8})
        ax.set_title(title, fontsize=10, fontweight='bold', color='#1E40AF', pad=10)
        plt.tight_layout()
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        plt.savefig(tmp.name, format='png', transparent=True, dpi=150)
        plt.close(fig)
        temp_files.append(tmp.name)
        return tmp.name

    # Generate and Place Row 1
    t1 = save_matplot_bar(df[df['Alert Type'] == 'Cycle Time'], "Cycle Time Deviations")
    t2 = save_matplot_bar(df[df['Alert Type'] == 'Low Run Rate - Time Stability'], "Run Rate Time Stability")
    t3 = save_matplot_bar(df[df['Alert Type'] == 'Capacity Risk (Target)'], "Loss vs. Target Capacity")
    pdf.image(t1, x=15, y=65, w=80)
    pdf.image(t2, x=105, y=65, w=80)
    pdf.image(t3, x=195, y=65, w=80)

    # Generate and Place Row 2
    os_cats = ['Sensor Offline', 'Sensor Detached', 'Inactive']
    os_df = df[df['Alert Type'].apply(lambda x: any(cat in x for cat in os_cats))]
    t4 = save_matplot_donut(os_df, "Operation Status", os_cats, status_colors, True)
    t5 = save_matplot_bar(df[df['Alert Type'] == 'Low Run Rate - Shot Efficiency'], "Run Rate Shot Efficiency")
    t6 = save_matplot_bar(df[df['Alert Type'] == 'Capacity Risk (Optimal)'], "Loss vs. Optimal Capacity")
    pdf.image(t4, x=15, y=125, w=80)
    pdf.image(t5, x=105, y=125, w=80)
    pdf.image(t6, x=195, y=125, w=80)

    # Page 2 for EOL and Top Entities
    pdf.add_page()
    t7 = save_matplot_donut(df[df['Alert Type'].str.contains('EOL')], "Tooling End of Life", ['Level 1', 'Level 2', 'Level 3'], sev_colors)
    pdf.image(t7, x=15, y=30, w=80)

    # --- Add Top Impacted Entities ---
    pdf.set_xy(15, 110)
    pdf.set_font('Arial', 'B', 12)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(0, 10, clean("TOP IMPACTED ENTITIES"), 0, 1, 'L')
    pdf.ln(2)

    top_tools = df['Tool'].value_counts().head(5)
    top_plants = df['Plant'].value_counts().head(5)
    top_suppliers = df['Supplier'].value_counts().head(5)

    def draw_mini_table(x_start, title, data_series, col1_name):
        pdf.set_xy(x_start, 125)
        pdf.set_font('Arial', 'B', 10)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(80, 6, clean(title), 0, 1, 'L')
        
        pdf.set_xy(x_start, 132)
        pdf.set_font('Arial', 'B', 8)
        pdf.set_fill_color(241, 245, 249)
        pdf.set_text_color(71, 85, 105)
        pdf.cell(60, 6, clean(col1_name), 1, 0, 'L', 1)
        pdf.cell(20, 6, "Alerts", 1, 1, 'C', 1)

        pdf.set_font('Arial', '', 8)
        pdf.set_text_color(15, 23, 42)
        y_pos = 138
        for name, count in data_series.items():
            pdf.set_xy(x_start, y_pos)
            pdf.cell(60, 6, clean(str(name)[:30]), 1, 0, 'L')
            pdf.cell(20, 6, str(count), 1, 1, 'C')
            y_pos += 6

    draw_mini_table(15, "Top Impacted Tools", top_tools, "Tooling ID")
    draw_mini_table(105, "Top Impacted Plants", top_plants, "Plant Name")
    draw_mini_table(195, "Top Impacted Suppliers", top_suppliers, "Supplier Name")

    try:
        output = bytes(pdf.output())
    except TypeError:
        output = pdf.output(dest='S').encode('latin-1')

    for tmp_file in temp_files:
        try: os.remove(tmp_file)
        except OSError: pass

    return output

def generate_summary_pdf(df, freq):
    """Generates the simulated automated alert email PDF attachment with strict frequency filtering."""
    def clean(text):
        text = str(text).replace('≤', '<=').replace('≥', '>=')
        return text.encode('latin-1', 'replace').decode('latin-1')

    # Filter strictly by configured frequency
    df_filtered = df[df['Frequency'] == freq]
    server_name = "JLR"

    now = datetime.datetime.now()
    if freq == "Daily":
        date_str = now.strftime('%Y-%m-%d')
        header_title = f"Daily Alert Summary - {date_str}"
        reporting_period = f"{date_str}"
    elif freq == "Weekly":
        week_num = now.isocalendar()[1]
        year_num = now.year
        start_date = (now - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
        end_date = now.strftime('%Y-%m-%d')
        header_title = f"Weekly Alert Summary - Week {week_num}, {year_num}"
        reporting_period = f"Week {week_num}, {year_num} - from {start_date} to {end_date}"
    else: # Monthly
        month_name = now.strftime('%B')
        year_num = now.year
        start_date = (now - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
        end_date = now.strftime('%Y-%m-%d')
        header_title = f"Monthly Alert Summary - {month_name}, {year_num}"
        reporting_period = f"{month_name}, {year_num} - from {start_date} to {end_date}"

    class PDF(FPDF):
        def header(self):
            self.set_fill_color(30, 58, 138)
            self.rect(0, 0, 297, 20, 'F')
            self.set_y(6)
            self.set_font('Arial', 'B', 16)
            self.set_text_color(255, 255, 255)
            self.cell(10)
            self.cell(150, 8, clean(header_title), 0, 0, 'L')
            self.set_font('Arial', '', 10)
            self.cell(120, 8, clean(f'Generated: {now.strftime("%Y-%m-%d %H:%M")}'), 0, 1, 'R')
            self.ln(10)

    pdf = PDF('L', 'mm', 'A4')
    pdf.add_page()
    
    # Meta Header Info
    pdf.set_font('Arial', 'B', 11)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(0, 6, clean(f"Client: {server_name}"), 0, 1)
    pdf.set_font('Arial', '', 11)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 6, clean(f"Reporting Period: {reporting_period}"), 0, 1)
    pdf.cell(0, 6, clean(f"Total Number of Alerts: {len(df_filtered)}"), 0, 1)
    pdf.ln(5)

    groups = [
        ("Cycle Time", ["Cycle Time"]),
        ("Run Rate", ["Low Run Rate - Shot Efficiency", "Low Run Rate - Time Stability"]),
        ("Capacity Risk", ["Capacity Risk (Optimal)", "Capacity Risk (Target)"]),
        ("Tooling End of Life", ["Tooling EOL (Combination)", "Tooling EOL (Utilization)", "Tooling EOL (Remaining Days)"]),
        ("Operation Status", ["Operation Status (Tool Producing)", "Operation Status (Tool Stops)", "Operation Status (Inactive)", "Operation Status (Sensor Offline)", "Operation Status (Sensor Detached)"])
    ]

    for group_name, alert_types in groups:
        group_df = df_filtered[df_filtered['Alert Type'].isin(alert_types)]
        if group_df.empty: continue

        pdf.set_font('Arial', 'B', 12)
        pdf.set_fill_color(241, 245, 249)
        pdf.set_text_color(30, 58, 138)
        pdf.cell(0, 8, clean(group_name), 0, 1, 'L', 1)
        pdf.ln(2)

        for a_type in alert_types:
            type_df = group_df[group_df['Alert Type'] == a_type]
            if type_df.empty: continue

            formatted_df = format_df_for_client_export(type_df, a_type)
            
            if len(alert_types) > 1:
                pdf.set_font('Arial', 'B', 10)
                pdf.set_text_color(71, 85, 105)
                pdf.cell(0, 6, clean(a_type), 0, 1, 'L')
            
            pdf.set_font('Arial', 'B', 8)
            pdf.set_fill_color(30, 58, 138)
            pdf.set_text_color(255, 255, 255)
            cols = list(formatted_df.columns)
            
            # Smart Table Width Distribution for A4 Landscape (277mm usable width)
            col_w = []
            remaining_w = 277
            fixed_cols = {'Date & Time': 28, 'Severity': 15, 'Tooling ID': 22, 'Utilization Rate': 20, '% of Deviation': 20, '% of Loss': 20, 'Tooling Status': 22}
            
            for c in cols:
                if c in fixed_cols:
                    col_w.append(fixed_cols[c])
                    remaining_w -= fixed_cols[c]
                else:
                    col_w.append(0)
            
            dynamic_count = col_w.count(0)
            if dynamic_count > 0:
                dyn_width = max(15, remaining_w / dynamic_count)
                col_w = [dyn_width if w == 0 else w for w in col_w]

            for i, c in enumerate(cols):
                pdf.cell(col_w[i], 6, clean(c), 1, 0, 'C', 1)
            pdf.ln()

            pdf.set_font('Arial', '', 7)
            pdf.set_text_color(0, 0, 0)
            for _, row in formatted_df.iterrows():
                # Automatic page breaking before content gets cut off
                if pdf.get_y() > 180:
                    pdf.add_page()
                for i, c in enumerate(cols):
                    val = clean(str(row[c]))
                    if len(val) > 28: val = val[:25] + "..." # Truncate long strings neatly
                    pdf.cell(col_w[i], 6, val, 1, 0, 'C')
                pdf.ln()
            pdf.ln(4)

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

def log_admin_action(alert_type, filters, selected_server, selected_users, config_payload=None):
    if not selected_users:
        st.error("⚠️ Please select at least one user from the User Assignment panel before saving.")
        return
    active_filters = {k: v for k, v in filters.items() if v}
    filter_str = " | ".join([f"{k}: {', '.join(v)}" for k, v in active_filters.items()])
    if not filter_str:
        filter_str = "Global (No filters applied)"
    users_str = ", ".join(selected_users)
    
    config_id = f"CFG-{random.randint(10000, 99999)}"
    
    new_log = pd.DataFrame([{
        "Config ID": config_id,
        "Timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Server": selected_server,
        "Users": users_str,
        "Alert Type": alert_type,
        "Target Scope (Filters)": filter_str,
        "Config Payload": config_payload if config_payload else {}
    }])
    st.session_state.admin_log = pd.concat([new_log, st.session_state.admin_log], ignore_index=True)
    st.success(f"Successfully programmed '{alert_type}' alert for {len(selected_users)} user(s) on {selected_server}!")

def render_payload_details(alert_type, payload):
    if not payload:
        st.write("No detailed thresholds recorded for this configuration.")
        return
        
    st.write(f"**Frequency:** {payload.get('freq', 'N/A')}")
    
    if "Cycle Time" in alert_type:
        st.write(f"**No Alert Zone:** ≤ ±{payload.get('no_alert', 5)}%")
        st.write(f"**Levels Configured:** {payload.get('levels')}")
        limits = payload.get('limits', [])
        for i, limit in enumerate(limits):
            lower = payload.get('no_alert', 5) if i == 0 else limits[i-1]
            st.write(f"- **Level {i+1}:** ±{lower}% < deviation ≤ ±{limit}%")
    
    elif "Run Rate" in alert_type:
        st.write(f"**No Alert Zone:** ≥ {payload.get('no_alert')}%")
        st.write(f"**Levels Configured:** {payload.get('levels')}")
        
        metric_name = "rate"
        if "Shot Efficiency" in alert_type:
            metric_name = "efficiency"
        elif "Time Stability" in alert_type:
            metric_name = "stability"
            
        limits = payload.get('limits', [])
        for i, limit in enumerate(limits):
            upper = payload.get('no_alert') if i == 0 else limits[i-1]
            st.write(f"- **Level {i+1}:** {limit}% ≤ {metric_name} < {upper}%")
            
    elif "Capacity Risk" in alert_type:
        if "Target" in alert_type:
            st.write(f"**Target Capacity Output:** {payload.get('target_cap')}%")
        st.write(f"**Levels Configured:** {payload.get('levels')}")
        limits = payload.get('limits', [])
        for i, limit in enumerate(limits):
            lower = 0 if i == 0 else limits[i-1]
            st.write(f"- **Level {i+1}:** {lower}% < loss ≤ {limit}%")
            
    elif "Tooling End of Life" in alert_type:
        st.write(f"**Levels Configured:** {payload.get('levels')}")
        
        for i in range(payload.get('levels', 1)):
            if "Utilization Rate" in alert_type and "Combination" not in alert_type:
                u_lims = payload.get('util_limits', [])
                lower = payload.get('base') if i == 0 else u_lims[i-1]
                upper = u_lims[i] if i < len(u_lims) else 'MAX'
                st.write(f"- **Level {i+1}:** {lower}% < utilization rate ≤ {upper}%")
            elif "Remaining Days" in alert_type and "Combination" not in alert_type:
                d_lims = payload.get('days_limits', [])
                upper_d = 365 if i == 0 else d_lims[i-1]
                lower_d = d_lims[i] if i < len(d_lims) else 0
                st.write(f"- **Level {i+1}:** {lower_d} < remaining days ≤ {upper_d}")
            else: # Combination
                u_lims = payload.get('util_limits', [])
                lower = payload.get('base') if i == 0 else u_lims[i-1]
                upper = u_lims[i] if i < len(u_lims) else 'MAX'
                
                d_lims = payload.get('days_limits', [])
                upper_d = 365 if i == 0 else d_lims[i-1]
                lower_d = d_lims[i] if i < len(d_lims) else 0
                
                st.write(f"- **Level {i+1}:** Utilization Rate: {lower}% to {upper}% or Remaining Days: {lower_d} to {upper_d}")
            
    elif "Operation Status" in alert_type:
        st.write(f"**Tool Starts Producing Alert:** {'Enabled' if payload.get('producing') else 'Disabled'}")
        st.write(f"**Tool Stops Alert:** {'Enabled' if payload.get('stops') else 'Disabled'}")
        st.write(f"**Connectivity & Status-Based Alerts:** {', '.join(payload.get('triggers', []))}")


def edit_thresholds(alert_type, payload, config_id):
    new_payload = payload.copy()
    
    if "Cycle Time" in alert_type:
        st.markdown("##### 'No Alert' Zone")
        new_payload['no_alert'] = st.number_input("No Alert Zone (Deviation ±%)", min_value=0, max_value=100, value=payload.get('no_alert', 5), key=f"e_ct_na_{config_id}")
        st.info(f"Production is considered **Healthy** when absolute deviation is **≤ {new_payload['no_alert']}%**.")
        st.divider()

        st.markdown("##### Configuration: Number of Levels")
        new_payload['levels'] = st.number_input("How many alert levels do you want to configure?", min_value=1, max_value=5, value=payload.get('levels', 2), key=f"e_ct_lvl_{config_id}")
        st.markdown("##### Deviation Threshold Boundaries")
        st.write("Set the deviation limits for each level.")
        cols = st.columns(new_payload['levels'])
        new_limits = []
        prev_val = new_payload['no_alert']
        for i in range(new_payload['levels']):
            with cols[i]:
                def_val = payload.get('limits', [])[i] if i < len(payload.get('limits', [])) else prev_val + 5
                c_min = min(200, prev_val + 1)
                def_val = max(def_val, c_min)
                val = st.number_input(f"Level {i+1} Limit (±%)", min_value=c_min, max_value=200, value=def_val, key=f"e_ct_lim_{config_id}_{i}")
                new_limits.append(val)
                prev_val = val
        new_payload['limits'] = new_limits

        st.markdown("##### Alert Conditions Summary")
        ct_disp_cols = st.columns(new_payload['levels'])
        for i in range(new_payload['levels']):
            with ct_disp_cols[i]:
                lower = new_payload['no_alert'] if i == 0 else new_payload['limits'][i-1]
                upper = new_payload['limits'][i]
                txt = f"**Level {i+1}**\n\nTriggers when absolute deviation is between **{lower}% and {upper}%**.\n\n`(±{lower}% < deviation ≤ ±{upper}%)`"
                display_level_box(i, txt)
        st.divider()
        new_payload['freq'] = st.selectbox("Alert Frequency", ["Hourly", "Daily", "Weekly", "Monthly"], index=["Hourly", "Daily", "Weekly", "Monthly"].index(payload.get('freq', 'Daily')), key=f"e_ct_fq_{config_id}")
    
    elif "Run Rate" in alert_type:
        rr_type = "Shot Efficiency" if "Shot Efficiency" in alert_type else "Time Stability"
        st.markdown("##### 'No Alert' Zone")
        new_payload['no_alert'] = st.number_input("No Alert Zone (Above %)", min_value=1, max_value=100, value=payload.get('no_alert', 85), key=f"e_rr_na_{config_id}")
        st.info(f"Production is considered **Healthy** when {rr_type.lower()} is **≥ {new_payload['no_alert']}%**.")
        st.divider()

        st.markdown("##### Configuration: Number of Levels")
        new_payload['levels'] = st.number_input("How many alert levels do you want to configure?", min_value=1, max_value=5, value=payload.get('levels', 2), key=f"e_rr_lvl_{config_id}")
        st.markdown("##### Threshold Boundaries")
        cols = st.columns(new_payload['levels'])
        new_limits = []
        prev_val = new_payload['no_alert']
        for i in range(new_payload['levels']):
            with cols[i]:
                def_val = payload.get('limits', [])[i] if i < len(payload.get('limits', [])) else max(0, prev_val - 15)
                c_max = max(0, prev_val - 1)
                def_val = min(def_val, c_max)
                val = st.number_input(f"Level {i+1} Limit (%)", min_value=0, max_value=c_max, value=def_val, key=f"e_rr_lim_{config_id}_{i}")
                new_limits.append(val)
                prev_val = val
        new_payload['limits'] = new_limits

        st.markdown("##### Alert Conditions Summary")
        rr_disp_cols = st.columns(new_payload['levels'])
        for i in range(new_payload['levels']):
            with rr_disp_cols[i]:
                upper = new_payload['no_alert'] if i == 0 else new_payload['limits'][i-1]
                lower = new_payload['limits'][i]
                op = "≤" if i == 0 else "<"
                txt = f"**Level {i+1}**\n\nTriggers when rate drops between **{lower}% and {upper}%**.\n\n`{lower}% ≤ rate {op} {upper}%`"
                display_level_box(i, txt)
        st.divider()
        new_payload['freq'] = st.selectbox("Alert Frequency", ["Daily", "Weekly", "Monthly"], index=["Daily", "Weekly", "Monthly"].index(payload.get('freq', 'Daily')), key=f"e_rr_fq_{config_id}")
        
    elif "Capacity Risk" in alert_type:
        if "Target" in alert_type:
            new_payload['target_cap'] = st.number_input("Target Capacity Output (%)", min_value=1, max_value=100, value=payload.get('target_cap', 90), key=f"e_cr_tgt_{config_id}")
            st.info(f"Calculations will be evaluated against **{new_payload['target_cap']}%** capacity output.")
            st.divider()

        st.markdown("##### Configuration: Number of Levels")
        new_payload['levels'] = st.number_input("How many alert levels do you want to configure?", min_value=1, max_value=5, value=payload.get('levels', 2), key=f"e_cr_lvl_{config_id}")
        st.markdown("##### Threshold Boundaries")
        cols = st.columns(new_payload['levels'])
        new_limits = []
        prev_val = 0
        for i in range(new_payload['levels']):
            with cols[i]:
                def_val = payload.get('limits', [])[i] if i < len(payload.get('limits', [])) else prev_val + 10
                c_min = min(100, prev_val + 1)
                def_val = max(def_val, c_min)
                val = st.number_input(f"Level {i+1} Limit (%)", min_value=c_min, max_value=100, value=def_val, key=f"e_cr_lim_{config_id}_{i}")
                new_limits.append(val)
                prev_val = val
        new_payload['limits'] = new_limits

        st.markdown("##### Alert Conditions Summary")
        cr_disp_cols = st.columns(new_payload['levels'])
        for i in range(new_payload['levels']):
            with cr_disp_cols[i]:
                lower = 0 if i == 0 else new_payload['limits'][i-1]
                upper = new_payload['limits'][i]
                op = "≤" if i == 0 else "<"
                txt = f"**Level {i+1}**\n\nTriggers when capacity loss is between **{lower}% and {upper}%**.\n\n`{lower}% {op} loss ≤ {upper}%`"
                display_level_box(i, txt)
        st.divider()
        new_payload['freq'] = st.selectbox("Alert Frequency", ["Daily", "Weekly", "Monthly"], index=["Daily", "Weekly", "Monthly"].index(payload.get('freq', 'Daily')), key=f"e_cr_fq_{config_id}")
        
    elif "Tooling End of Life" in alert_type:
        new_payload['mode'] = st.radio("Choose how End of Life alerts should be evaluated:", ["Utilization Rate (%)", "Remaining Days", "Combination (Whichever comes first)"], index=["Utilization Rate (%)", "Remaining Days", "Combination (Whichever comes first)"].index(payload.get('mode', "Utilization Rate (%)")), horizontal=True, key=f"e_eol_mod_{config_id}")
        st.divider()

        new_payload['levels'] = st.number_input("How many alert levels do you want to configure?", min_value=1, max_value=5, value=payload.get('levels', 2), key=f"e_eol_lvl_{config_id}")
        st.markdown("##### Threshold Boundaries")
        
        show_util = "Utilization" in new_payload['mode'] or "Combination" in new_payload['mode']
        show_days = "Days" in new_payload['mode'] or "Combination" in new_payload['mode']
        
        new_util_limits, new_days_limits = [], []
        if show_util:
            new_payload['base'] = st.number_input("Start Monitoring At (% of forecasted max shot)", min_value=0, max_value=99, value=payload.get('base', 80), key=f"e_eol_base_{config_id}")
            cols = st.columns(new_payload['levels'])
            prev_val = new_payload['base']
            for i in range(new_payload['levels']):
                with cols[i]:
                    def_val = payload.get('util_limits', [])[i] if i < len(payload.get('util_limits', [])) else prev_val + 10
                    c_min = min(200, prev_val + 1)
                    def_val = max(def_val, c_min)
                    val = st.number_input(f"Level {i+1} Upper Limit (%)", min_value=c_min, max_value=200, value=def_val, key=f"e_eol_ulim_{config_id}_{i}")
                    new_util_limits.append(val)
                    prev_val = val
            new_payload['util_limits'] = new_util_limits
            st.write("")
            
        if show_days:
            cols = st.columns(new_payload['levels'])
            prev_val = 365
            for i in range(new_payload['levels']):
                with cols[i]:
                    def_val = payload.get('days_limits', [])[i] if i < len(payload.get('days_limits', [])) else max(0, prev_val - 15)
                    c_max = max(0, prev_val - 1)
                    def_val = min(def_val, c_max)
                    val = st.number_input(f"Level {i+1} Remaining Days Limit", min_value=0, max_value=c_max, value=def_val, key=f"e_eol_dlim_{config_id}_{i}")
                    new_days_limits.append(val)
                    prev_val = val
            new_payload['days_limits'] = new_days_limits

        st.markdown("##### Alert Conditions Summary")
        eol_disp_cols = st.columns(new_payload['levels'])
        for i in range(new_payload['levels']):
            with eol_disp_cols[i]:
                conds = []
                if show_util:
                    lower = new_payload['base'] if i == 0 else new_payload['util_limits'][i-1]
                    upper = new_payload['util_limits'][i]
                    op = "≤" if i == 0 else "<"
                    conds.append(f"Shots are between **{lower}% and {upper}%** of max shot.\n\n`{lower}% {op} shots ≤ {upper}%`")
                if show_days:
                    upper_d = 365 if i == 0 else new_payload['days_limits'][i-1]
                    lower_d = new_payload['days_limits'][i]
                    conds.append(f"Remaining days fall between **{upper_d} and {lower_d} days**.")
                txt = f"**Level {i+1}**\n\nTriggers when:\n\n" + "\n\n**OR**\n\n".join(conds)
                display_level_box(i, txt)
        st.divider()
        new_payload['freq'] = st.selectbox("Alert Frequency", ["Daily", "Weekly", "Monthly"], index=["Daily", "Weekly", "Monthly"].index(payload.get('freq', 'Daily')), key=f"e_eol_fq_{config_id}")

    elif "Operation Status" in alert_type:
        st.markdown("##### Real-Time Event Alerts")
        new_payload['producing'] = st.checkbox("Tool Starts Producing", value=payload.get('producing', True), key=f"e_os_p_{config_id}")
        st.write("")
        new_payload['stops'] = st.checkbox("Tool Stops", value=payload.get('stops', False), key=f"e_os_s_{config_id}")
        st.divider()
        st.markdown("##### Connectivity & Status-Based Alerts")
        c1, c2 = st.columns(2)
        with c1:
            new_payload['triggers'] = st.multiselect("Trigger when tools remain in:", ["Sensor offline", "Inactive", "Sensor detached"], default=payload.get('triggers', ["Sensor offline"]), key=f"e_os_t_{config_id}")
        with c2:
            new_payload['freq'] = st.selectbox("Alert Frequency", ["Daily", "Weekly", "Monthly", "Real time"], index=["Daily", "Weekly", "Monthly", "Real time"].index(payload.get('freq', 'Real time')), key=f"e_os_f_{config_id}")

    return new_payload

# --- EDIT AND DELETE DIALOGS (GLOBAL DASHBOARD) ---
@st.dialog("Edit Configuration", width="large")
def edit_config_popup(config_id, row_data):
    st.write(f"Editing settings for **{config_id}**")
    
    st.markdown("### User Assignment")
    new_server = st.selectbox("Target Server", list(MOCK_USERS.keys()), index=list(MOCK_USERS.keys()).index(row_data['Server']))
    
    # Parse existing users into a list for the multiselect default
    existing_users_list = [u.strip() for u in str(row_data['Users']).split(",") if u.strip()]
    available_users = MOCK_USERS.get(new_server, [])
    
    # Ensure defaults are valid for the currently selected server to avoid Streamlit errors
    valid_defaults = [u for u in existing_users_list if u in available_users]
    
    new_users_list = st.multiselect("Select User(s)", options=available_users, default=valid_defaults, help="Search and select users")
    new_users = ", ".join(new_users_list)
    
    st.divider()
    
    new_payload = edit_thresholds(row_data['Alert Type'], row_data.get('Config Payload', {}), config_id)
    
    st.divider()
    if st.button("Save Changes", type="primary", use_container_width=True):
        if not new_users_list:
            st.error("⚠️ Please assign at least one user.")
        else:
            idx = st.session_state.admin_log.index[st.session_state.admin_log['Config ID'] == config_id].tolist()[0]
            st.session_state.admin_log.at[idx, 'Server'] = new_server
            st.session_state.admin_log.at[idx, 'Users'] = new_users
            st.session_state.admin_log.at[idx, 'Config Payload'] = new_payload
            st.session_state.admin_log.at[idx, 'Timestamp'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " (Edited)"
            st.rerun()

@st.dialog("Delete Configuration")
def delete_config_popup(config_id):
    st.warning(f"Are you sure you want to permanently delete **{config_id}**?")
    st.write("This action will immediately remove the alert configuration for all assigned users.")
    
    c1, c2 = st.columns(2)
    if c1.button("Cancel", use_container_width=True):
        st.rerun()
    if c2.button("Confirm Delete", type="primary", use_container_width=True):
        st.session_state.admin_log = st.session_state.admin_log[st.session_state.admin_log['Config ID'] != config_id]
        st.rerun()

# ==========================================
#         SIDEBAR: NAVIGATION & FILTERS
# ==========================================
with st.sidebar:
    st.markdown("### Navigation")
    page = st.radio("Go to:", ["Configuration Setup", "Configuration Management", "Client Alerts Portal"])
    st.divider()

    if page == "Configuration Setup":
        st.markdown("### User Assignment")
        selected_server = st.selectbox("Target Server", list(MOCK_USERS.keys()))
        
        selected_users = st.multiselect(
            "Select User(s)", 
            options=MOCK_USERS[selected_server], 
            default=[MOCK_USERS[selected_server][0]],
            help="Search and select users"
        )
        st.divider()
        st.markdown("### Target Data Filters")
        user_filters = render_filters("admin_filters")

    elif page == "Client Alerts Portal":
        st.markdown("### Target Data Filters")
        client_filters = render_filters("client_filters")

# ==========================================
#              MAIN CONTENT
# ==========================================

if page == "Configuration Setup":
    # Top Header & Export Button
    header_col, export_col = st.columns([5, 1])

    with header_col:
        st.markdown('<div class="main-header">Alert Configuration Setup</div>', unsafe_allow_html=True)
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
                st.markdown("##### 'No Alert' Zone")
                ct_no_alert = st.number_input("No Alert Zone (Deviation ±%)", min_value=0, max_value=100, value=5, key="ct_no_alert")
                st.info(f"Production is considered **Healthy** when absolute deviation is **≤ {ct_no_alert}%**.")
                st.divider()

                st.markdown("##### Configuration: Number of Levels")
                ct_num = st.number_input("How many alert levels do you want to configure?", min_value=1, max_value=5, value=2, key="ct_num_levels")
                st.markdown("##### Deviation Threshold Boundaries")
                st.write("Set the deviation limits for each level.")
                ct_limits = []
                prev_val = ct_no_alert
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
                        lower = ct_no_alert if i == 0 else ct_limits[i-1]
                        upper = ct_limits[i]
                        txt = f"**Level {i+1}**\n\nTriggers when absolute deviation is between **{lower}% and {upper}%**.\n\n`(±{lower}% < deviation ≤ ±{upper}%)`"
                        display_level_box(i, txt)
                st.divider()
                ct_freq = st.selectbox("Alert Frequency", ["Hourly", "Daily", "Weekly", "Monthly"], key="ct_freq")
            if st.button("Save Cycle Time Settings", type="primary"):
                log_admin_action("Cycle Time", user_filters, selected_server, selected_users, {"no_alert": ct_no_alert, "levels": ct_num, "limits": ct_limits, "freq": ct_freq})

    # --- 2. RUN Rate ---
    with tab2:
        st.subheader("Run Rate Alerts")
        st.write("Alerts based on Run Rate Shot Efficiency and Run Rate Time Stability")
        rr_enabled = st.toggle("Enable Run Rate Alerts", value=True, key="rr_toggle")
        if rr_enabled:
            rr_tab1, rr_tab2 = st.tabs(["Run Rate Shot Efficiency", "Run Rate Time Stability"])
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
                    log_admin_action(f"Run Rate - Low Run Rate {rr_type}", user_filters, selected_server, selected_users, {"no_alert": no_alert_zone, "levels": rr_num, "limits": rr_limits, "freq": rr_freq})

            with rr_tab1: render_run_rate_logic("Shot Efficiency", "eff")
            with rr_tab2: render_run_rate_logic("Time Stability", "stab")

    # --- 3. CAPACITY RISK ---
    with tab3:
        st.subheader("Capacity Risk Alerts")
        cr_enabled = st.toggle("Enable Capacity Risk Alerts", value=True, key="cr_toggle")
        if cr_enabled:
            cr_tab1, cr_tab2 = st.tabs(["Loss Parts vs Optimal Capacity", "Loss Parts vs Target Capacity"])
            def render_capacity_logic(cr_type, prefix, is_target=False):
                with st.container(border=True):
                    target_cap = 100
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
                    payload = {"levels": cr_num, "limits": cr_limits, "freq": cr_freq}
                    if is_target: payload["target_cap"] = target_cap
                    log_admin_action(f"Capacity Risk - Loss Parts vs {cr_type} Capacity", user_filters, selected_server, selected_users, payload)

            with cr_tab1: render_capacity_logic("Optimal", "opt")
            with cr_tab2: render_capacity_logic("Target", "tgt", is_target=True)

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
                base_start = None
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
                clean_eol_mode = eol_mode.replace(" (%)", "")
                log_admin_action(f"Tooling End of Life - {clean_eol_mode}", user_filters, selected_server, selected_users, {"mode": eol_mode, "levels": eol_num, "util_limits": util_limits, "days_limits": days_limits, "base": base_start, "freq": eol_freq})

    # --- 5. OPERATION STATUS ---
    with tab5:
        st.subheader("Operational Status Alerts")
        os_enabled = st.toggle("Enable Operation Status Alerts", value=True, key="os_toggle")
        if os_enabled:
            with st.container(border=True):
                st.markdown("##### Real-Time Event Alerts")
                os_producing = st.checkbox("Tool Starts Producing", value=True)
                st.write("")
                os_stops = st.checkbox("Tool Stops", value=False)
                st.divider()
                st.markdown("##### Connectivity & Status-Based Alerts")
                c1, c2 = st.columns(2)
                with c1:
                    os_triggers = st.multiselect("Trigger when tools remain in:", ["Sensor offline", "Inactive", "Sensor detached"], default=["Sensor offline"])
                with c2:
                    os_freq = st.selectbox("Alert Frequency", ["Daily", "Weekly", "Monthly", "Real time"], index=3, key="os_freq")
            if st.button("Save Operation Status Settings", type="primary"):
                log_admin_action("Operation Status", user_filters, selected_server, selected_users, {"producing": os_producing, "stops": os_stops, "triggers": os_triggers, "freq": os_freq})

# ==========================================
#        GLOBAL CONFIGURATIONS DASHBOARD
# ==========================================
elif page == "Configuration Management":
    st.markdown('<div class="main-header">Configuration Management</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">A comprehensive view of all active alert configurations across all servers and user groups.</div>', unsafe_allow_html=True)
    
    st.markdown("### Automated Alert Summary (Simulation)")
    st.write("Generate a simulated PDF attachment for automated digest emails sent to clients.")
    
    sim_col1, sim_col2 = st.columns([3, 7])
    with sim_col1:
        sim_freq = st.selectbox("Email Frequency", ["Daily", "Weekly", "Monthly"], key="sim_freq")
        
    with sim_col2:
        st.write("") 
        st.write("")
        if FPDF_AVAILABLE:
            pdf_bytes = generate_summary_pdf(st.session_state.client_alerts_db, sim_freq)
            
            now = datetime.datetime.now()
            if sim_freq == "Daily":
                export_filename = f"eMoldino Daily Alert Summary - {now.strftime('%Y%m%d')}.pdf"
            elif sim_freq == "Weekly":
                export_filename = f"eMoldino Weekly Alert Summary - Week {now.isocalendar()[1]}, {now.year}.pdf"
            else:
                export_filename = f"eMoldino Monthly Alert Summary - {now.strftime('%B')}, {now.year}.pdf"
                
            st.download_button(
                label=f"Generate & Download {sim_freq} Alert Summary PDF", 
                data=pdf_bytes, 
                file_name=export_filename, 
                mime="application/pdf", 
                type="primary",
                use_container_width=True
            )
        else:
            st.error("FPDF library missing.")
    
    st.divider()

    if st.session_state.admin_log.empty:
        st.info("No configurations have been applied yet in this session.")
    else:
        display_df = st.session_state.admin_log.copy()
        
        def simplify_alert_type(t):
            if "Cycle Time" in t: return "Cycle Time"
            if "Run Rate" in t: return "Run Rate"
            if "Capacity Risk" in t: return "Capacity Risk"
            if "End of Life" in t or "EOL" in t: return "Tooling End of Life"
            if "Operation Status" in t: return "Operation Status"
            return t
            
        def summarize_users(u):
            ulist = [x.strip() for x in str(u).split(",") if x.strip()]
            if len(ulist) > 1: return f"{ulist[0]} (+{len(ulist)-1} more)"
            return u
            
        def summarize_filters(f):
            if f == "Global (No filters applied)": return f
            flist = [x.strip() for x in str(f).split("|") if x.strip()]
            if len(flist) > 1: return f"{flist[0]} (+{len(flist)-1} more)"
            if len(str(f)) > 50: return str(f)[:47] + "..."
            return f
        
        display_df['Display Alert Type'] = display_df['Alert Type'].apply(simplify_alert_type)
        
        st.markdown("##### Active Configurations")
        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            server_filter = st.multiselect("Filter by Server", options=display_df['Server'].unique(), default=[])
        with f_col2:
            alert_filter = st.multiselect("Filter by Alert Type", options=display_df['Display Alert Type'].unique(), default=[])
        st.divider()
        
        if server_filter: display_df = display_df[display_df['Server'].isin(server_filter)]
        if alert_filter: display_df = display_df[display_df['Display Alert Type'].isin(alert_filter)]
        
        st.write("**Click on any row in the table below to view, edit, or delete its configuration.**")
        
        # Prepare the visual table rendering
        table_display = display_df.copy()
        table_display['Alert Type'] = table_display['Display Alert Type']
        table_display['Users'] = table_display['Users'].apply(summarize_users)
        table_display['Target Scope (Filters)'] = table_display['Target Scope (Filters)'].apply(summarize_filters)
        table_display = table_display.drop(columns=['Config Payload', 'Display Alert Type'])
        table_display = table_display[['Config ID', 'Timestamp', 'Server', 'Users', 'Alert Type', 'Target Scope (Filters)']]
        
        try:
            event = st.dataframe(
                table_display, 
                use_container_width=True, 
                hide_index=True, 
                on_select="rerun", 
                selection_mode="single-row"
            )
            selected_rows = event.selection.rows
        except Exception:
            # Fallback for Streamlit versions < 1.35
            st.dataframe(table_display, use_container_width=True, hide_index=True)
            st.markdown("### Select a Configuration")
            selected_config_id = st.selectbox(
                "Select a configuration to View, Edit, or Delete:", 
                display_df['Config ID'].tolist(),
                format_func=lambda x: f"{x} | {display_df[display_df['Config ID'] == x]['Alert Type'].values[0]}"
            )
            selected_rows = [display_df.reset_index().index[display_df['Config ID'] == selected_config_id].tolist()[0]] if selected_config_id else []

        if selected_rows:
            sel_row = display_df.iloc[selected_rows[0]]
            selected_config_id = sel_row['Config ID']
            
            with st.container(border=True):
                st.markdown(f"#### Configuration Details: `{selected_config_id}`")
                
                # --- Basic Details Section ---
                col1, col2 = st.columns(2)
                col1.write(f"**Alert Type:** {sel_row['Alert Type']}")
                col1.write(f"**Server:** {sel_row['Server']}")
                col1.write(f"**Assigned Users:** {sel_row['Users']}")
                col2.write(f"**Target Scope (Filters):** {sel_row['Target Scope (Filters)']}")
                col2.write(f"**Last Updated:** {sel_row['Timestamp']}")
                
                st.divider()
                
                # --- Advanced Threshold View Section ---
                st.markdown("##### Alert Thresholds & Logic")
                render_payload_details(sel_row['Alert Type'], sel_row.get('Config Payload', {}))
                
                st.divider()
                bc1, bc2, bc3 = st.columns([1, 1, 4])
                
                if bc1.button("Edit", key=f"edit_{selected_config_id}", use_container_width=True):
                    edit_config_popup(selected_config_id, sel_row)
                    
                if bc2.button("Delete", key=f"del_{selected_config_id}", use_container_width=True):
                    delete_config_popup(selected_config_id)

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
        st.markdown('<div class="main-header">Alert Center</div>', unsafe_allow_html=True)
        
        df = st.session_state.client_alerts_db.copy()
        
        # Calculate dynamic risk score for workflow sorting
        df['Risk Score'] = df.apply(calculate_risk_index, axis=1)
        df = df.sort_values(by='Risk Score', ascending=False)
        
        if client_filters.get("OEM"): df = df[df['OEM Division'].isin(client_filters["OEM"])]
        if client_filters.get("Supplier"): df = df[df['Supplier'].isin(client_filters["Supplier"])]
        if client_filters.get("Plant"): df = df[df['Plant'].isin(client_filters["Plant"])]
        if client_filters.get("Tooling Type"): df = df[df['Tooling Type'].isin(client_filters["Tooling Type"])]
        if client_filters.get("Part"): df = df[df['Part'].isin(client_filters["Part"])]
        if client_filters.get("Tooling"): df = df[df['Tool'].isin(client_filters["Tooling"])]
        
        search_query = st.text_input("Search (Tooling ID, Part ID, Part Name)")
        if search_query:
            df = df[df.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)]

        st.write("")
        
        def render_tab_export_button(tab_id, df_subset, filename_prefix):
            with st.popover("Export Tab Data", use_container_width=True):
                st.caption(f"Export {len(df_subset)} filtered alerts.")
                zip_file_bytes = generate_client_csv_zip(df_subset)
                st.download_button(
                    label="Download CSV Zip",
                    data=zip_file_bytes,
                    file_name=f"{filename_prefix}_export_{datetime.datetime.now().strftime('%Y%m%d')}.zip",
                    mime="application/zip",
                    use_container_width=True,
                    key=f"client_csv_dl_{tab_id}"
                )
                st.divider()
                st.write("Send to Email")
                email_input = st.text_input("Email Address", value="user@client.com", key=f"client_email_in_{tab_id}", label_visibility="collapsed")
                if st.button("Send Now", type="primary", use_container_width=True, key=f"client_email_btn_{tab_id}"):
                    st.success(f"Sent successfully to {email_input}!")

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
                st.markdown(f"#### {sev}")
                sev_df = filtered_df[filtered_df['Severity'] == sev]
                
                for a_type in sorted(sev_df['Alert Type'].unique()):
                    type_df = sev_df[sev_df['Alert Type'] == a_type].copy()
                    display_cols = base_cols.copy()
                    
                    if a_type == "Cycle Time": 
                        display_cols["Metric_1"] = "% of Deviation"
                    elif a_type == "Low Run Rate - Shot Efficiency": 
                        display_cols["Metric_1"] = "Run Rate Shot Efficiency"
                    elif a_type == "Low Run Rate - Time Stability": 
                        display_cols["Metric_1"] = "Run Rate Time Stability"
                    elif "Capacity Risk" in a_type: 
                        display_cols["Metric_1"] = "% of Loss"
                    elif "EOL" in a_type: 
                        display_cols["Metric_1"] = "Utilization Rate"
                        if a_type in ["Tooling EOL (Remaining Days)", "Tooling EOL (Combination)"]:
                            display_cols["Metric_2"] = "Remaining Life (Days)"
                    elif "Operation Status" in a_type:
                        if "Severity" in display_cols:
                            del display_cols["Severity"]
                    else:
                        status_val = a_type.replace("Operation Status (", "").replace(")", "")
                        type_df["Tooling Status"] = status_val
                        display_cols["Tooling Status"] = "Tooling Status"
                    
                    display_cols["Date/Time"] = "Date & Time"
                    
                    final_cols = {k: v for k, v in display_cols.items() if k in type_df.columns}
                    out_df = type_df[list(final_cols.keys())].rename(columns=final_cols)
                    if len(sev_df['Alert Type'].unique()) > 1: st.markdown(f"##### {a_type}")
                    st.dataframe(out_df, use_container_width=True, hide_index=True)
                st.write("")

    # Helper Maps
    sev_colors = {'Level 1': '#FACC15', 'Level 2': '#F59E0B', 'Level 3': '#EF4444', 'Event': '#8B5CF6', 'Status': '#64748B'}
    status_colors = {'Sensor Offline': '#F87171', 'Sensor Detached': '#FACC15', 'Inactive': '#94A3B8'}

    # ---------------------------------------------------------
    # INTERACTIVE POPUP DIALOGS
    # ---------------------------------------------------------
    def show_alert_detail(row):
        st.markdown(f"#### Alert Detail: `{row['Alert ID']}`")
        st.divider()
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### Tooling Information")
            st.write(f"**Tooling ID:** {row['Tool']}")
            st.write(f"**OEM Business Division:** {row['OEM Division']}")
            st.write(f"**Supplier:** {row['Supplier']}")
            st.write(f"**Plant:** {row['Plant']}")
            st.write(f"**Part ID (Part Name):** {row['Part']}")
            st.write(f"**Tooling Type:** {row['Tooling Type']}")

        with c2:
            st.markdown("##### Alert Information")
            
            raw_type = row['Alert Type']
            display_type = raw_type
            if raw_type == "Low Run Rate - Shot Efficiency":
                display_type = "Run Rate - Low Run Rate Shot Efficiency"
            elif raw_type == "Low Run Rate - Time Stability":
                display_type = "Run Rate - Low Run Rate Time Stability"
            elif raw_type == "Capacity Risk (Optimal)":
                display_type = "Capacity Risk - Loss Parts vs Optimal Capacity"
            elif raw_type == "Capacity Risk (Target)":
                display_type = "Capacity Risk - Loss Parts vs Target Capacity"
            elif raw_type == "Tooling EOL (Utilization)":
                display_type = "Tooling End of Life - Utilization Rate"
            elif raw_type == "Tooling EOL (Remaining Days)":
                display_type = "Tooling End of Life - Remaining Days"
            elif raw_type == "Tooling EOL (Combination)":
                display_type = "Tooling End of Life - Combination (Whichever Comes First)"
            elif "Operation Status" in raw_type:
                display_type = "Operation Status"
                
            st.write(f"**Alert Name:** {display_type}")
            if "Operation Status" not in raw_type:
                st.write(f"**Severity:** {row['Severity']}")
            
            # Dynamic Value
            if "Cycle Time" in display_type:
                st.write(f"**% of Deviation:** {row['Metric_1']}")
            elif "Shot Efficiency" in display_type:
                st.write(f"**Run Rate Shot Efficiency:** {row['Metric_1']}")
            elif "Time Stability" in display_type:
                st.write(f"**Run Rate Time Stability:** {row['Metric_1']}")
            elif "Capacity Risk" in display_type:
                st.write(f"**% of Loss:** {row['Metric_1']}")
            elif "Utilization Rate" in display_type and "Combination" not in display_type:
                st.write(f"**Utilization Rate:** {row['Metric_1']}")
            elif "Remaining Days" in display_type and "Combination" not in display_type:
                st.write(f"**Remaining Days:** {row['Metric_1']}")
            elif "Combination" in display_type:
                st.write(f"**Utilization Rate:** {row['Metric_1']}")
                val_2 = row['Metric_2'] if pd.notna(row['Metric_2']) and str(row['Metric_2']).strip() else 'N/A'
                st.write(f"**Remaining Days:** {val_2}")
            elif "Operation Status" in raw_type:
                status_event = raw_type.replace("Operation Status (", "").replace(")", "")
                st.write(f"**{status_event}:** {row['Date/Time']}")
                
            st.write(f"**Date/Time:** {row['Date/Time']}")
            st.write(f"**Frequency:** {row['Frequency']}")

    @st.dialog("High Risk Alerts", width="large")
    def act_now_popup(tool_name, tool_alerts_df):
        st.markdown(f"### {tool_name}")
        st.write("**Click on an alert below to view its detailed information.**")
        sorted_df = tool_alerts_df.sort_values(by='Risk Score', ascending=False)
        disp = sorted_df[['Alert ID', 'Alert Type', 'Severity', 'Frequency', 'Date/Time']].rename(columns={'Severity': 'Level'})
        
        try:
            event = st.dataframe(disp, hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row")
            if event.selection.rows:
                selected_row = sorted_df.iloc[event.selection.rows[0]]
                st.divider()
                show_alert_detail(selected_row)
        except Exception:
            st.dataframe(disp, hide_index=True, use_container_width=True)
            selected_alert_id = st.selectbox("Select Alert ID to view details:", sorted_df['Alert ID'].tolist())
            if selected_alert_id:
                selected_row = sorted_df[sorted_df['Alert ID'] == selected_alert_id].iloc[0]
                st.divider()
                show_alert_detail(selected_row)

    @st.dialog("Alert Details", width="large")
    def category_popup(a_type_label, level, level_df):
        st.markdown(f"### {a_type_label} - {level}")
        if level_df.empty:
            st.info("No alerts found for this selection.")
            return
            
        st.write("**Click on an alert below to view its detailed information.**")
        level_df = level_df.copy()
        level_df['Exact calculation/value'] = level_df.apply(format_trigger_value, axis=1)
        
        display_cols = {
            "Alert ID": "Alert ID",
            "Tool": "Tooling ID", "Part": "Part ID (Part Name)", 
            "OEM Division": "OEM Business Division", "Supplier": "Supplier", 
            "Plant": "Plant", "Tooling Type": "Tooling Type"
        }
        
        if a_type_label == "Cycle Time Deviations":
            display_cols["Metric_1"] = "% of Deviation"
        elif a_type_label == "Low Run Rate Shot Efficiency":
            display_cols["Metric_1"] = "Run Rate Shot Efficiency"
        elif a_type_label == "Low Run Rate Time Stability":
            display_cols["Metric_1"] = "Run Rate Time Stability"
        elif a_type_label in ["Loss vs. Optimal Capacity", "Loss vs. Target Capacity"]:
            display_cols["Metric_1"] = "% of Loss"
        elif a_type_label == "Tooling End of Life":
            display_cols["Metric_1"] = "Utilization Rate"

        display_cols["Date/Time"] = "Date & Time" 

        sorted_df = level_df.sort_values(by='Risk Score', ascending=False)
        out_df = sorted_df[list(display_cols.keys())].rename(columns=display_cols)
        
        try:
            event = st.dataframe(out_df, hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row")
            if event.selection.rows:
                selected_row = sorted_df.iloc[event.selection.rows[0]]
                st.divider()
                show_alert_detail(selected_row)
        except Exception:
            st.dataframe(out_df, hide_index=True, use_container_width=True)
            selected_alert_id = st.selectbox("Select Alert ID to view details:", sorted_df['Alert ID'].tolist())
            if selected_alert_id:
                selected_row = sorted_df[sorted_df['Alert ID'] == selected_alert_id].iloc[0]
                st.divider()
                show_alert_detail(selected_row)

    @st.dialog("Impacted Tools", width="large")
    def impacted_tools_dialog(subset, prefix):
        st.write("Select a Tool to view associated alerts.")
        counts = subset['Tool'].value_counts().reset_index()
        counts.columns = ['Tool', 'Alert Count']
        
        try:
            event = st.dataframe(counts, hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row", key=f"itd_{prefix}")
            if event.selection.rows:
                selected_item = counts.iloc[event.selection.rows[0]]['Tool']
                st.divider()
                st.markdown(f"#### Alerts for {selected_item}")
                item_alerts = subset[subset['Tool'] == selected_item]
                sorted_df = item_alerts.sort_values('Risk Score', ascending=False)
                disp = sorted_df[['Alert ID', 'Alert Type', 'Severity', 'Frequency', 'Date/Time']].rename(columns={'Severity': 'Level'})
                
                event2 = st.dataframe(disp, hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row", key=f"itd2_{prefix}_{selected_item}")
                if event2.selection.rows:
                    selected_row = sorted_df.iloc[event2.selection.rows[0]]
                    st.divider()
                    show_alert_detail(selected_row)
        except Exception:
            st.dataframe(counts, hide_index=True, use_container_width=True)
            sel_item = st.selectbox("Select Tool to view details:", counts['Tool'].tolist(), key=f"sel_t_{prefix}")
            if sel_item:
                st.divider()
                st.markdown(f"#### Alerts for {sel_item}")
                item_alerts = subset[subset['Tool'] == sel_item]
                sorted_df = item_alerts.sort_values('Risk Score', ascending=False)
                disp = sorted_df[['Alert ID', 'Alert Type', 'Severity', 'Frequency', 'Date/Time']].rename(columns={'Severity': 'Level'})
                st.dataframe(disp, hide_index=True, use_container_width=True)
                sel_alert = st.selectbox("Select Alert ID to view details:", sorted_df['Alert ID'].tolist(), key=f"sel_ta_{prefix}_{sel_item}")
                if sel_alert:
                    selected_row = sorted_df[sorted_df['Alert ID'] == sel_alert].iloc[0]
                    st.divider()
                    show_alert_detail(selected_row)

    @st.dialog("Impacted Plants", width="large")
    def impacted_plants_dialog(subset, prefix):
        st.write("Select a Plant to view associated alerts.")
        counts = subset['Plant'].value_counts().reset_index()
        counts.columns = ['Plant', 'Alert Count']
        
        try:
            event = st.dataframe(counts, hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row", key=f"ipd_{prefix}")
            if event.selection.rows:
                selected_item = counts.iloc[event.selection.rows[0]]['Plant']
                st.divider()
                st.markdown(f"#### Alerts for {selected_item}")
                item_alerts = subset[subset['Plant'] == selected_item]
                sorted_df = item_alerts.sort_values('Risk Score', ascending=False)
                disp = sorted_df[['Alert ID', 'Alert Type', 'Severity', 'Frequency', 'Date/Time']].rename(columns={'Severity': 'Level'})
                
                event2 = st.dataframe(disp, hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row", key=f"ipd2_{prefix}_{selected_item}")
                if event2.selection.rows:
                    selected_row = sorted_df.iloc[event2.selection.rows[0]]
                    st.divider()
                    show_alert_detail(selected_row)
        except Exception:
            st.dataframe(counts, hide_index=True, use_container_width=True)
            sel_item = st.selectbox("Select Plant to view details:", counts['Plant'].tolist(), key=f"sel_p_{prefix}")
            if sel_item:
                st.divider()
                st.markdown(f"#### Alerts for {sel_item}")
                item_alerts = subset[subset['Plant'] == sel_item]
                sorted_df = item_alerts.sort_values('Risk Score', ascending=False)
                disp = sorted_df[['Alert ID', 'Alert Type', 'Severity', 'Frequency', 'Date/Time']].rename(columns={'Severity': 'Level'})
                st.dataframe(disp, hide_index=True, use_container_width=True)
                sel_alert = st.selectbox("Select Alert ID to view details:", sorted_df['Alert ID'].tolist(), key=f"sel_pa_{prefix}_{sel_item}")
                if sel_alert:
                    selected_row = sorted_df[sorted_df['Alert ID'] == sel_alert].iloc[0]
                    st.divider()
                    show_alert_detail(selected_row)

    @st.dialog("Impacted Suppliers", width="large")
    def impacted_suppliers_dialog(subset, prefix):
        st.write("Select a Supplier to view associated alerts.")
        counts = subset['Supplier'].value_counts().reset_index()
        counts.columns = ['Supplier', 'Alert Count']
        
        try:
            event = st.dataframe(counts, hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row", key=f"isd_{prefix}")
            if event.selection.rows:
                selected_item = counts.iloc[event.selection.rows[0]]['Supplier']
                st.divider()
                st.markdown(f"#### Alerts for {selected_item}")
                item_alerts = subset[subset['Supplier'] == selected_item]
                sorted_df = item_alerts.sort_values('Risk Score', ascending=False)
                disp = sorted_df[['Alert ID', 'Alert Type', 'Severity', 'Frequency', 'Date/Time']].rename(columns={'Severity': 'Level'})
                
                event2 = st.dataframe(disp, hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row", key=f"isd2_{prefix}_{selected_item}")
                if event2.selection.rows:
                    selected_row = sorted_df.iloc[event2.selection.rows[0]]
                    st.divider()
                    show_alert_detail(selected_row)
        except Exception:
            st.dataframe(counts, hide_index=True, use_container_width=True)
            sel_item = st.selectbox("Select Supplier to view details:", counts['Supplier'].tolist(), key=f"sel_s_{prefix}")
            if sel_item:
                st.divider()
                st.markdown(f"#### Alerts for {sel_item}")
                item_alerts = subset[subset['Supplier'] == sel_item]
                sorted_df = item_alerts.sort_values('Risk Score', ascending=False)
                disp = sorted_df[['Alert ID', 'Alert Type', 'Severity', 'Frequency', 'Date/Time']].rename(columns={'Severity': 'Level'})
                st.dataframe(disp, hide_index=True, use_container_width=True)
                sel_alert = st.selectbox("Select Alert ID to view details:", sorted_df['Alert ID'].tolist(), key=f"sel_sa_{prefix}_{sel_item}")
                if sel_alert:
                    selected_row = sorted_df[sorted_df['Alert ID'] == sel_alert].iloc[0]
                    st.divider()
                    show_alert_detail(selected_row)

    @st.dialog("Top Tool Details", width="large")
    def top_tool_popup(tool_id, subset):
        supplier = subset['Supplier'].iloc[0] if not subset.empty else "N/A"
        plant = subset['Plant'].iloc[0] if not subset.empty else "N/A"
        st.markdown(f"### {tool_id}")
        st.markdown(f"**Supplier:** {supplier} | **Plant:** {plant}")
        st.write("**Click on an alert below to view its detailed information.**")
        
        sorted_df = subset.sort_values('Risk Score', ascending=False)
        disp = sorted_df[['Alert ID', 'Alert Type', 'Severity', 'Frequency', 'Date/Time']].rename(columns={'Severity': 'Level'})
        
        try:
            event = st.dataframe(disp, hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row")
            if event.selection.rows:
                selected_row = sorted_df.iloc[event.selection.rows[0]]
                st.divider()
                show_alert_detail(selected_row)
        except Exception:
            st.dataframe(disp, hide_index=True, use_container_width=True)
            selected_alert_id = st.selectbox("Select Alert ID to view details:", sorted_df['Alert ID'].tolist())
            if selected_alert_id:
                selected_row = sorted_df[sorted_df['Alert ID'] == selected_alert_id].iloc[0]
                st.divider()
                show_alert_detail(selected_row)

    @st.dialog("Top Plant Details", width="large")
    def top_plant_popup(plant, subset):
        supplier = subset['Supplier'].iloc[0] if not subset.empty else "N/A"
        st.markdown(f"### {plant}")
        st.markdown(f"**Supplier:** {supplier}")
        st.write("**Click on an alert below to view its detailed information.**")
        
        sorted_df = subset.sort_values('Risk Score', ascending=False)
        disp = sorted_df[['Alert ID', 'Tool', 'Alert Type', 'Severity', 'Frequency', 'Date/Time']].rename(columns={'Tool':'Tooling ID', 'Severity': 'Level'})
        
        try:
            event = st.dataframe(disp, hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row")
            if event.selection.rows:
                selected_row = sorted_df.iloc[event.selection.rows[0]]
                st.divider()
                show_alert_detail(selected_row)
        except Exception:
            st.dataframe(disp, hide_index=True, use_container_width=True)
            selected_alert_id = st.selectbox("Select Alert ID to view details:", sorted_df['Alert ID'].tolist())
            if selected_alert_id:
                selected_row = sorted_df[sorted_df['Alert ID'] == selected_alert_id].iloc[0]
                st.divider()
                show_alert_detail(selected_row)

    @st.dialog("Top Supplier Details", width="large")
    def top_supplier_popup(supplier, subset):
        plants = ", ".join(subset['Plant'].unique())
        st.markdown(f"### {supplier}")
        st.markdown(f"**Plant(s):** {plants}")
        st.write("**Click on an alert below to view its detailed information.**")
        
        sorted_df = subset.sort_values('Risk Score', ascending=False)
        disp = sorted_df[['Alert ID', 'Tool', 'Plant', 'Alert Type', 'Severity', 'Frequency', 'Date/Time']].rename(columns={'Tool':'Tooling ID', 'Severity': 'Level'})
        
        try:
            event = st.dataframe(disp, hide_index=True, use_container_width=True, on_select="rerun", selection_mode="single-row")
            if event.selection.rows:
                selected_row = sorted_df.iloc[event.selection.rows[0]]
                st.divider()
                show_alert_detail(selected_row)
        except Exception:
            st.dataframe(disp, hide_index=True, use_container_width=True)
            selected_alert_id = st.selectbox("Select Alert ID to view details:", sorted_df['Alert ID'].tolist())
            if selected_alert_id:
                selected_row = sorted_df[sorted_df['Alert ID'] == selected_alert_id].iloc[0]
                st.divider()
                show_alert_detail(selected_row)

    # ---------------------------------------------------------
    # FALLBACK BUTTONS FOR OLDER STREAMLIT VERSIONS
    # ---------------------------------------------------------
    def render_breakdown_actions(label, df_subset, levels, is_status=False):
        btn_cols = st.columns(len(levels))
        for i, lvl in enumerate(levels):
            if btn_cols[i].button(f"View {lvl}", key=f"btn_{label}_{lvl}", use_container_width=True):
                if is_status:
                    lvl_df = df_subset[df_subset['Alert Type'].str.contains(lvl)]
                else:
                    lvl_df = df_subset[df_subset['Severity'] == lvl]
                category_popup(label, lvl, lvl_df)

    def render_interactive_bar(df_subset, label):
        categories = ['Level 1', 'Level 2', 'Level 3']
        counts = df_subset['Severity'].value_counts() if not df_subset.empty else pd.Series(dtype=int)
        data = pd.DataFrame({
            'Level': categories,
            'Count': [counts.get(cat, 0) for cat in categories],
            'Color': [sev_colors.get(cat, '#3B82F6') for cat in categories]
        })
        
        chart = alt.Chart(data).mark_bar().encode(
            x=alt.X('Level:N', sort=categories, axis=alt.Axis(labelAngle=0, title=None)),
            y=alt.Y('Count:Q', title='Tool Count'),
            color=alt.Color('Color:N', scale=None, legend=None),
            tooltip=['Level', 'Count']
        ).properties(height=250)
        
        safe_label = label.replace(" ", "_").lower()
        st.altair_chart(chart, use_container_width=True, key=f"bar_{safe_label}")
        render_breakdown_actions(label, df_subset, categories)

    def render_interactive_donut(df_subset, label, categories, color_map, is_status=False):
        if is_status:
            counts = df_subset['Alert Type'].apply(lambda x: x.replace("Operation Status (", "").replace(")", "")).value_counts()
        else:
            counts = df_subset['Severity'].value_counts()

        data = pd.DataFrame({
            'Category': categories,
            'Count': [counts.get(cat, 0) for cat in categories]
        })
        data = data[data['Count'] > 0]
        if data.empty:
            st.info("No Active Alerts")
            return

        domain = categories
        range_colors = [color_map.get(cat, '#3B82F6') for cat in categories]
        
        chart = alt.Chart(data).mark_arc(innerRadius=50).encode(
            theta=alt.Theta(field="Count", type="quantitative"),
            color=alt.Color(field="Category", type="nominal", scale=alt.Scale(domain=domain, range=range_colors), legend=alt.Legend(title=None)),
            tooltip=['Category', 'Count']
        ).properties(height=250)

        safe_label = label.replace(" ", "_").lower()
        st.altair_chart(chart, use_container_width=True, key=f"donut_{safe_label}")
        render_breakdown_actions(label, df_subset, categories, is_status=is_status)

    def render_tab_summary(tab_df, tab_name_prefix):
        st.markdown("### Category Summary")
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        with kpi1:
            st.markdown(f"<div class='metric-card'><div class='metric-title'>Total Active Alerts</div><div class='metric-value'>{len(tab_df)}</div></div>", unsafe_allow_html=True)
        with kpi2:
            st.markdown(f"<div class='metric-card' style='margin-bottom: 5px;'><div class='metric-title'>Impacted Tools</div><div class='metric-value'>{tab_df['Tool'].nunique()}</div></div>", unsafe_allow_html=True)
            if st.button("View Tools", key=f"btn_tools_{tab_name_prefix}", use_container_width=True):
                impacted_tools_dialog(tab_df, tab_name_prefix)
        with kpi3:
            st.markdown(f"<div class='metric-card' style='margin-bottom: 5px;'><div class='metric-title'>Impacted Plants</div><div class='metric-value'>{tab_df['Plant'].nunique()}</div></div>", unsafe_allow_html=True)
            if st.button("View Plants", key=f"btn_plants_{tab_name_prefix}", use_container_width=True):
                impacted_plants_dialog(tab_df, tab_name_prefix)
        with kpi4:
            st.markdown(f"<div class='metric-card' style='margin-bottom: 5px;'><div class='metric-title'>Impacted Suppliers</div><div class='metric-value'>{tab_df['Supplier'].nunique()}</div></div>", unsafe_allow_html=True)
            if st.button("View Suppliers", key=f"btn_suppliers_{tab_name_prefix}", use_container_width=True):
                impacted_suppliers_dialog(tab_df, tab_name_prefix)

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
        
        c1, c2 = st.columns([8, 2])
        with c2:
            with st.popover("Export Dashboard", use_container_width=True):
                st.caption("Export Executive Dashboard PDF.")
                if FPDF_AVAILABLE and MATPLOTLIB_AVAILABLE:
                    pdf_data = generate_client_dashboard_pdf(df)
                    st.download_button(
                        label="Download PDF Dashboard",
                        data=pdf_data,
                        file_name=f"alert_center_dashboard_{datetime.datetime.now().strftime('%Y%m%d')}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key="client_pdf_dl_ov"
                    )
                else:
                    st.warning("FPDF or Matplotlib missing.")
                st.divider()
                st.write("Send to Email")
                email_input = st.text_input("Email Address", value="user@client.com", key="client_email_in_ov", label_visibility="collapsed")
                if st.button("Send Now", type="primary", use_container_width=True, key="client_email_btn_ov"):
                    st.success(f"Sent successfully to {email_input}!")

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.markdown(f"<div class='metric-card'><div class='metric-title'>Total Active Alerts</div><div class='metric-value'>{len(df)}</div></div>", unsafe_allow_html=True)
        kpi2.markdown(f"<div class='metric-card'><div class='metric-title'>Impacted Tools</div><div class='metric-value'>{df['Tool'].nunique()}</div></div>", unsafe_allow_html=True)
        kpi3.markdown(f"<div class='metric-card'><div class='metric-title'>Impacted Plants</div><div class='metric-value'>{df['Plant'].nunique()}</div></div>", unsafe_allow_html=True)
        kpi4.markdown(f"<div class='metric-card'><div class='metric-title'>Impacted Suppliers</div><div class='metric-value'>{df['Supplier'].nunique()}</div></div>", unsafe_allow_html=True)

        st.divider()

        st.markdown("### Act Now: Critical Priorities")
        st.write("Tools with the highest number of Level 2 and above (high risk) alerts.")
        
        high_risk_df = df[df['Severity'].isin(['Level 2', 'Level 3'])]
        if high_risk_df.empty:
            st.success("No high-risk alerts currently active.")
        else:
            top_tools = high_risk_df.groupby(['Tool']).size().reset_index(name='Alert Count')
            top_tools = top_tools.sort_values(by='Alert Count', ascending=False).head(3)
            
            cols = st.columns(3)
            for idx, (_, tool_data) in enumerate(top_tools.iterrows()):
                tool_name = tool_data['Tool']
                tool_alerts = high_risk_df[high_risk_df['Tool'] == tool_name]
                plant_name = tool_alerts['Plant'].iloc[0] if not tool_alerts.empty else "N/A"
                supplier_name = tool_alerts['Supplier'].iloc[0] if not tool_alerts.empty else "N/A"
                
                with cols[idx]:
                    
                    st.markdown(f"""
                    <div class="action-card action-card-warning act-now-card">
                        <div class="risk-score-badge risk-score-warning">High Risk Alerts: {len(tool_alerts)}</div>
                        <div class="card-tool">{tool_name}</div>
                        <div class="card-context">Plant: {plant_name} <br/> Supplier: {supplier_name}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(" ", key=f"act_now_btn_{idx}", help="Click to view high risk alerts", use_container_width=True):
                        act_now_popup(tool_name, tool_alerts)
        
        st.divider()

        st.markdown("### Alert Distribution Breakdowns")
        st.write("Detailed threshold analysis across the 6 major alert logic categories.")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### Cycle Time Deviations")
            ct_df = df[df['Alert Type'] == 'Cycle Time']
            render_interactive_bar(ct_df, "Cycle Time Deviations")
            with st.expander("Definitions & Thresholds"):
                st.markdown("- **Level 1:** ±5% < deviation ≤ ±10%\n- **Level 2:** ±10% < deviation ≤ ±15%\n- **Level 3:** ±15% < deviation ≤ ±20%")
            
            st.markdown("##### Low Run Rate Time Stability")
            rr_stab_df = df[df['Alert Type'] == 'Low Run Rate - Time Stability']
            render_interactive_bar(rr_stab_df, "Low Run Rate Time Stability")
            with st.expander("Definitions & Thresholds"):
                st.markdown("- **Level 1:** 75% ≤ stability < 85%\n- **Level 2:** 60% ≤ stability < 75%\n- **Level 3:** 0% ≤ stability < 60%")

            st.markdown("##### Loss vs. Target Capacity")
            cr_tgt_df = df[df['Alert Type'] == 'Capacity Risk (Target)']
            render_interactive_bar(cr_tgt_df, "Loss vs. Target Capacity")
            with st.expander("Definitions & Thresholds"):
                st.markdown("- **Level 1:** 0% < loss ≤ 5%\n- **Level 2:** 5% < loss ≤ 10%\n- **Level 3:** 10% < loss ≤ 100%")

            st.markdown("##### Operation Status")
            os_target_cats = ['Sensor Offline', 'Sensor Detached', 'Inactive']
            os_df = df[df['Alert Type'].apply(lambda x: any(cat in x for cat in os_target_cats))]
            os_counts = os_df['Alert Type'].apply(lambda x: x.replace("Operation Status (", "").replace(")", "")).value_counts()
            os_aligned = pd.Series({cat: os_counts.get(cat, 0) for cat in os_target_cats})
            os_aligned = os_aligned[os_aligned > 0] 
            if MATPLOTLIB_AVAILABLE: render_interactive_donut(os_df, "Operation Status", os_target_cats, status_colors, is_status=True)
            with st.expander("Definitions & Categories"):
                st.markdown("- **Sensor Offline:** Sensor heartbeat lost.\n- **Sensor Detached:** Physical detachment detected.\n- **Inactive:** Tool idle beyond threshold.")

        with c2:
            st.markdown("##### Low Run Rate Shot Efficiency")
            rr_eff_df = df[df['Alert Type'] == 'Low Run Rate - Shot Efficiency']
            render_interactive_bar(rr_eff_df, "Low Run Rate Shot Efficiency")
            with st.expander("Definitions & Thresholds"):
                st.markdown("- **Level 1:** 75% ≤ efficiency < 85%\n- **Level 2:** 60% ≤ efficiency < 75%\n- **Level 3:** 0% ≤ efficiency < 60%")

            st.markdown("##### Loss vs. Optimal Capacity")
            cr_opt_df = df[df['Alert Type'] == 'Capacity Risk (Optimal)']
            render_interactive_bar(cr_opt_df, "Loss vs. Optimal Capacity")
            with st.expander("Definitions & Thresholds"):
                st.markdown("- **Level 1:** 0% < loss ≤ 5%\n- **Level 2:** 5% < loss ≤ 10%\n- **Level 3:** 10% < loss ≤ 100%")

            st.markdown("##### Tooling End of Life")
            eol_df = df[df['Alert Type'].str.contains('EOL')]
            categories = ['Level 1', 'Level 2', 'Level 3']
            if MATPLOTLIB_AVAILABLE: render_interactive_donut(eol_df, "Tooling End of Life", categories, sev_colors)
            with st.expander("Definitions & Thresholds"):
                st.markdown("- **Level 1:** Utilization Rate: 70% to 80% or Remaining Days: 30 to 45\n- **Level 2:** Utilization Rate: 80% to 90% or Remaining Days: 10 to 30\n- **Level 3:** Utilization Rate: 90% to MAX or Remaining Days: 0 to 10")

        st.divider()

        # --- 4. Top Impacted Entities ---
        st.markdown("### Top Impacted Entities")
        t1, t2, t3 = st.columns(3)
        with t1:
            st.markdown("**Top Impacted Tools**")
            top_tools = df['Tool'].value_counts().head(5).reset_index()
            top_tools.columns = ['Tool', 'Alerts']
            c1, c2 = st.columns([3, 1])
            c1.caption("Tooling ID")
            c2.caption("Alerts")
            for _, row in top_tools.iterrows():
                c1, c2 = st.columns([3, 1])
                c1.write(row['Tool'])
                if c2.button(str(row['Alerts']), key=f"btn_top_tool_{row['Tool']}", use_container_width=True):
                    top_tool_popup(row['Tool'], df[df['Tool'] == row['Tool']])
        with t2:
            st.markdown("**Top Impacted Plants**")
            top_plants = df['Plant'].value_counts().head(5).reset_index()
            top_plants.columns = ['Plant', 'Alerts']
            c1, c2 = st.columns([3, 1])
            c1.caption("Plant Name")
            c2.caption("Alerts")
            for _, row in top_plants.iterrows():
                c1, c2 = st.columns([3, 1])
                c1.write(row['Plant'])
                if c2.button(str(row['Alerts']), key=f"btn_top_plant_{row['Plant']}", use_container_width=True):
                    top_plant_popup(row['Plant'], df[df['Plant'] == row['Plant']])
        with t3:
            st.markdown("**Top Impacted Suppliers**")
            top_suppliers = df['Supplier'].value_counts().head(5).reset_index()
            top_suppliers.columns = ['Supplier', 'Alerts']
            c1, c2 = st.columns([3, 1])
            c1.caption("Supplier Name")
            c2.caption("Alerts")
            for _, row in top_suppliers.iterrows():
                c1, c2 = st.columns([3, 1])
                c1.write(row['Supplier'])
                if c2.button(str(row['Alerts']), key=f"btn_top_supplier_{row['Supplier']}", use_container_width=True):
                    top_supplier_popup(row['Supplier'], df[df['Supplier'] == row['Supplier']])

    with cat_tabs[1]: # Cycle Time
        df_tab = df[df['Alert Type'] == 'Cycle Time']
        c1, c2 = st.columns([8, 2])
        with c2: render_tab_export_button("cycle_time", df_tab, "cycle_time")
        render_tab_summary(df_tab, "cycle_time")
        st.divider()
        render_alert_hierarchy(df_tab, "Cycle Time")
        
    with cat_tabs[2]: # Run Rate
        df_tab = df[df['Alert Type'].str.contains('Run Rate')]
        c1, c2 = st.columns([8, 2])
        with c2: render_tab_export_button("run_rate", df_tab, "run_rate")
        render_tab_summary(df_tab, "run_rate")
        st.divider()
        
        rr_tab1, rr_tab2 = st.tabs(["Run Rate Shot Efficiency", "Run Rate Time Stability"])
        with rr_tab1:
            render_alert_hierarchy(df[df['Alert Type'] == 'Low Run Rate - Shot Efficiency'], "Run Rate Shot Efficiency")
        with rr_tab2:
            render_alert_hierarchy(df[df['Alert Type'] == 'Low Run Rate - Time Stability'], "Run Rate Time Stability")
        
    with cat_tabs[3]: # Capacity Risk
        df_tab = df[df['Alert Type'].str.contains('Capacity Risk')]
        c1, c2 = st.columns([8, 2])
        with c2: render_tab_export_button("capacity_risk", df_tab, "capacity_risk")
        render_tab_summary(df_tab, "capacity_risk")
        st.divider()

        cr_tab1, cr_tab2 = st.tabs(["Loss Parts vs Optimal Capacity", "Loss Parts vs Target Capacity"])
        with cr_tab1:
            render_alert_hierarchy(df[df['Alert Type'] == 'Capacity Risk (Optimal)'], "Optimal Capacity")
        with cr_tab2:
            render_alert_hierarchy(df[df['Alert Type'] == 'Capacity Risk (Target)'], "Target Capacity")
        
    with cat_tabs[4]: # Tooling EOL
        df_tab = df[df['Alert Type'].str.contains('EOL')]
        c1, c2 = st.columns([8, 2])
        with c2: render_tab_export_button("tooling_eol", df_tab, "tooling_eol")
        render_tab_summary(df_tab, "tooling_eol")
        st.divider()
        render_alert_hierarchy(df_tab, "EOL")
        
    with cat_tabs[5]: # Operation Status
        df_tab = df[df['Alert Type'].str.contains('Operation Status')]
        c1, c2 = st.columns([8, 2])
        with c2: render_tab_export_button("operation_status", df_tab, "operation_status")
        render_tab_summary(df_tab, "operation_status")
        st.divider()
        render_alert_hierarchy(df_tab, "Operation Status")