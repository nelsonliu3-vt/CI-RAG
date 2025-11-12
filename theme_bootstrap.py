"""
Graphite-Sand Theme Bootstrap
Professional warm theme with token-based CSS for CI-RAG
"""

import streamlit as st


def boot_graphite_sand():
    """
    Idempotent theme bootstrap for any Streamlit page.
    Applies Graphite-Sand design system with warm colors and professional polish.
    """
    # Avoid double injection on reruns/multipage apps
    if st.session_state.get("_gs_booted"):
        return

    # Set page config (must be first Streamlit command)
    try:
        st.set_page_config(
            page_title="CI-RAG - Competitive Intelligence",
            page_icon="🧭",
            layout="wide",
            initial_sidebar_state="expanded"
        )
    except:
        # Already configured (multipage app)
        pass

    # Inject Graphite-Sand CSS
    st.markdown("""
    <style>
    /* ============================================================
       GRAPHITE-SAND DESIGN TOKENS
       ============================================================ */
    :root {
      /* Colors */
      --bg: #F4EEE4;              /* warm paper beige */
      --surface: #FEFDFB;         /* ivory card background */
      --text: #1E1C1A;            /* warm black text */
      --muted: #746C64;           /* brown-grey labels */
      --border: #DCD5CC;          /* beige divider */
      --accent: #3C3A36;          /* warm graphite (buttons/headings) */
      --accent-hover: #4A4845;    /* darker graphite on hover */

      /* Semantic colors */
      --success-bg: #E7F2EC;      /* soft mint green */
      --success-fg: #1A7F53;      /* emerald text */
      --warning-bg: #FFF4E6;      /* soft amber */
      --warning-fg: #B45309;      /* burnt orange */
      --error-bg: #FDECEC;        /* soft red */
      --error-fg: #B91C1C;        /* crimson */
      --info-bg: #EFF6FF;         /* soft blue */
      --info-fg: #1E40AF;         /* navy blue */

      /* Chip colors */
      --chip-neutral: #EEE6DA;    /* sand-tinted */
      --chip-ok-bg: var(--success-bg);
      --chip-ok-fg: var(--success-fg);
      --chip-warn-bg: var(--warning-bg);
      --chip-warn-fg: var(--warning-fg);

      /* Spacing & Layout */
      --radius: 16px;             /* rounded corners */
      --shadow-sm: 0 1px 0 rgba(255,255,255,.6) inset, 0 2px 10px rgba(60,58,54,.12);
      --shadow-md: 0 1px 0 rgba(255,255,255,.6) inset, 0 4px 20px rgba(60,58,54,.18);
    }

    /* ============================================================
       BASE STYLES
       ============================================================ */
    html, body, [class*="css"] {
      background: var(--bg) !important;
      color: var(--text);
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
      font-size: 17px;
      line-height: 1.7;
      font-variant-numeric: tabular-nums;
    }

    /* Header chrome */
    header[data-testid="stHeader"] {
      background: linear-gradient(180deg, #FCFAF8 0%, #F4EEE4 100%) !important;
      border-bottom: 1px solid var(--border);
    }

    /* Hide Streamlit branding */
    footer {
      visibility: hidden;
    }
    #MainMenu {
      visibility: hidden;
    }

    /* Main content area */
    .main .block-container {
      padding-top: 2rem;
      padding-bottom: 3rem;
      max-width: 1400px;
    }

    /* ============================================================
       SIDEBAR STYLING
       ============================================================ */
    section[data-testid="stSidebar"] {
      background: var(--surface) !important;
      border-right: 1px solid var(--border);
    }

    section[data-testid="stSidebar"] > div {
      background: var(--surface);
    }

    /* ============================================================
       TABS STYLING
       ============================================================ */
    div[data-baseweb="tab-list"] {
      gap: 6px;
      border-bottom: 1px solid var(--border);
      background: transparent;
    }

    div[data-baseweb="tab"] {
      background: #FAF8F4;
      border: 1px solid var(--border);
      border-bottom-color: transparent;
      border-top-left-radius: 10px;
      border-top-right-radius: 10px;
      color: var(--muted);
      padding: 0.5rem 1.2rem;
      font-weight: 600;
    }

    div[aria-selected="true"][data-baseweb="tab"] {
      background: var(--surface);
      color: var(--accent);
      border-color: var(--border);
      border-bottom-color: var(--surface);
    }

    div[data-baseweb="tab-panel"] {
      border: 1px solid var(--border);
      border-top: none;
      background: var(--surface);
      padding: 1.5rem;
      border-radius: 0 10px 10px 10px;
    }

    /* ============================================================
       BUTTONS
       ============================================================ */
    div.stButton > button {
      display: inline-block;
      padding: 0.8rem 1.3rem;
      border-radius: var(--radius);
      border: 1px solid var(--accent);
      background: var(--accent);
      color: #FAFAF8;
      text-decoration: none;
      font-weight: 700;
      letter-spacing: -0.012em;
      transition: all 0.15s ease-in;
      box-shadow: var(--shadow-sm);
    }

    div.stButton > button:hover {
      background: var(--accent-hover);
      box-shadow: var(--shadow-md);
      transform: translateY(-1px);
    }

    /* Secondary button */
    div.stButton > button[kind="secondary"] {
      background: transparent;
      color: var(--accent);
      border-color: var(--accent);
      box-shadow: none;
    }

    div.stButton > button[kind="secondary"]:hover {
      background: #F4EEE4;
    }

    /* ============================================================
       METRICS & STATS
       ============================================================ */
    div[data-testid="stMetric"] {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1.2rem;
      box-shadow: var(--shadow-sm);
    }

    div[data-testid="stMetric"] label {
      color: var(--muted);
      font-size: 14px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
      color: var(--accent);
      font-size: 28px;
      font-weight: 800;
    }

    /* ============================================================
       INPUT FIELDS
       ============================================================ */
    input, textarea, select {
      background: var(--surface) !important;
      border: 1px solid var(--border) !important;
      border-radius: var(--radius) !important;
      color: var(--text) !important;
      padding: 0.8rem !important;
    }

    input:focus, textarea:focus, select:focus {
      border-color: var(--accent) !important;
      box-shadow: 0 0 0 2px rgba(60, 58, 54, 0.1) !important;
    }

    /* ============================================================
       FILE UPLOADER
       ============================================================ */
    div[data-testid="stFileUploader"] {
      background: var(--surface);
      border: 1px dashed var(--border);
      border-radius: var(--radius);
      padding: 2rem;
      text-align: center;
    }

    div[data-testid="stFileUploader"]:hover {
      border-color: var(--accent);
      background: #FAF8F4;
    }

    /* ============================================================
       ALERTS & MESSAGES
       ============================================================ */
    div.stSuccess {
      background: var(--success-bg) !important;
      border: 1px solid var(--success-fg) !important;
      border-radius: var(--radius);
      color: var(--success-fg) !important;
    }

    div.stWarning {
      background: var(--warning-bg) !important;
      border: 1px solid var(--warning-fg) !important;
      border-radius: var(--radius);
      color: var(--warning-fg) !important;
    }

    div.stError {
      background: var(--error-bg) !important;
      border: 1px solid var(--error-fg) !important;
      border-radius: var(--radius);
      color: var(--error-fg) !important;
    }

    div.stInfo {
      background: var(--info-bg) !important;
      border: 1px solid var(--info-fg) !important;
      border-radius: var(--radius);
      color: var(--info-fg) !important;
    }

    /* ============================================================
       EXPANDERS
       ============================================================ */
    div[data-testid="stExpander"] {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      margin-bottom: 0.8rem;
    }

    div[data-testid="stExpander"] summary {
      background: #FAF8F4;
      border-radius: var(--radius);
      padding: 1rem;
      font-weight: 600;
      color: var(--accent);
    }

    div[data-testid="stExpander"] summary:hover {
      background: #F4EEE4;
    }

    /* ============================================================
       PROGRESS BAR
       ============================================================ */
    div.stProgress > div > div {
      background: var(--success-bg);
      border-radius: 999px;
    }

    div.stProgress > div > div > div {
      background: var(--success-fg);
      border-radius: 999px;
    }

    /* ============================================================
       TEXT STYLING
       ============================================================ */
    h1, h2, h3, h4, h5, h6 {
      color: var(--accent);
      font-weight: 800;
      letter-spacing: -0.02em;
    }

    h1 {
      font-size: 2.5rem;
      margin-bottom: 0.5rem;
    }

    h2 {
      font-size: 2rem;
      margin-top: 2rem;
      margin-bottom: 1rem;
    }

    h3 {
      font-size: 1.5rem;
      margin-top: 1.5rem;
      margin-bottom: 0.8rem;
    }

    p {
      color: var(--text);
      line-height: 1.7;
    }

    code {
      background: #F4EEE4;
      color: var(--accent);
      padding: 0.2rem 0.4rem;
      border-radius: 4px;
      font-family: 'SF Mono', 'Consolas', monospace;
      font-size: 0.9em;
    }

    pre {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1rem;
      overflow-x: auto;
    }

    /* ============================================================
       CUSTOM COMPONENTS (for use with st.markdown)
       ============================================================ */

    /* Card container */
    .gs-card {
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      padding: 1.5rem;
      box-shadow: var(--shadow-sm);
      margin-bottom: 1rem;
    }

    /* Chips / badges */
    .gs-chip {
      display: inline-block;
      padding: 0.35rem 0.75rem;
      border-radius: 999px;
      border: 1px solid var(--border);
      color: var(--muted);
      font-size: 14px;
      background: #FAF8F4;
      font-weight: 600;
      margin-right: 0.4rem;
    }

    .gs-chip.impact {
      background: var(--chip-neutral);
      color: var(--text);
    }

    .gs-chip.ok {
      background: var(--chip-ok-bg);
      color: var(--chip-ok-fg);
      border-color: var(--chip-ok-fg);
    }

    .gs-chip.warn {
      background: var(--chip-warn-bg);
      color: var(--chip-warn-fg);
      border-color: var(--chip-warn-fg);
    }

    .gs-chip.bad {
      background: var(--error-bg);
      color: var(--error-fg);
      border-color: var(--error-fg);
    }

    /* Drop zone styling */
    .gs-drop {
      border: 1px dashed var(--border);
      border-radius: var(--radius);
      padding: 2rem;
      text-align: center;
      color: var(--muted);
      background: var(--surface);
    }

    .gs-drop:hover {
      border-color: var(--accent);
      background: #FAF8F4;
    }

    /* Button link (for use with <a> tags) */
    .gs-btn {
      display: inline-block;
      padding: 0.8rem 1.3rem;
      border-radius: var(--radius);
      border: 1px solid var(--accent);
      background: var(--accent);
      color: #FAFAF8;
      text-decoration: none;
      font-weight: 700;
      letter-spacing: -0.012em;
      transition: all 0.15s ease-in;
      box-shadow: var(--shadow-sm);
    }

    .gs-btn:hover {
      background: var(--accent-hover);
      box-shadow: var(--shadow-md);
      transform: translateY(-1px);
    }

    .gs-btn.ghost {
      background: transparent;
      color: var(--accent);
      border-color: var(--accent);
      box-shadow: none;
    }

    .gs-btn.ghost:hover {
      background: #F4EEE4;
    }

    /* Divider */
    hr {
      border: none;
      border-top: 1px dashed var(--border);
      margin: 2rem 0;
    }

    /* Caption text */
    .caption {
      color: var(--muted);
      font-size: 14px;
      line-height: 1.5;
    }

    /* ============================================================
       UTILITY CLASSES
       ============================================================ */
    .text-muted {
      color: var(--muted);
    }

    .text-accent {
      color: var(--accent);
    }

    .font-bold {
      font-weight: 700;
    }

    .font-extrabold {
      font-weight: 800;
    }

    .mt-1 { margin-top: 0.5rem; }
    .mt-2 { margin-top: 1rem; }
    .mt-3 { margin-top: 1.5rem; }
    .mb-1 { margin-bottom: 0.5rem; }
    .mb-2 { margin-bottom: 1rem; }
    .mb-3 { margin-bottom: 1.5rem; }

    </style>
    """, unsafe_allow_html=True)

    # Mark as booted
    st.session_state["_gs_booted"] = True
