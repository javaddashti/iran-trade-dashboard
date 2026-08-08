
import streamlit as st

def apply_global_style():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Lalezar&family=Vazirmatn:wght@300;400;500;600;700;800&display=swap');

        :root {
            --font-main: "Vazirmatn", "Tahoma", "Arial", sans-serif;
            --font-title: "Lalezar", "Vazirmatn", "Tahoma", sans-serif;
            --ink: #172033;
            --muted: #64748b;
            --line: #e7ebef;
            --panel: #ffffff;
            --panel-soft: #f6f9fb;
            --brand: #1f6f8b;
            --brand-dark: #173b56;
        }

        /* ---------- Global RTL ---------- */
        html,
        body,
        .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"],
        [data-testid="stMainBlockContainer"] {
            direction: rtl !important;
            text-align: right !important;
            font-family: var(--font-main) !important;
        }

        * {
            font-family: var(--font-main);
        }

        .block-container {
            max-width: 1500px;
            padding-top: 1.25rem;
            padding-bottom: 3rem;
            direction: rtl !important;
            text-align: right !important;
        }

        /* ---------- Sidebar / navigation ---------- */
        section[data-testid="stSidebar"] {
            direction: rtl !important;
        }

        section[data-testid="stSidebar"] > div {
            direction: rtl !important;
        }

        section[data-testid="stSidebar"] * {
            direction: rtl !important;
            text-align: right !important;
        }

        [data-testid="stSidebarNav"] ul {
            direction: rtl !important;
        }

        [data-testid="stSidebarNav"] a {
            direction: rtl !important;
            text-align: right !important;
            justify-content: flex-start !important;
        }

        /* ---------- Standard text ---------- */
        h1, h2, h3, h4, h5, h6,
        p, label, span,
        [data-testid="stCaptionContainer"],
        [data-testid="stMarkdownContainer"] {
            direction: rtl !important;
            text-align: right !important;
        }

        h1, h2, h3, h4 {
            color: var(--ink);
        }

        /* ---------- Hero ---------- */
        .trade-hero {
            direction: rtl !important;
            text-align: right !important;
            border: 1px solid var(--line);
            border-radius: 22px;
            padding: 28px 32px 24px 32px;
            margin: 0 0 22px 0;
            background: linear-gradient(135deg, #f8fbfc 0%, #eef6f8 100%);
            box-shadow: 0 2px 10px rgba(15, 23, 42, 0.025);
        }

        .trade-hero-title {
            direction: rtl !important;
            text-align: right !important;
            font-family: var(--font-title) !important;
            font-size: 2.35rem;
            line-height: 1.35;
            font-weight: 400;
            color: var(--brand-dark);
            margin: 0;
        }

        .trade-hero-subtitle {
            direction: rtl !important;
            text-align: right !important;
            font-family: var(--font-main) !important;
            font-size: 1rem;
            line-height: 1.9;
            color: var(--muted);
            margin-top: 7px;
        }

        /* ---------- Section headings ---------- */
        .section-kicker {
            direction: rtl !important;
            text-align: right !important;
            font-size: 0.9rem;
            font-weight: 500;
            color: var(--muted);
            margin: 0 0 3px 0;
        }

        .section-title {
            direction: rtl !important;
            text-align: right !important;
            font-family: var(--font-main) !important;
            font-size: 1.45rem;
            line-height: 1.7;
            font-weight: 800;
            color: var(--ink);
            margin: 0 0 12px 0;
        }

        /* ---------- Metrics ---------- */
        div[data-testid="stMetric"] {
            direction: rtl !important;
            text-align: right !important;
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 17px;
            padding: 15px 17px;
            min-height: 126px;
            box-shadow: 0 2px 8px rgba(15, 23, 42, 0.025);
        }

        div[data-testid="stMetric"] > div {
            direction: rtl !important;
            text-align: right !important;
        }

        div[data-testid="stMetricLabel"],
        div[data-testid="stMetricValue"],
        div[data-testid="stMetricDelta"] {
            direction: rtl !important;
            text-align: right !important;
            justify-content: flex-start !important;
        }

        div[data-testid="stMetricLabel"] p {
            font-size: 0.92rem !important;
            font-weight: 600 !important;
        }

        div[data-testid="stMetricValue"] {
            font-size: 1.5rem !important;
            font-weight: 800 !important;
            white-space: normal !important;
            overflow: visible !important;
        }

        /* ---------- Controls ---------- */
        div[data-testid="stSelectbox"],
        div[data-testid="stMultiSelect"],
        div[data-testid="stRadio"],
        div[data-testid="stSlider"] {
            direction: rtl !important;
            text-align: right !important;
        }

        div[data-testid="stSelectbox"] label,
        div[data-testid="stMultiSelect"] label,
        div[data-testid="stRadio"] label,
        div[data-testid="stSlider"] label {
            direction: rtl !important;
            text-align: right !important;
            width: 100%;
            font-weight: 600;
        }

        /* Keep slider geometry natural while its labels remain RTL */
        div[data-testid="stSlider"] [data-baseweb="slider"] {
            direction: ltr !important;
        }

        div[role="radiogroup"] {
            direction: rtl !important;
            justify-content: flex-start !important;
        }

        /* ---------- Tabs ---------- */
        div[data-baseweb="tab-list"] {
            direction: rtl !important;
            justify-content: flex-start !important;
            gap: 0.35rem;
        }

        button[data-baseweb="tab"] {
            direction: rtl !important;
            text-align: right !important;
            font-family: var(--font-main) !important;
            font-weight: 600;
        }

        /* ---------- Alerts / captions ---------- */
        div[data-testid="stAlert"] {
            direction: rtl !important;
            text-align: right !important;
        }

        div[data-testid="stAlert"] * {
            direction: rtl !important;
            text-align: right !important;
        }

        /* ---------- Plotly cards ---------- */
        div[data-testid="stPlotlyChart"] {
            direction: rtl !important;
            border: 1px solid #edf0f2;
            border-radius: 17px;
            padding: 7px;
            background: white;
        }

        /* ---------- Dividers ---------- */
        hr {
            margin: 1.6rem 0;
            border-color: var(--line);
        }

        /* ---------- Mobile ---------- */
        @media (max-width: 900px) {
            .trade-hero-title {
                font-size: 1.85rem;
            }

            .trade-hero {
                padding: 22px 20px;
            }

            .block-container {
                padding-left: 0.8rem;
                padding-right: 0.8rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
