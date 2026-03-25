import streamlit as st
import os
import sys
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

# Add root directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.operations import get_all_cases, get_case_by_id, get_case_transactions, get_current_narrative, get_audit_log
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
    # Outer layout to vertically center things
    st.write("<br><br><br><br><br>", unsafe_allow_html=True)
    
    col_left, col_mid, col_right = st.columns([1, 0.2, 1])
    
    with col_left:
        st.markdown("""
        <div style="padding-top: 40px;">
            <h1 style="font-size: 3.5rem; letter-spacing: 2px; margin-bottom: 0px;">FINSENTRY AI</h1>
            <div style="font-size: 1.2rem; font-weight: 500; color: #E0E0E0; margin-top: 5px;">
                <span style="color: #FF3D00;">✨</span> AI Powered SAR Generator
            </div>
            <div class="login-divider"></div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Learn More", key="learn_more_btn", type="primary" if not st.session_state.show_info else "secondary"):
            st.session_state.show_info = not st.session_state.show_info
            
        if st.session_state.show_info:
            st.markdown("""
            <div style="background: rgba(255,255,255,0.05); border-left: 3px solid #FF3D00; padding: 15px; border-radius: 4px; margin-top: 20px;">
                <h4 style="margin-top:0;">What is FinSentry AI?</h4>
                <p style="color:#B0BEC5; font-size: 0.95rem; line-height: 1.5;">
                FinSentry AI is an automated Suspicious Activity Report (SAR) generator designed for financial institutions. 
                Instead of compliance officers spending hours gathering metrics, interpreting transaction topologies, and manually 
                writing regulatory forms, FinSentry intelligently analyzes bank CSV ledgers, accurately grades the risk via fixed heuristics, 
                and references live FinCEN regulations using RAG (Retrieval-Augmented Generation) to draft standard-proof SAR narratives automatically.
                </p>
            </div>
            """, unsafe_allow_html=True)

    with col_mid:
        st.write("") # Spacer
        
    with col_right:
        st.markdown('<div class="subtext">User Name</div>', unsafe_allow_html=True)
        username = st.text_input("Username", key="login_user", placeholder="👤 Enter your user name", label_visibility="collapsed")
        
        st.write("<br>", unsafe_allow_html=True)
        st.markdown('<div class="subtext">Password</div>', unsafe_allow_html=True)
        password = st.text_input("Password", type="password", key="login_pass", placeholder="🔒 ••••••••••", label_visibility="collapsed")
        
        st.write("<br><br>", unsafe_allow_html=True)
        if st.button("🛡️ Secure Login", use_container_width=True, type="primary"):
            if username == "admin" and password == "admin": 
                st.session_state.logged_in = True
                st.session_state.username = "Sarah Jane"
                st.session_state.user_role = "AML Analyst"
                st.rerun()
            else:
                st.error("Authentication Failed. Unauthorized Access Logged.")
        
    st.write("<br><br><br><br><br>", unsafe_allow_html=True)

def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# ----------------- SIDEBAR -----------------
def render_sidebar():
    st.sidebar.markdown(f"<h2 style='color: var(--text-white); margin-bottom:0px; letter-spacing:1px;'>FINSENTRY AI</h2>", unsafe_allow_html=True)
    st.sidebar.markdown(f"<div style='color: var(--accent-orange); font-size: 0.8rem; font-weight:700; text-transform:uppercase;'>System Operator</div>", unsafe_allow_html=True)
    st.sidebar.markdown(f"<div style='margin-bottom:15px; color: #B0BEC5;'><span style='font-size:1.2rem; vertical-align:middle;'>👤</span> {st.session_state.username} ({st.session_state.user_role})</div>", unsafe_allow_html=True)
    st.sidebar.markdown("---")
    
    views = ["Dashboard", "Case Management", "Case Repository", "SAR Reporting", "Audit Trail"]
    
    for view in views:
        is_active = (st.session_state.current_view == view)
        if st.sidebar.button(view, use_container_width=True, type="primary" if is_active else "secondary"):
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
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<h4>Risk Level Distribution</h4>', unsafe_allow_html=True)
        med_risk = sum(1 for c in cases if safely_get_enum_name(c.risk_level) == "MEDIUM")
        low_risk = sum(1 for c in cases if safely_get_enum_name(c.risk_level) == "LOW")
        
        df_pie = pd.DataFrame({"Risk": ["HIGH", "MEDIUM", "LOW"], "Count": [high_risk, med_risk, low_risk]})
        fig_pie = px.pie(df_pie, values='Count', names='Risk', hole=0.5,
                         color='Risk', color_discrete_map={"HIGH": "#FF3D00", "MEDIUM": "#FF9800", "LOW": "#4CAF50"})
        fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              font=dict(color="white"), margin=dict(t=20, b=20, l=0, r=0))
        st.plotly_chart(fig_pie, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
    with colB:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<h4>Anomaly Risk Scoring (Top Entities)</h4>', unsafe_allow_html=True)
        scores = [{"Entity": c.customer_name, "Risk Score": c.risk_score or 0} for c in cases]
        df_bar = pd.DataFrame(scores).sort_values("Risk Score", ascending=False).head(5)
        
        fig_bar = px.bar(df_bar, x='Risk Score', y='Entity', orientation='h', text='Risk Score')
        fig_bar.update_traces(marker_color='#FF3D00', textposition='outside')
        fig_bar.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              font=dict(color="white"), margin=dict(t=20, b=20, l=0, r=0),
                              xaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)'),
                              yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_bar, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

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
            st.markdown('<div class="glass-card" style="margin-top:20px;">', unsafe_allow_html=True)
            st.markdown("<h4 style='color: var(--accent-orange);'>Suspicious Activity Report Transcription</h4>", unsafe_allow_html=True)
            st.markdown("<hr style='border-color: rgba(255,255,255,0.1); margin-top:5px; margin-bottom:20px;'>", unsafe_allow_html=True)
            
            st.markdown(f"<p style='color: #E0E0E0; line-height:1.6; font-size:1.05rem;'>{narrative.content}</p>", unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
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
    elif view == "Audit Trail":
        view_audit_trail()
