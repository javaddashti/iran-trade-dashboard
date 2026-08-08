
import streamlit as st

st.set_page_config(
    page_title="داشبورد تجارت خارجی ایران و بوشهر",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
)

from ui_style import apply_global_style
apply_global_style()

pages = [
    st.Page("pages/overview.py", title="نمای کلی", icon="📊", default=True),
    st.Page("pages/commodities.py", title="کالاها و تعرفه‌ها", icon="🧩"),
    st.Page("pages/partners.py", title="شرکای تجاری", icon="🌍"),
    st.Page("pages/customs.py", title="گمرک‌ها و بنادر", icon="⚓"),
    st.Page("pages/bushehr_analysis.py", title="تحلیل بوشهر", icon="📍"),
]

pg = st.navigation(pages)
pg.run()
