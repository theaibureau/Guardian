import io, os, csv
from datetime import datetime, date
from typing import List

import streamlit as st
from PIL import Image
from streamlit_drawable_canvas import st_canvas
from sqlalchemy.orm import Session
from sqlalchemy import func
from dotenv import load_dotenv

from db import init_db, SessionLocal
from models import User, Inspection, InspectionItem
from auth import (
    create_user_and_send_confirmation, confirm_email, authenticate,
    toggle_subscription, set_company_branding
)
from report import generate_inspection_pdf

# ===================== ⚙️ Setup =====================
load_dotenv()
APP_NAME = os.getenv("APP_NAME", "The Guardian – Safety & Compliance")

# 🛡️ Must be FIRST Streamlit command
st.set_page_config(page_title=APP_NAME, page_icon="🛡️", layout="wide")

# ===================== 🎨 Inject CSS =====================
def inject_custom_css():
    st.markdown("""
    <style>
        .stApp { background: #f7f9fc; font-family: "Inter", "Segoe UI", Roboto, sans-serif; }
        section[data-testid="stSidebar"] { background-color: #1a1d2d; padding: 1rem; }
        section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] p, 
        section[data-testid="stSidebar"] label { color: #f0f0f0 !important; }
        h1, h2, h3 { color: #0f172a; font-weight: 600; }
        .stTextInput > div > div > input, .stTextArea textarea, .stDateInput input {
            border-radius: 10px; border: 1px solid #d1d5db; padding: 10px;
        }
        [data-testid="stFileUploader"] {
            border: 2px dashed #6366f1; border-radius: 12px; background: #eef2ff;
        }
        button[kind="primary"] {
            background: linear-gradient(90deg, #6366f1, #3b82f6); color: white;
            border-radius: 10px; font-weight: 600; transition: 0.2s ease;
        }
        button[kind="primary"]:hover { transform: scale(1.02); 
            background: linear-gradient(90deg, #4f46e5, #2563eb); }
        button[kind="secondary"] { border-radius: 10px; background: #f1f5f9; color: #111827; }
        .stForm { background: white; padding: 2rem; border-radius: 16px;
                  box-shadow: 0 6px 16px rgba(0,0,0,0.08); }
        canvas { border: 2px solid #d1d5db !important; border-radius: 12px; }
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# ===================== 🔑 DB Helpers =====================
def get_db() -> Session:
    return SessionLocal()

def is_admin() -> bool:
    return st.session_state.get('user', {}).get('role') == 'admin'

def load_checklist() -> List[dict]:
    rows = []
    with open("checklist.csv", "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r: rows.append(row)
    return rows

# ===================== 📊 Pages =====================
def page_dashboard():
    st.header("📊 Inspector Dashboard")
    with get_db() as db:
        uid = st.session_state['user']['id']

        st.subheader("Past Inspections")
        past = db.query(Inspection).filter(
            Inspection.inspector_id == uid
        ).order_by(Inspection.created_at.desc()).all()

        if not past:
            st.info("No inspections yet.")
        else:
            for insp in past:
                with st.expander(f"✅ #{insp.id} – {insp.building_name} – {insp.created_at.date()}"):
                    st.write(f"📍 Address: {insp.building_address or '-'}")
                    st.write(f"📝 Notes: {insp.notes or '-'}")
                    if insp.pdf_blob:
                        st.download_button("⬇️ Download PDF", data=insp.pdf_blob,
                            file_name=f"inspection_{insp.id}.pdf", mime="application/pdf")

        st.subheader("Upcoming Inspections")
        upcoming = db.query(Inspection).filter(
            Inspection.inspector_id == uid, Inspection.scheduled_for != None
        ).order_by(Inspection.scheduled_for.asc()).all()
        if not upcoming:
            st.info("No upcoming inspections scheduled.")
        else:
            for insp in upcoming:
                st.write(f"📅 {insp.scheduled_for} – {insp.building_name}")

def page_new_inspection():
    st.title("🛡️ New Inspection")
    st.caption("Fill in the inspection details below and upload any required documents/images.")

    with st.form("new_insp_form"):
        st.markdown("### 🏢 Building Information")
        building_name = st.text_input("Building Name *")
        building_address = st.text_input("Address")
        scheduled_for = st.date_input("Schedule for (optional)")
        notes = st.text_area("General Notes")

        st.markdown("### 🎨 Branding Assets")
        col1, col2 = st.columns(2)
        with col1: logo_file = st.file_uploader("Upload Report Logo", type=["png","jpg","jpeg"])
        with col2: hero_file = st.file_uploader("Upload Hero Image", type=["png","jpg","jpeg"])

        st.markdown("### ✍️ Inspector Signature")
        canvas = st_canvas(height=150, width=600, background_color="#FFFFFF",
                           stroke_color="#000000", stroke_width=2,
                           drawing_mode="freedraw", key="sig")

        submitted = st.form_submit_button("🚀 Create Inspection", use_container_width=True)
        if submitted:
            if not building_name:
                st.error("Building name is required"); return
            st.success(f"Inspection for **{building_name}** created! 🎉 (checklist page coming next…)")

def page_profile():
    st.header("👤 Profile & Branding")
    with get_db() as db:
        user = db.query(User).filter(User.id == st.session_state['user']['id']).first()
        st.write(f"**Username:** {user.username}")
        st.write(f"**Email:** {user.email}")
        st.write(f"**Mobile:** {user.mobile or '-'}")
        st.write(f"**Subscription:** {'Subscribed' if user.is_subscribed else 'Free'}")

# ===================== 🚀 Main =====================
def sidebar_nav():
    st.sidebar.title("Navigation")
    if 'user' in st.session_state and st.session_state['user']:
        st.sidebar.markdown(f"👤 **{st.session_state['user']['full_name']}**")
        choice = st.sidebar.radio("Go to", [
            "Dashboard", "New Inspection", "Profile & Branding", "Logout"
        ], index=0)
        return choice
    return None

def main():
    init_db()

    # 🔑 BYPASS LOGIN: inject demo user
    if 'user' not in st.session_state or st.session_state['user'] is None:
        st.session_state['user'] = {
            'id': 1, 'username': 'demo',
            'full_name': 'Demo Inspector',
            'role': 'inspector',
        }

    nav = sidebar_nav() or "Dashboard"
    if nav == "Dashboard": page_dashboard()
    elif nav == "New Inspection": page_new_inspection()
    elif nav == "Profile & Branding": page_profile()
    elif nav == "Logout":
        st.session_state.clear(); st.rerun()

if __name__ == "__main__":
    main()
