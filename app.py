"""Main entry point for the Iran & Bushehr foreign trade dashboard.

Temporary deploy probe: shows a safe, read-only version fingerprint in the
sidebar so the live Streamlit Cloud instance can be matched to the files
actually present in its deployed source directory.
"""
from pathlib import Path
import re

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
    st.Page("pages/trade_explorer.py", title="کاوشگر تجارت", icon="🔎"),
]

pg = st.navigation(pages)

# Read only short, nonsecret facts about the files in THIS deployed directory.
# Do not display local paths, environment variables, secrets, or dataset info.
_PROBE_ID = "trade-dashboard-check-20261121-A"
_BASE = Path(__file__).resolve().parent


def _source_text(relative_path):
    try:
        return (_BASE / relative_path).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return ""


_utils_text = _source_text("page_utils.py")
_customs_text = _source_text("pages/customs.py")
_fa_text = _source_text("persian_display.py")
_match = re.search(
    r'''(?m)^METRIC_CARD_RENDERER\s*=\s*["']([^"']+)["']''', _utils_text
)
_renderer_version = _match.group(1) if _match else "قدیمی یا نامشخص"
_fa_ready = bool(_fa_text) and "def persianize_figure" in _fa_text
_customs_ready = "persianize_figure" in _customs_text
_html_ready = "container.html(content)" in _utils_text

with st.sidebar.expander("🔎 بررسی نسخه نصب‌شده", expanded=True):
    st.caption("شناسه انتشار: " + _PROBE_ID)
    st.caption("نسخه کارت‌ها: " + _renderer_version)
    st.caption("نمایش HTML کارت‌ها: " + ("✅ جدید" if _html_ready else "❌ قدیمی"))
    st.caption("فایل فارسی‌ساز: " + ("✅ موجود" if _fa_ready else "❌ موجود نیست"))
    st.caption("صفحه گمرک‌ها: " + ("✅ اصلاح‌شده" if _customs_ready else "❌ قدیمی"))

pg.run()
