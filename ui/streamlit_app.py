import streamlit as st
import os
import sys
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# Add root directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.operations import get_all_cases, get_case_by_id, get_case_transactions, get_current_narrative, get_audit_log, save_narrative, update_case_status
from src.integration.sar_pipeline import SARPipeline
from src.generators.narrative_generator_llama import LlamaNarrativeGenerator

st.set_page_config(
    page_title="FinSentry AI | SAR Intelligence",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Dark Mode, Red/Orange Accents, Glassmorphism)
st.markdown("""
<style>
    /* Reset & Base Variables */
    :root {
        --bg-dark: #0A0E17;
        --card-bg: rgba(19, 28, 45, 0.7);
        --accent-orange: #FF3D00;
        --accent-glow: rgba(255, 61, 0, 0.4);
        --text-white: #FFFFFF;
        --text-muted: #8E9BAE;
        --border-color: rgba(255, 255, 255, 0.05);
    }

    /* Main background */
    .stApp {
        background-color: var(--bg-dark);
        background-image: linear-gradient(135deg, rgba(255,61,0,0.03) 0%, rgba(10,14,23,1) 50%, rgba(255,61,0,0.02) 100%);
    }
    
    /* Typography */
    h1, h2, h3, h4, h5, h6 {
        color: var(--text-white) !important;
        font-family: 'Helvetica Neue', sans-serif;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    .subtext {
        color: var(--text-muted);
        font-size: 1rem;
        margin-bottom: 5px;
        font-weight: 500;
    }

    /* Primary Gradient Button Injection for Streamlit */
    /* Target primary buttons universally across the app for the consistent glowing theme */
    button[kind="primary"] {
        background: linear-gradient(90deg, #FF3D00 0%, #E65100 100%) !important;
        color: #fff !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.6rem 1.5rem !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 15px rgba(255, 61, 0, 0.4) !important;
        transition: all 0.3s ease !important;
    }
    button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(255, 61, 0, 0.6) !important;
    }
    button[kind="secondary"] {
        background: transparent !important;
        color: var(--text-white) !important;
        border: 1px solid rgba(255, 61, 0, 0.5) !important;
        border-radius: 8px !important;
        transition: all 0.3s ease !important;
    }
    button[kind="secondary"]:hover {
        background: rgba(255, 61, 0, 0.1) !important;
    }

    /* Container Styling - Glassmorphic */
    .glass-card {
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(10px);
        margin-bottom: 20px;
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: 800;
        color: var(--text-white);
        margin: 5px 0;
    }
    .metric-label {
        font-size: 0.9rem;
        color: var(--text-muted);
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* Input Fields styling overrides */
    .stTextInput>div>div>input {
        background-color: rgba(255, 255, 255, 0.05) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        color: white !important;
        border-radius: 8px !important;
    }
    .stTextInput>div>div>input:focus {
        border-color: var(--accent-orange) !important;
        box-shadow: 0 0 0 1px var(--accent-orange) !important;
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #101622 !important;
        border-right: 1px solid var(--border-color);
    }
    [data-testid="stSidebar"] button {
        border-radius: 6px !important;
        text-align: left;
        font-weight: 600;
        margin-bottom: 5px;
    }

    /* Login Area Specific Tweaks */
    .login-divider {
        width: 60px;
        height: 3px;
        background-color: var(--accent-orange);
        margin: 15px 0 30px 0;
        border-radius: 2px;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- SESSION STATE -----------------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'current_view' not in st.session_state:
    st.session_state.current_view = "Dashboard"
if 'show_info' not in st.session_state:
    st.session_state.show_info = False

@st.cache_resource
def get_pipeline():
    llama_gen = LlamaNarrativeGenerator()
    return SARPipeline(llama_generator=llama_gen)

def safely_get_enum_name(enum_val):
    if hasattr(enum_val, 'name'):
        return enum_val.name
    return str(enum_val).split('.')[-1]

# ----------------- LOGIN PAGE -----------------
def login_page():
    # Style the login form column as a bordered glass card
    st.markdown("""<style>
    .login-form-col [data-testid="stVerticalBlockBorderWrapper"],
    [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(4) {
        background: rgba(15,23,42,0.85) !important;
        border: 1px solid rgba(100,150,255,0.15) !important;
        border-radius: 16px !important;
        padding: 30px 25px !important;
        box-shadow: 0 0 40px rgba(50,100,255,0.06), 0 8px 32px rgba(0,0,0,0.4) !important;
        overflow: hidden !important;
    }
    </style>""", unsafe_allow_html=True)
    
    st.write("<br><br>", unsafe_allow_html=True)
    
    _, col_left, col_mid, col_right, _ = st.columns([0.3, 1, 0.08, 1, 0.3])
    
    with col_left:
        st.markdown('<div style="padding-top:30px;"><h1 style="font-size:3rem;letter-spacing:2px;margin-bottom:5px;">FINSENTRY AI</h1><div style="font-size:1.1rem;font-weight:500;color:#E0E0E0;margin-top:5px;">AI Powered SAR Generator</div><div class="login-divider"></div></div>', unsafe_allow_html=True)
        
        if st.button("Learn More", key="learn_more_btn", type="primary" if not st.session_state.show_info else "secondary"):
            st.session_state.show_info = not st.session_state.show_info
            
        if st.session_state.show_info:
            st.markdown('<div style="background:rgba(255,255,255,0.05);border-left:3px solid #FF3D00;padding:15px;border-radius:4px;margin-top:10px;"><h4 style="margin-top:0;">What is FinSentry AI?</h4><p style="color:#B0BEC5;font-size:0.95rem;line-height:1.5;">FinSentry AI is an automated SAR generator for financial institutions. It analyzes bank CSV ledgers, grades risk via fixed heuristics, and references FinCEN regulations using RAG to draft SAR narratives automatically.</p></div>', unsafe_allow_html=True)

    with col_mid:
        st.write("")
        
    with col_right:
        st.markdown('<h2 style="color:#fff !important;text-align:center;font-size:1.5rem;font-weight:700;margin-bottom:20px;font-style:italic;">Sign In to Your Account</h2>', unsafe_allow_html=True)
        
        st.markdown('<div style="color:#8E9BAE;font-size:0.85rem;margin-bottom:4px;">User Name</div>', unsafe_allow_html=True)
        username = st.text_input("Username", key="login_user", placeholder="Enter your user name", label_visibility="collapsed")
        
        st.markdown('<div style="color:#8E9BAE;font-size:0.85rem;margin-bottom:4px;margin-top:12px;">Password</div>', unsafe_allow_html=True)
        password = st.text_input("Password", type="password", key="login_pass", placeholder="Enter your password", label_visibility="collapsed")
        
        st.write("")
        if st.button("Secure Login", use_container_width=True, type="primary"):
            if username == "admin" and password == "admin": 
                st.session_state.logged_in = True
                st.session_state.username = "Sarah Jane"
                st.session_state.user_role = "AML Analyst"
                st.rerun()
            else:
                st.error("Authentication Failed. Unauthorized Access Logged.")

def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# ----------------- SIDEBAR -----------------
def render_sidebar():
    st.sidebar.markdown("<h2 style='color: var(--text-white); margin-bottom:0px; letter-spacing:2px; font-size:1.6rem;'>FINSENTRY AI</h2>", unsafe_allow_html=True)
    
    # User info card
    st.sidebar.markdown(f'<div style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,61,0,0.3);border-radius:10px;padding:10px 14px;margin:10px 0 15px 0;"><div style="color:var(--accent-orange);font-size:0.7rem;font-weight:700;text-transform:uppercase;letter-spacing:1px;">System Operator</div><div style="color:#B0BEC5;font-size:0.95rem;margin-top:4px;">&#x1F464; {st.session_state.username} ({st.session_state.user_role})</div></div>', unsafe_allow_html=True)
    
    st.sidebar.markdown("---")
    
    views = ["Dashboard", "Case Management", "Case Repository", "SAR Reporting", "Review", "Audit Trail"]
    
    # Style sidebar buttons as tile cards via CSS
    st.sidebar.markdown("""<style>
    [data-testid="stSidebar"] .stButton button {
        border-radius:10px !important;
        min-height:75px !important;
        padding:12px 10px !important;
        font-size:0.8rem !important;
        font-weight:600 !important;
        text-align:left !important;
        justify-content:flex-start !important;
        border:1px solid rgba(255,255,255,0.08) !important;
        background:rgba(255,255,255,0.03) !important;
        color:#B0BEC5 !important;
        transition: all 0.2s ease !important;
    }
    [data-testid="stSidebar"] .stButton button:hover {
        border-color:rgba(255,61,0,0.4) !important;
        background:rgba(255,61,0,0.08) !important;
        color:#fff !important;
    }
    [data-testid="stSidebar"] .stButton button[kind="primary"] {
        background:linear-gradient(135deg,#FF3D00,#FF6D00) !important;
        border:none !important;
        color:#fff !important;
        font-weight:700 !important;
    }
    </style>""", unsafe_allow_html=True)
    
    # Render 2-column grid
    for i in range(0, len(views), 2):
        c1, c2 = st.sidebar.columns(2)
        for col, idx in [(c1, i), (c2, i+1)]:
            if idx < len(views):
                view = views[idx]
                is_active = (st.session_state.current_view == view)
                with col:
                    if st.button(view, use_container_width=True, key=f"nav_{view}", type="primary" if is_active else "secondary"):
                        st.session_state.current_view = view
                        st.rerun()
    
    st.sidebar.markdown("---")
    
    if st.sidebar.button("Logout", use_container_width=True, type="secondary"):
        logout()

# ----------------- VIEWS -----------------
def view_dashboard():
    st.markdown('<h1 style="border-bottom: 2px solid var(--accent-orange); display:inline-block; padding-bottom:5px; margin-bottom:30px;">OVERVIEW DASHBOARD</h1>', unsafe_allow_html=True)
    
    try:
        cases = get_all_cases()
    except Exception as e:
        cases = []
        st.error(f"Database error: {e}")
        
    total_cases = len(cases)
    high_risk = sum(1 for c in cases if safely_get_enum_name(c.risk_level) == "HIGH")
    sar_filed = sum(1 for c in cases if safely_get_enum_name(c.status) == "FILED")
    pending = total_cases - sar_filed
    
    # KIP Cards Level
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class="glass-card text-center" style="text-align:center;">
            <div class="metric-label">TOTAL ENTITIES</div>
            <div class="metric-value">{total_cases}</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="glass-card text-center" style="text-align:center;">
            <div class="metric-label">CRITICAL ALERTS</div>
            <div class="metric-value" style="color: var(--accent-orange);">{high_risk}</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="glass-card text-center" style="text-align:center;">
            <div class="metric-label">REPORTS FILED</div>
            <div class="metric-value" style="color: #4CAF50;">{sar_filed}</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="glass-card text-center" style="text-align:center;">
            <div class="metric-label">PENDING REVIEW</div>
            <div class="metric-value">{pending}</div>
        </div>""", unsafe_allow_html=True)

    if total_cases == 0:
        st.info("System operational. Awaiting transaction batch data to populate metrics.")
        return

    # Charts Level
    colA, colB = st.columns(2)
    
    with colA:
        med_risk = sum(1 for c in cases if safely_get_enum_name(c.risk_level) == "MEDIUM")
        low_risk = sum(1 for c in cases if safely_get_enum_name(c.risk_level) == "LOW")
        
        st.markdown('<h4>Risk Level Distribution</h4>', unsafe_allow_html=True)
        df_pie = pd.DataFrame({"Risk": ["HIGH", "MEDIUM", "LOW"], "Count": [high_risk, med_risk, low_risk]})
        fig_pie = px.pie(df_pie, values='Count', names='Risk', hole=0.5,
                         color='Risk', color_discrete_map={"HIGH": "#FF3D00", "MEDIUM": "#FF9800", "LOW": "#4CAF50"})
        fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              font=dict(color="white"), margin=dict(t=20, b=20, l=0, r=0))
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with colB:
        scores = [{"Entity": c.customer_name, "Risk Score": c.risk_score or 0} for c in cases]
        df_bar = pd.DataFrame(scores).sort_values("Risk Score", ascending=False).head(5)
        
        st.markdown('<h4>Anomaly Risk Scoring (Top Entities)</h4>', unsafe_allow_html=True)
        fig_bar = px.bar(df_bar, x='Risk Score', y='Entity', orientation='h', text='Risk Score')
        fig_bar.update_traces(marker_color='#FF3D00', textposition='outside')
        fig_bar.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              font=dict(color="white"), margin=dict(t=20, b=20, l=0, r=0),
                              xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
                              yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_bar, use_container_width=True)

def view_case_management():
    st.markdown('<h1 style="border-bottom: 2px solid var(--accent-orange); display:inline-block; padding-bottom:5px; margin-bottom:30px;">CASE MANAGEMENT</h1>', unsafe_allow_html=True)
    st.markdown("<p style='color: var(--text-muted);'>Instantiate the automated transaction pipeline for suspicious activity detection by providing the subject entity profile and their respective CSV ledger.</p>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### Entity Information Target", unsafe_allow_html=True)
        st.markdown("<hr style='border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
        c_name = st.text_input("Customer Name", "Apex Holdings LLC")
        c_acc = st.text_input("Account Number", "987654321")
        c_occ = st.text_input("Business Area", "Cross-border Logistics")
        c_inc = st.number_input("Stated Monthly Revenue (₹/$)", value=450000)
        
    with col2:
        st.markdown("### Transaction Ingestion", unsafe_allow_html=True)
        st.markdown("<hr style='border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
        st.write("Upload raw ledger (CSV Format)")
        uploaded_file = st.file_uploader("", type=['csv'], label_visibility="collapsed")
        
        st.write("<br>", unsafe_allow_html=True)
        if st.button("EXECUTE ANALYSIS PIPELINE", type="primary", use_container_width=True):
            if uploaded_file:
                customer_info = {
                    'name': c_name,
                    'account_number': c_acc,
                    'occupation': c_occ,
                    'stated_income': c_inc
                }
                with st.spinner("Pipeline Engaging... Analyzing patterns, synthesizing RAG regulations, and generating SAR reasoning..."):
                    with open("temp_tx.csv", "wb") as f:
                        f.write(uploaded_file.getbuffer())
                        
                    pipeline = get_pipeline()
                    result = pipeline.process_case("temp_tx.csv", customer_info)
                    
                    if result.get("status") == "SUCCESS":
                        st.success(f"Processing Complete! Reference ID: {result['case_id']}")
                        st.info(f"Assigned Risk Level: {safely_get_enum_name(result['risk_level'])} (Score: {result['risk_score']})")
                    else:
                        st.error(f"Pipeline error: {result.get('error_message')}")
            else:
                st.warning("Please upload a transaction CSV batch before execution.")

def view_case_repository():
    st.markdown('<h1 style="border-bottom: 2px solid var(--accent-orange); display:inline-block; padding-bottom:5px; margin-bottom:30px;">CASE REPOSITORY</h1>', unsafe_allow_html=True)
    
    cases = get_all_cases()
    if not cases:
        st.info("No active investigations located in database.")
        return
        
    c1, c2, c3 = st.columns(3)
    search_kw = c1.text_input("Search Identification", placeholder="ID or Name")
    risk_filter = c2.selectbox("Filter Risk", ["ALL", "HIGH", "MEDIUM", "LOW"])
    status_filter = c3.selectbox("Filter Status", ["ALL", "DRAFT", "UNDER_REVIEW", "FILED"])
    
    filtered = []
    for c in cases:
        r_lvl = safely_get_enum_name(c.risk_level)
        s_lvl = safely_get_enum_name(c.status)
        
        if risk_filter != "ALL" and r_lvl != risk_filter: continue
        if status_filter != "ALL" and s_lvl != status_filter: continue
        if search_kw.lower() not in c.case_id.lower() and search_kw.lower() not in c.customer_name.lower(): continue
        filtered.append(c)
        
    if filtered:
        # Build strict internal representation instead of dumping class
        df_list = []
        for f in filtered:
            df_list.append({
                "Reference ID": f.case_id,
                "Entity Name": f.customer_name,
                "Risk Score": f.risk_score,
                "Risk Level": safely_get_enum_name(f.risk_level),
                "Workflow Phase": safely_get_enum_name(f.status),
                "Time Added": f.created_at.strftime("%Y-%m-%d %H:%M") if f.created_at else "N/A"
            })
        st.dataframe(pd.DataFrame(df_list), use_container_width=True, hide_index=True)
    else:
        st.write("No matching cases found for these filters.")

def view_sar_reporting():
    st.markdown('<h1 style="border-bottom: 2px solid var(--accent-orange); display:inline-block; padding-bottom:5px; margin-bottom:30px;">SAR REPORTING</h1>', unsafe_allow_html=True)
    
    cases = get_all_cases()
    if not cases:
        st.warning("No regulatory reports synthesized yet.")
        return
        
    target = st.selectbox("Select Target Reference", [c.case_id for c in cases])
    
    if target:
        case = get_case_by_id(target)
        narrative = get_current_narrative(target)
        
        c1, c2 = st.columns([1, 1])
        with c1:
            st.markdown(f"**Entity Subject:** {case.customer_name}")
        with c2:
            st.markdown(f"**Operational Workflow Phase:** {safely_get_enum_name(case.status)}")
        
        if narrative:
            st.markdown("<h4 style='color: var(--accent-orange);'>Suspicious Activity Report Transcription</h4>", unsafe_allow_html=True)
            st.markdown("<hr style='border-color: rgba(255,255,255,0.1); margin-top:5px; margin-bottom:20px;'>", unsafe_allow_html=True)
            st.markdown(f"<p style='color: #E0E0E0; line-height:1.6; font-size:1.05rem;'>{narrative.content}</p>", unsafe_allow_html=True)
            
            st.download_button("📥 Export Regulatory Document (.TXT)", narrative.content, file_name=f"SAR_{target}_{case.customer_name}.txt", type="primary")
        else:
            st.error("SAR Generation sequence incomplete or not generated for this entity.")

def view_audit_trail():
    st.markdown('<h1 style="border-bottom: 2px solid var(--accent-orange); display:inline-block; padding-bottom:5px; margin-bottom:30px;">EXPLAINABILITY & AUDIT</h1>', unsafe_allow_html=True)
    st.markdown("<p style='color: var(--text-muted);'>Maintain immutable traceability between data ingestion, rule engine flags, vector database RAG citations, and LLaMA logic reasoning.</p>", unsafe_allow_html=True)
    
    cases = get_all_cases()
    if not cases:
        return
        
    target = st.selectbox("Target Entity Traceability", [c.case_id for c in cases], label_visibility="collapsed")
    
    if target:
        log = get_audit_log(target)
        if log:
            data = log.audit_data
            
            col1, col2 = st.columns([1, 1])
            with col1:
                st.markdown("<h4>Rule Engine Triggers</h4>", unsafe_allow_html=True)
                st.markdown("<hr style='border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
                
                risk_assess = data.get('risk_assessment_trail', {})
                # Access the list of dictionaries instead of integer count
                rules = risk_assess.get('rules_triggered_details', [])
                if isinstance(rules, list) and len(rules) > 0:
                    for r in rules:
                        st.markdown(f"""
                        <div style="background: rgba(255,255,255,0.03); border-left: 4px solid var(--accent-orange); padding: 12px; margin-bottom: 10px; border-radius: 4px;">
                            <strong style="color:var(--text-white);">{r.get('rule_id')}</strong>: {r.get('rule_name')}<br>
                            <span style="color:#B0BEC5; font-size:0.85em;">Desc: {r.get('explanation')}</span><br>
                            <span style="color:#FF9800; font-size:0.85em; font-weight:600;">System Severity Grade: {r.get('severity')}</span>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.write("No anomalous rule breaches recorded in ledger.")
                    
            with col2:
                st.markdown("<h4>Vector Database (RAG) Citations</h4>", unsafe_allow_html=True)
                st.markdown("<hr style='border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
                
                ai_trail = data.get('ai_generation_trail', {})
                citations = ai_trail.get('citations_used', {})
                if citations:
                    for rule_id, context in citations.items():
                        st.markdown(f"<strong style='color:var(--text-white);'>Regulatory Injection [Rule {rule_id}]</strong>", unsafe_allow_html=True)
                        st.markdown(f"<div style='background: rgba(255,255,255,0.03); padding: 12px; border-radius: 4px; border-left: 2px solid #00B0FF; margin-bottom: 10px; color:#cfd8df; font-size:0.9em;'>{(str(context)[:250] + '...')}</div>", unsafe_allow_html=True)
                else:
                    st.write("No external FinCEN regulatory anchors fetched.")
                    
            st.markdown("### Immutable Log Snapshot")
            with st.expander("Expand JSON Integrity Structure"):
                st.json(data)
        else:
            st.error("Audit log missing. Transaction may have failed or bypassed logging.")

# ----------------- REVIEW PAGE -----------------
def view_review():
    st.markdown('<h1 style="border-bottom: 2px solid var(--accent-orange); display:inline-block; padding-bottom:5px; margin-bottom:30px;">SAR REVIEW WORKBENCH</h1>', unsafe_allow_html=True)
    st.markdown("<p style='color: var(--text-muted);'>Review, edit, and finalize SAR narratives before regulatory submission. This is where an AML analyst validates AI-generated output.</p>", unsafe_allow_html=True)
    
    cases = get_all_cases()
    if not cases:
        st.warning("No cases available for review. Process a transaction batch from Case Management first.")
        return
    
    # Case selector
    case_options = {f"{c.case_id} — {c.customer_name} ({safely_get_enum_name(c.risk_level)})": c.case_id for c in cases}
    selected_label = st.selectbox("Select Case / SAR for Review", list(case_options.keys()))
    target_id = case_options[selected_label]
    
    case = get_case_by_id(target_id)
    narrative = get_current_narrative(target_id)
    audit = get_audit_log(target_id)
    
    if not case:
        st.error("Case not found.")
        return

    # Status banner
    risk_lvl = safely_get_enum_name(case.risk_level)
    risk_color = "#FF3D00" if risk_lvl == "HIGH" else ("#FF9800" if risk_lvl == "MEDIUM" else "#4CAF50")
    st.markdown(f"""
    <div style="display:flex; gap:20px; margin-bottom:25px; flex-wrap:wrap;">
        <div class="glass-card" style="flex:1; min-width:200px; text-align:center; padding:16px;">
            <div class="metric-label">CASE ID</div>
            <div style="color:var(--text-white); font-size:1.1rem; font-weight:700; margin-top:4px;">{case.case_id}</div>
        </div>
        <div class="glass-card" style="flex:1; min-width:200px; text-align:center; padding:16px;">
            <div class="metric-label">ENTITY</div>
            <div style="color:var(--text-white); font-size:1.1rem; font-weight:700; margin-top:4px;">{case.customer_name}</div>
        </div>
        <div class="glass-card" style="flex:1; min-width:200px; text-align:center; padding:16px;">
            <div class="metric-label">RISK SCORE</div>
            <div style="color:{risk_color}; font-size:1.5rem; font-weight:800; margin-top:4px;">{case.risk_score or 0}/100</div>
        </div>
        <div class="glass-card" style="flex:1; min-width:200px; text-align:center; padding:16px;">
            <div class="metric-label">STATUS</div>
            <div style="color:var(--text-white); font-size:1.1rem; font-weight:700; margin-top:4px;">{safely_get_enum_name(case.status)}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ---- 3-COLUMN LAYOUT ----
    current_content = narrative.content if narrative else "No SAR narrative has been generated for this case yet. Please run the analysis pipeline from Case Management first."

    col_left, col_mid, col_right = st.columns([1.2, 2.2, 1])
    
    # ---- LEFT COLUMN ----
    with col_left:
        score_val = case.risk_score or 0
        gauge_pct = score_val / 100
        rules_html = ""
        if audit and audit.audit_data:
            risk_trail = audit.audit_data.get('risk_assessment_trail', {})
            rules = risk_trail.get('rules_triggered_details', [])
            if isinstance(rules, list) and len(rules) > 0:
                for r in rules:
                    sev = r.get('severity', 'N/A')
                    sc = "#FF3D00" if sev in ['HIGH', 'CRITICAL'] else ("#FF9800" if sev == 'MEDIUM' else "#4CAF50")
                    rules_html += f'<div style="background:rgba(255,255,255,0.03);border-left:4px solid {sc};padding:10px;margin-bottom:8px;border-radius:4px;"><strong style="color:#fff;font-size:0.85rem;">{r.get("rule_id")}: {r.get("rule_name")}</strong><br><span style="color:#B0BEC5;font-size:0.78em;">{r.get("explanation","")}</span><br><span style="color:{sc};font-size:0.78em;font-weight:600;">Severity: {sev}</span></div>'
            else:
                rules_html = '<p style="color:#8E9BAE;">No rules triggered.</p>'
        else:
            rules_html = '<p style="color:#8E9BAE;">Audit data unavailable.</p>'
        left_html = f'<div style="background:rgba(19,28,45,0.7);border:1px solid rgba(255,255,255,0.05);border-radius:12px;padding:20px;box-shadow:0 8px 32px rgba(0,0,0,0.3);"><div style="text-align:center;margin-bottom:15px;"><div style="color:#8E9BAE;font-size:0.9rem;text-transform:uppercase;letter-spacing:1px;margin-bottom:10px;">Composite Risk Score</div><div style="position:relative;width:120px;height:70px;margin:0 auto 5px auto;overflow:hidden;"><svg viewBox="0 0 120 70" style="width:100%;height:100%;"><path d="M10,65 A50,50 0 0,1 110,65" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="10" stroke-linecap="round"/><path d="M10,65 A50,50 0 0,1 110,65" fill="none" stroke="{risk_color}" stroke-width="10" stroke-linecap="round" stroke-dasharray="{gauge_pct * 157}" stroke-dashoffset="0"/></svg><div style="position:absolute;bottom:0;width:100%;text-align:center;font-size:1.8rem;font-weight:800;color:#fff;">{score_val}</div></div><div style="color:#8E9BAE;font-size:0.75rem;margin-top:5px;">Risk Level</div><div style="display:flex;justify-content:space-around;margin-top:10px;"><div style="text-align:center;"><div style="color:{risk_color};font-weight:700;font-size:0.9rem;">{risk_lvl}</div><div style="color:#8E9BAE;font-size:0.7rem;">Risk Level</div></div><div style="text-align:center;"><div style="color:#fff;font-weight:700;font-size:0.9rem;">₹{case.total_credits or 0:,.0f}</div><div style="color:#8E9BAE;font-size:0.7rem;">Account Size</div></div></div></div><hr style="border:none;border-top:1px solid rgba(255,255,255,0.08);margin:15px 0;"><h4 style="color:#fff !important;margin-bottom:12px;font-size:1rem;">⚠️ Triggered AML Rules</h4>{rules_html}</div>'
        st.markdown(left_html, unsafe_allow_html=True)
    
    # ---- MIDDLE COLUMN ----
    with col_mid:
        st.markdown("### 📝 SAR Narrative Editor")
        st.caption("Edit the AI-generated narrative. Changes can be saved as a new version.")
        edited_narrative = st.text_area(
            "SAR Narrative",
            value=current_content,
            height=480,
            key=f"review_editor_{target_id}",
            label_visibility="collapsed"
        )
    
    # ---- RIGHT COLUMN ----
    with col_right:
        reasoning_points = []
        if case.risk_score and case.risk_score >= 70:
            reasoning_points.append(f"High risk score ({case.risk_score}/100) warrants immediate regulatory filing.")
        if case.risk_score and case.risk_score >= 40 and case.risk_score < 70:
            reasoning_points.append(f"Medium risk score ({case.risk_score}/100) requires enhanced due diligence.")
        if case.flags_triggered and case.flags_triggered > 0:
            reasoning_points.append(f"{case.flags_triggered} AML red flag(s) triggered by deterministic rule engine.")
        if narrative:
            reasoning_points.append(f"SAR narrative generated ({narrative.word_count or 'N/A'} words).")
        if not reasoning_points:
            reasoning_points.append("No additional reasoning flags at this time.")
        bullets = ""
        for p in reasoning_points:
            bullets += f'<div style="color:#E0E0E0;font-size:0.83rem;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.05);">• {p}</div>'
        right_html = f'<div style="background:rgba(19,28,45,0.7);border:1px solid rgba(255,255,255,0.05);border-radius:12px;padding:18px;box-shadow:0 8px 32px rgba(0,0,0,0.3);margin-bottom:15px;"><h4 style="color:#fff !important;margin-top:0;margin-bottom:12px;font-size:1rem;">✅ Key Reasoning Points</h4>{bullets}</div>'
        st.markdown(right_html, unsafe_allow_html=True)
        st.markdown("#### Actions")
        if st.button("💾 Save Changes", type="primary", use_container_width=True, key="save_review"):
            if narrative and edited_narrative != current_content:
                result = save_narrative(
                    case_id=target_id,
                    content=edited_narrative,
                    metadata={'edited_by': st.session_state.username, 'edit_time': datetime.now().isoformat()},
                    created_by=st.session_state.username or 'Analyst',
                    generation_method='manual_edit'
                )
                if result:
                    st.success(f"✅ Saved v{result}!")
                    st.rerun()
                else:
                    st.error("Save failed.")
            elif not narrative:
                st.warning("No narrative yet.")
            else:
                st.info("No changes.")
        if narrative:
            st.download_button(
                "📥 Download SAR (.txt)",
                edited_narrative,
                file_name=f"SAR_{target_id}_{case.customer_name}.txt",
                type="secondary",
                use_container_width=True
            )
        if st.button("✅ Mark as Reviewed", type="secondary", use_container_width=True, key="mark_reviewed"):
            success = update_case_status(target_id, "UNDER_REVIEW")
            if success:
                st.success("Status updated.")
                st.rerun()


# ----------------- ROUTING -----------------
if not st.session_state.logged_in:
    login_page()
else:
    render_sidebar()
    view = st.session_state.current_view
    
    if view == "Dashboard":
        view_dashboard()
    elif view == "Case Management":
        view_case_management()
    elif view == "Case Repository":
        view_case_repository()
    elif view == "SAR Reporting":
        view_sar_reporting()
    elif view == "Review":
        view_review()
    elif view == "Audit Trail":
        view_audit_trail()
