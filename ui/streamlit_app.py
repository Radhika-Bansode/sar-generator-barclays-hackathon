import streamlit as st
import os
import sys
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import io

# Add root directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.operations import get_all_cases, get_case_by_id, get_case_transactions, get_current_narrative, get_audit_log, save_narrative, update_case_status
from src.integration.sar_pipeline import SARPipeline
from src.generators.narrative_generator_llama import LlamaNarrativeGenerator
from ui.pdf_generator import generate_sar_pdf

st.set_page_config(
    page_title="FinSentry AI | SAR Intelligence",
    page_icon="FS",
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
    
    views = ["Dashboard", "Case Intake", "CSV Intake", "Case Repository", "SAR Reporting", "Review", "Audit Trail"]
    
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
def view_csv_intake():
    st.markdown('<h1 style="border-bottom: 2px solid var(--accent-orange); display:inline-block; padding-bottom:5px; margin-bottom:10px;">CSV BATCH INTAKE</h1>', unsafe_allow_html=True)
    st.markdown("<p style='color: var(--text-muted); margin-bottom:20px;'>Upload a CSV file to batch-process transactions. The system will auto-detect if it contains Normal or Crypto data.</p>", unsafe_allow_html=True)

    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
    
    if uploaded_file is not None:
        try:
            import pandas as pd
            df = pd.read_csv(uploaded_file)
            st.dataframe(df.head(), use_container_width=True)
            
            headers = [h.lower() for h in df.columns]
            is_crypto = any(k in headers for k in ['hash', 'transaction_hash', 'wallet', 'crypto_amount', 'sender_wallet'])
            
            type_label = "CRYPTO" if is_crypto else "NORMAL BANKING"
            st.info(f"Detected Type: **{type_label}** | Rows found: {len(df)}")
            
            if st.button("EXECUTE BATCH PROCESSING", type="primary"):
                results = []
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                pipeline = get_pipeline()
                
                for i, row in df.iterrows():
                    status_text.text(f"Processing row {i+1} of {len(df)}...")
                    
                    if is_crypto:
                        # Map crypto columns
                        user_case = {
                            "transaction_hash": str(row.get('hash', row.get('transaction_hash', f'BATCH-TX-{i}'))),
                            "sender_wallet": str(row.get('sender_wallet', row.get('from_address', 'N/A'))),
                            "receiver_wallet": str(row.get('receiver_wallet', row.get('to_address', 'N/A'))),
                            "crypto_amount": float(row.get('amount', row.get('crypto_amount', 0))),
                            "crypto_type": str(row.get('token', row.get('crypto_type', 'USDT'))),
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                    else:
                        # Map banking columns
                        user_case = {
                            "name": str(row.get('from_name', row.get('name', 'Bulk User'))),
                            "account_number": str(row.get('from_account', row.get('account_number', 'N/A'))),
                            "txn_amount": float(row.get('amount', row.get('txn_amount', 0))),
                            "txn_type": str(row.get('type', row.get('txn_type', 'NEFT'))),
                            "channel": str(row.get('channel', 'Online')),
                            "country": str(row.get('country', 'India')),
                            "timestamp": str(row.get('date', datetime.now().strftime("%Y-%m-%d")))
                        }
                    
                    res = pipeline.process_single_transaction(user_case, is_crypto)
                    results.append({
                        "id": res.get("case_id", "N/A"),
                        "risk": res.get("risk_level", "UNKNOWN"),
                        "score": res.get("risk_score", 0),
                        "sar": "YES" if res.get("sar_generated") else "NO"
                    })
                    progress_bar.progress((i + 1) / len(df))
                
                status_text.success(f"Batch processing complete! {len(results)} records processed.")
                res_df = pd.DataFrame(results)
                st.markdown("### Processed Summary")
                st.dataframe(res_df, use_container_width=True)
                
        except Exception as e:
            st.error(f"Error processing CSV: {str(e)}")


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
    # Inject compact form CSS
    st.markdown("""<style>
    .ci-section-label {
        color: #8E9BAE;
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        margin: 18px 0 6px;
    }
    </style>""", unsafe_allow_html=True)

    st.markdown('<h1 style="border-bottom: 2px solid var(--accent-orange); display:inline-block; padding-bottom:5px; margin-bottom:10px;">CASE INTAKE</h1>', unsafe_allow_html=True)
    st.markdown("<p style='color: var(--text-muted); margin-bottom:20px;'>Submit a transaction for AI-powered risk evaluation and conditional SAR generation.</p>", unsafe_allow_html=True)

    # Transaction Type Selector
    txn_type = st.radio("Transaction Type", ["Normal (Banking)", "Crypto (Blockchain)"], horizontal=True, key="ci_txn_type_radio")
    is_crypto = txn_type.startswith("Crypto")

    if is_crypto:
        st.markdown("### Crypto Transaction Details")
        st.markdown('<div class="ci-section-label">Wallet & Transaction</div>', unsafe_allow_html=True)
        tx_hash = st.text_input("Transaction Hash *", placeholder="0xabc123...def456", key="ci_hash")
        c1, c2 = st.columns(2)
        with c1:
            sender_w = st.text_input("Sender Wallet *", placeholder="0x1234...5678", key="ci_sender")
        with c2:
            receiver_w = st.text_input("Receiver Wallet *", placeholder="0xabcd...ef01", key="ci_receiver")
        c3, c4 = st.columns(2)
        with c3:
            crypto_amt = st.number_input("Amount *", min_value=0.0, step=0.01, format="%.6f", key="ci_amt")
        with c4:
            crypto_type = st.selectbox("Crypto Type *", ["BTC", "ETH", "USDT", "XRP", "SOL", "BNB", "Other"], key="ci_ctype")
        timestamp = st.date_input("Transaction Date *", value=datetime.now(), key="ci_ts")
    else:
        st.markdown("### Banking Transaction Details")

        # Customer Info
        st.markdown('<div class="ci-section-label">Customer Information</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            cust_name = st.text_input("Customer Name *", placeholder="e.g. Ankita Sharma", key="ci_name")
            acct_open_date = st.date_input("Account Open Date *", value=datetime.now(), key="ci_open_date")
            occupation = st.text_input("Occupation *", placeholder="e.g. Student", key="ci_occupation")
        with c2:
            acct_num = st.text_input("Account Number *", placeholder="e.g. ACC12345", key="ci_acct")
            kyc_status = st.selectbox("KYC Status *", ["verified", "pending", "rejected"], key="ci_kyc")
            country = st.text_input("Country *", value="India", key="ci_country")

        # Transaction Details
        st.markdown('<div class="ci-section-label">Transaction Details</div>', unsafe_allow_html=True)
        c3, c4 = st.columns(2)
        with c3:
            txn_amount = st.number_input("Amount *", min_value=0.0, step=100.0, key="ci_txnamt")
            txn_type_sel = st.selectbox("Type *", ["UPI", "Wire Transfer", "Cash Deposit", "Cash Withdrawal", "NEFT", "RTGS", "IMPS", "SWIFT", "ACH", "Other"], key="ci_txntype")
            channel = st.selectbox("Channel *", ["Online", "Branch", "ATM", "Mobile", "POS"], key="ci_channel")
        with c4:
            timestamp = st.date_input("Transaction Date *", value=datetime.now(), key="ci_ts2")
            dest_account = st.text_input("Destination Acct *", placeholder="e.g. ACC56789", key="ci_dest_acct")
            dest_country = st.text_input("Destination Country *", value="India", key="ci_dest_country")

        # Pattern & Behavior
        st.markdown('<div class="ci-section-label">Pattern & Behavior Analysis</div>', unsafe_allow_html=True)
        c5, c6 = st.columns(2)
        with c5:
            avg_txn_range = st.text_input("Typical Txn Range", placeholder="e.g. 100-500", key="ci_avg_range")
            source_of_funds = st.text_input("Source of Funds *", placeholder="e.g. Salary", key="ci_source")
        with c6:
            txn_frequency = st.selectbox("Frequency", ["low", "medium", "high"], key="ci_freq")
            previous_flags = st.selectbox("Previous Flags", ["no", "yes"], key="ci_prev_flags")

        # Action & Status
        st.markdown('<div class="ci-section-label">Action & Status</div>', unsafe_allow_html=True)
        c7, c8 = st.columns(2)
        with c7:
            action_taken = st.text_input("Action Taken", value="Transaction flagged for review", key="ci_action")
        with c8:
            status_val = st.selectbox("Status", ["Under Review", "Closed after verification", "Escalated"], key="ci_status")

    # Centered submit button
    st.markdown('<div style="max-width:720px;margin:20px auto 0;">', unsafe_allow_html=True)
    btn_col1, btn_col2, btn_col3 = st.columns([1, 1.2, 1])
    with btn_col2:
        submitted = st.button("EXECUTE RISK ANALYSIS", type="primary", use_container_width=True, key="exec_pipeline")
    st.markdown('</div>', unsafe_allow_html=True)

    if submitted:
        # Validation
        valid = True
        if is_crypto:
            if not tx_hash.strip() or not sender_w.strip() or not receiver_w.strip() or crypto_amt <= 0:
                valid = False
        else:
            if not cust_name.strip() or not acct_num.strip() or txn_amount <= 0 or not country.strip():
                valid = False

        if not valid:
            st.error("All fields marked with * are mandatory. Please fill in all required fields.")
        else:
            # Build case object matching user_input_sar.py format
            if is_crypto:
                user_case = {
                    "transaction_hash": tx_hash.strip(),
                    "sender_wallet": sender_w.strip(),
                    "receiver_wallet": receiver_w.strip(),
                    "crypto_amount": crypto_amt,
                    "crypto_type": crypto_type,
                    "timestamp": str(timestamp)
                }
            else:
                user_case = {
                    "name": cust_name.strip(),
                    "account_number": acct_num.strip(),
                    "account_open_date": str(acct_open_date),
                    "occupation": occupation.strip() if occupation else "N/A",
                    "kyc_status": kyc_status,
                    "txn_amount": txn_amount,
                    "txn_type": txn_type_sel,
                    "channel": channel,
                    "country": country.strip(),
                    "timestamp": str(timestamp),
                    "txn_date": str(timestamp),
                    "destination_account": dest_account.strip() if dest_account else "N/A",
                    "destination_country": dest_country.strip() if dest_country else "India",
                    "avg_txn_range": avg_txn_range.strip() if avg_txn_range else "N/A",
                    "txn_frequency": txn_frequency,
                    "source_of_funds": source_of_funds.strip() if source_of_funds else "N/A",
                    "previous_flags": previous_flags,
                    "action_taken": action_taken.strip() if action_taken else "N/A",
                    "status": status_val
                }

            with st.spinner("Pipeline executing... Analyzing risk patterns, retrieving regulations, generating SAR..."):
                pipeline = get_pipeline()
                result = pipeline.process_single_transaction(user_case, is_crypto)

            st.session_state['last_intake_result'] = result
            st.session_state['last_intake_crypto'] = is_crypto
            st.session_state['last_intake_case'] = user_case

    # ── Display Results ──
    if 'last_intake_result' in st.session_state:
        result = st.session_state['last_intake_result']
        if result.get('status') == 'ERROR':
            st.error(f"Pipeline Error: {result.get('error_message', 'Unknown error')}")
        else:
            r_level = result.get('risk_level', 'UNKNOWN')
            r_score = result.get('risk_score', 0)
            reasons = result.get('reasons', [])
            r_color = "#FF3D00" if r_level == "HIGH" else ("#FF9800" if r_level == "MEDIUM" else "#4CAF50")

            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown('<h3 style="color:var(--text-white);">Risk Evaluation Results</h3>', unsafe_allow_html=True)

            rc1, rc2, rc3 = st.columns(3)
            with rc1:
                st.markdown(f"""<div class="glass-card" style="text-align:center;padding:20px;">
                    <div class="metric-label">RISK LEVEL</div>
                    <div style="font-size:2rem;font-weight:800;color:{r_color};margin:8px 0;">{r_level}</div>
                </div>""", unsafe_allow_html=True)
            with rc2:
                st.markdown(f"""<div class="glass-card" style="text-align:center;padding:20px;">
                    <div class="metric-label">RISK SCORE</div>
                    <div style="font-size:2rem;font-weight:800;color:{r_color};margin:8px 0;">{r_score}/100</div>
                </div>""", unsafe_allow_html=True)
            with rc3:
                sar_status = "GENERATED" if result.get('sar_generated') else "NOT REQUIRED"
                sar_color = "#FF3D00" if result.get('sar_generated') else "#4CAF50"
                st.markdown(f"""<div class="glass-card" style="text-align:center;padding:20px;">
                    <div class="metric-label">SAR STATUS</div>
                    <div style="font-size:1.3rem;font-weight:700;color:{sar_color};margin:8px 0;">{sar_status}</div>
                </div>""", unsafe_allow_html=True)

            if reasons:
                reasons_html = "".join([f'<div style="color:#E0E0E0;font-size:0.9rem;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.05);">- {r}</div>' for r in reasons])
                st.markdown(f"""<div class="glass-card" style="margin-top:10px;">
                    <h4 style="color:var(--accent-orange) !important;margin-bottom:10px;">Risk Indicators</h4>
                    {reasons_html}
                </div>""", unsafe_allow_html=True)

            if not result.get('sar_generated'):
                st.markdown(f"""<div class="glass-card" style="border-left:4px solid #4CAF50;margin-top:15px;">
                    <p style="color:#4CAF50;font-size:1.1rem;font-weight:600;margin:0;">
                    SAR not generated as {r_level.lower()} risk transaction detected.
                    </p><p style="color:var(--text-muted);margin-top:6px;">
                    Transaction does not meet the HIGH risk threshold required for SAR filing.
                    </p>
                </div>""", unsafe_allow_html=True)
            else:
                sar_text = result.get('sar_report', '')
                st.markdown('<h3 style="color:var(--accent-orange);margin-top:20px;">Generated SAR Narrative</h3>', unsafe_allow_html=True)
                st.markdown(f"""<div class="glass-card" style="max-height:500px;overflow-y:auto;">
                    <pre style="color:#E0E0E0;white-space:pre-wrap;font-size:0.92rem;line-height:1.6;margin:0;">{sar_text}</pre>
                </div>""", unsafe_allow_html=True)

                # PDF + TXT downloads
                dl1, dl2 = st.columns(2)
                case_id = result.get('case_id', 'SAR-REPORT')
                case_label = st.session_state.get('last_intake_case', {}).get('name',
                    st.session_state.get('last_intake_case', {}).get('sender_wallet', 'Entity'))
                with dl1:
                    pdf_bytes = generate_sar_pdf(sar_text, case_id=case_id, customer_name=case_label,
                                                 risk_level=r_level, risk_score=r_score)
                    st.download_button("Download SAR (.PDF)", data=pdf_bytes,
                                       file_name=f"SAR_{case_id}.pdf", mime="application/pdf",
                                       type="primary", use_container_width=True)
                with dl2:
                    st.download_button("Download SAR (.TXT)", data=sar_text,
                                       file_name=f"SAR_{case_id}.txt", type="secondary",
                                       use_container_width=True)

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
            
            dl1, dl2 = st.columns(2)
            with dl1:
                pdf_bytes = generate_sar_pdf(narrative.content, case_id=target, customer_name=case.customer_name,
                                             risk_level=safely_get_enum_name(case.risk_level), risk_score=case.risk_score or 0)
                st.download_button("Export SAR (.PDF)", data=pdf_bytes,
                                   file_name=f"SAR_{target}_{case.customer_name}.pdf", mime="application/pdf",
                                   type="primary", use_container_width=True)
            with dl2:
                st.download_button("Export SAR (.TXT)", narrative.content,
                                   file_name=f"SAR_{target}_{case.customer_name}.txt",
                                   type="secondary", use_container_width=True)
        else:
            st.error("SAR Generation sequence incomplete or not generated for this entity.")

def view_audit_trail():
    st.markdown('<h1 style="border-bottom: 2px solid var(--accent-orange); display:inline-block; padding-bottom:5px; margin-bottom:30px;">EXPLAINABILITY AND AUDIT</h1>', unsafe_allow_html=True)
    st.markdown("<p style='color: var(--text-muted);'>Immutable traceability between data ingestion, rule engine flags, and LLM reasoning.</p>", unsafe_allow_html=True)
    
    cases = get_all_cases()
    if not cases:
        return
        
    target = st.selectbox("Select Case", [c.case_id for c in cases], label_visibility="collapsed")
    
    if target:
        log = get_audit_log(target)
        if log:
            data = log.audit_data
            
            st.markdown("<h4>Rule Engine Triggers</h4>", unsafe_allow_html=True)
            st.markdown("<hr style='border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
            
            risk_assess = data.get('risk_assessment_trail', {})
            rules = risk_assess.get('rules_triggered_details', [])
            if isinstance(rules, list) and len(rules) > 0:
                for r in rules:
                    st.markdown(f"""
                    <div style="background: rgba(255,255,255,0.03); border-left: 4px solid var(--accent-orange); padding: 12px; margin-bottom: 10px; border-radius: 4px;">
                        <strong style="color:var(--text-white);">{r.get('rule_id')}</strong>: {r.get('rule_name')}<br>
                        <span style="color:#B0BEC5; font-size:0.85em;">Description: {r.get('explanation')}</span><br>
                        <span style="color:#FF9800; font-size:0.85em; font-weight:600;">Severity: {r.get('severity')}</span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.write("No rule breaches recorded.")

            # AI Generation info
            ai_trail = data.get('ai_generation_trail', {})
            model_info = ai_trail.get('model_details', {})
            if model_info:
                st.markdown("<h4>LLM Generation Details</h4>", unsafe_allow_html=True)
                st.markdown("<hr style='border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
                st.markdown(f"""
                <div style="background: rgba(255,255,255,0.03); border-left: 4px solid #00B0FF; padding: 12px; border-radius: 4px;">
                    <strong style="color:var(--text-white);">Model:</strong> {model_info.get('model_name', 'N/A')}<br>
                    <strong style="color:var(--text-white);">Source:</strong> {'Ollama LLM' if model_info.get('model_name') == 'llama3' else 'Template Fallback'}
                </div>
                """, unsafe_allow_html=True)

            st.markdown("### Audit Log")
            with st.expander("View Full JSON"):
                st.json(data)
        else:
            st.error("Audit log missing for this case.")

# ----------------- REVIEW PAGE -----------------
def view_review():
    st.markdown('<h1 style="border-bottom: 2px solid var(--accent-orange); display:inline-block; padding-bottom:5px; margin-bottom:30px;">SAR REVIEW WORKBENCH</h1>', unsafe_allow_html=True)
    st.markdown("<p style='color: var(--text-muted);'>Review, edit, and finalize SAR narratives before regulatory submission. Select a case generated from Case Intake.</p>", unsafe_allow_html=True)
    
    cases = get_all_cases()
    if not cases:
        st.warning("No cases available for review. Process a transaction from Case Intake first.")
        return
    
    # Case selector
    case_options = {f"{c.case_id} — {c.customer_name} ({safely_get_enum_name(c.risk_level)})": c.case_id for c in cases}
    selected_label = st.selectbox("Select Case for Review", list(case_options.keys()))
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

    # ---- 2-COLUMN LAYOUT: Editor + Actions ----
    current_content = narrative.content if narrative else "No SAR narrative has been generated for this case yet. Run the analysis pipeline from Case Intake first."

    col_editor, col_actions = st.columns([3, 1])
    
    # ---- EDITOR COLUMN ----
    with col_editor:
        st.markdown("### SAR Narrative Editor")
        st.caption("Review and edit the LLM-generated SAR narrative. Save to create a new version.")
        edited_narrative = st.text_area(
            "SAR Narrative",
            value=current_content,
            height=520,
            key=f"review_editor_{target_id}",
            label_visibility="collapsed"
        )
    
    # ---- ACTIONS COLUMN ----
    with col_actions:
        # Risk info panel
        score_val = case.risk_score or 0
        gauge_pct = score_val / 100
        st.markdown(f"""<div style="background:rgba(19,28,45,0.7);border:1px solid rgba(255,255,255,0.05);border-radius:12px;padding:18px;box-shadow:0 8px 32px rgba(0,0,0,0.3);margin-bottom:15px;">
            <div style="text-align:center;margin-bottom:10px;">
                <div style="color:#8E9BAE;font-size:0.8rem;text-transform:uppercase;letter-spacing:1px;">Risk Score</div>
                <div style="font-size:2rem;font-weight:800;color:{risk_color};margin:5px 0;">{score_val}</div>
                <div style="color:{risk_color};font-weight:600;font-size:0.85rem;">{risk_lvl}</div>
            </div>
        </div>""", unsafe_allow_html=True)

        # Triggered rules
        if audit and audit.audit_data:
            risk_trail = audit.audit_data.get('risk_assessment_trail', {})
            rules = risk_trail.get('rules_triggered_details', [])
            if isinstance(rules, list) and len(rules) > 0:
                st.markdown("**Triggered Rules**")
                for r in rules:
                    sev = r.get('severity', 'N/A')
                    sc = "#FF3D00" if sev in ['HIGH', 'CRITICAL'] else ("#FF9800" if sev == 'MEDIUM' else "#4CAF50")
                    st.markdown(f'<div style="background:rgba(255,255,255,0.03);border-left:3px solid {sc};padding:8px;margin-bottom:6px;border-radius:4px;font-size:0.8rem;"><strong style="color:#fff;">{r.get("rule_id")}</strong>: {r.get("rule_name")}<br><span style="color:{sc};font-size:0.75rem;">Severity: {sev}</span></div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("**Actions**")

        # Save button
        if st.button("Save Changes", type="primary", use_container_width=True, key="save_review"):
            if not narrative:
                st.warning("No narrative exists yet for this case.")
            else:
                # Always save if user clicks save (comparison can fail due to whitespace)
                result = save_narrative(
                    case_id=target_id,
                    content=edited_narrative,
                    metadata={'edited_by': st.session_state.username, 'edit_time': datetime.now().isoformat()},
                    created_by=st.session_state.username or 'Analyst',
                    generation_method='manual_edit'
                )
                if result:
                    st.success(f"Saved version {result}.")
                    st.rerun()
                else:
                    st.error("Save failed.")

        # Download buttons
        if narrative:
            pdf_bytes = generate_sar_pdf(edited_narrative, case_id=target_id, customer_name=case.customer_name,
                                         risk_level=risk_lvl, risk_score=case.risk_score or 0)
            st.download_button(
                "Download SAR (.PDF)",
                data=pdf_bytes,
                file_name=f"SAR_{target_id}_{case.customer_name}.pdf",
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )
            st.download_button(
                "Download SAR (.TXT)",
                edited_narrative,
                file_name=f"SAR_{target_id}_{case.customer_name}.txt",
                type="secondary",
                use_container_width=True
            )

        # Mark reviewed
        if st.button("Mark as Reviewed", type="secondary", use_container_width=True, key="mark_reviewed"):
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
    elif view == "Case Intake":
        view_case_management()
    elif view == "CSV Intake":
        view_csv_intake()
    elif view == "Case Repository":
        view_case_repository()
    elif view == "SAR Reporting":
        view_sar_reporting()
    elif view == "Review":
        view_review()
    elif view == "Audit Trail":
        view_audit_trail()
