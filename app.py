import io, os, csv
from datetime import datetime, date
from typing import List

import streamlit as st
from PIL import Image
from streamlit_drawable_canvas import st_canvas
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from db import init_db, SessionLocal
from models import User, Inspection, InspectionItem
from auth import (
    create_user_and_send_confirmation, confirm_email, authenticate,
    toggle_subscription, set_company_branding
)
from report import generate_inspection_pdf

# ===================== 🎨 Inject CSS =====================
def inject_custom_css():
    st.markdown("""
    <style>
        .stApp {
            background: #f7f9fc;
            font-family: "Inter", "Segoe UI", Roboto, sans-serif;
        }
        section[data-testid="stSidebar"] {
            background-color: #1a1d2d;
            padding: 1rem;
        }
        section[data-testid="stSidebar"] h1, 
        section[data-testid="stSidebar"] p, 
        section[data-testid="stSidebar"] label {
            color: #f0f0f0 !important;
        }
        h1, h2, h3 {
            color: #0f172a;
            font-weight: 600;
        }
        .stTextInput > div > div > input, 
        .stTextArea textarea, 
        .stDateInput input {
            border-radius: 10px;
            border: 1px solid #d1d5db;
            padding: 10px;
        }
        [data-testid="stFileUploader"] {
            border: 2px dashed #6366f1;
            border-radius: 12px;
            background: #eef2ff;
        }
        button[kind="primary"] {
            background: linear-gradient(90deg, #6366f1, #3b82f6);
            color: white;
            border-radius: 10px;
            font-weight: 600;
        }
        button[kind="secondary"] {
            border-radius: 10px;
            background: #f1f5f9;
            color: #111827;
        }
        .stForm {
            background: white;
            padding: 2rem;
            border-radius: 16px;
            box-shadow: 0 6px 16px rgba(0,0,0,0.08);
        }
        canvas {
            border: 2px solid #d1d5db !important;
            border-radius: 12px;
        }
    </style>
    """, unsafe_allow_html=True)

# ========================================================
APP_NAME = os.getenv("APP_NAME", "The Guardian – Safety & Compliance")

# Must be first Streamlit call
st.set_page_config(page_title=APP_NAME, page_icon="🛡️", layout="wide")
inject_custom_css()
load_dotenv()

# ========================================================
def get_db() -> Session:
    return SessionLocal()

def is_admin() -> bool:
    return st.session_state.get('user', {}).get('role') == 'admin'

def load_checklist() -> List[dict]:
    rows = []
    with open("checklist.csv", "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)
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
                    st.write(f"📍 {insp.building_address or '-'}")
                    st.write(f"📝 {insp.notes or '-'}")
                    if insp.pdf_blob:
                        st.download_button("⬇️ Download PDF", data=insp.pdf_blob,
                                           file_name=f"inspection_{insp.id}.pdf",
                                           mime="application/pdf")

        st.subheader("Upcoming Inspections")
        upcoming = db.query(Inspection).filter(
            Inspection.inspector_id == uid,
            Inspection.scheduled_for != None
        ).order_by(Inspection.scheduled_for.asc()).all()
        if not upcoming:
            st.info("No upcoming inspections scheduled.")
        else:
            for insp in upcoming:
                st.write(f"📅 {insp.scheduled_for} – {insp.building_name}")

def page_new_inspection():
    st.title("🛡️ New Inspection")
    with st.form("new_insp_form"):
        building_name = st.text_input("Building Name *")
        building_address = st.text_input("Address")
        scheduled_for = st.date_input("Schedule for (optional)")
        notes = st.text_area("General Notes")

        col1, col2 = st.columns(2)
        with col1:
            logo_file = st.file_uploader("Upload Report Logo", type=["png","jpg","jpeg"])
        with col2:
            hero_file = st.file_uploader("Upload Hero Image", type=["png","jpg","jpeg"])

        st.markdown("### ✍️ Inspector Signature")
        canvas = st_canvas(height=150, width=600, background_color="#FFFFFF",
                           stroke_color="#000000", stroke_width=2, drawing_mode="freedraw", key="sig")

        submitted = st.form_submit_button("🚀 Create Inspection", use_container_width=True)
        if submitted:
            if not building_name:
                st.error("Building name is required")
                return

            def file_to_bytes(f): return f.read() if f else None
            sig_bytes = None
            if canvas and canvas.image_data is not None:
                try:
                    import numpy as np
                    img = Image.fromarray((canvas.image_data[:, :, :3]).astype("uint8"))
                    buf = io.BytesIO(); img.save(buf, format="PNG")
                    sig_bytes = buf.getvalue()
                except Exception: pass

            with get_db() as db:
                insp = Inspection(
                    building_name=building_name,
                    building_address=building_address or None,
                    scheduled_for=datetime.combine(scheduled_for, datetime.min.time()) if isinstance(scheduled_for, date) else None,
                    inspector_id=st.session_state['user']['id'],
                    logo_image=file_to_bytes(logo_file),
                    hero_image=file_to_bytes(hero_file),
                    signature_image=sig_bytes,
                    notes=notes or None,
                )
                db.add(insp); db.commit(); db.refresh(insp)
                for row in load_checklist():
                    item = InspectionItem(
                        inspection_id=insp.id,
                        question_en=row.get("EnglishQuestion", ""),
                        question_ar=row.get("ArabicQuestion", ""),
                        status="Pending"
                    )
                    db.add(item)
                db.commit()
                st.success(f"Inspection #{insp.id} created. Proceed to checklist 👉")
                st.session_state['current_insp_id'] = insp.id

    cur_id = st.session_state.get('current_insp_id')
    if cur_id:
        with get_db() as db:
            insp = db.query(Inspection).filter(Inspection.id == cur_id).first()
            if insp:
                st.subheader(f"Checklist – {insp.building_name}")
                items = db.query(InspectionItem).filter(InspectionItem.inspection_id == insp.id).all()
                for it in items:
                    with st.expander(it.question_en):
                        it.status = st.selectbox("Status", ["Compliant","Non-Compliant","Pending"],
                                                 index=["Compliant","Non-Compliant","Pending"].index(it.status),
                                                 key=f"st_{it.id}")
                        it.observation_text = st.text_area("Observation", value=it.observation_text or "", key=f"obs_{it.id}")
                        it.code_ref = st.text_input("NFPA/UAE Code reference", value=it.code_ref or "", key=f"code_{it.id}")
                        up = st.file_uploader("Photo (optional)", type=["png","jpg","jpeg"], key=f"ph_{it.id}")
                        if up: it.photo = up.read()
                        if st.button("Save item", key=f"sv_{it.id}"):
                            db.commit(); st.success("Saved ✅")
                if st.button("📄 Export PDF", type="primary"):
                    items = db.query(InspectionItem).filter(InspectionItem.inspection_id == insp.id).all()
                    user = db.query(User).filter(User.id == insp.inspector_id).first()
                    pdf_bytes = generate_inspection_pdf(insp=insp, items=items, user=user)
                    insp.pdf_blob = pdf_bytes; insp.completed_at = datetime.utcnow()
                    db.commit()
                    st.download_button("⬇️ Download PDF", data=pdf_bytes,
                                       file_name=f"inspection_{insp.id}.pdf", mime="application/pdf")

def page_profile():
    st.header("👤 Profile & Branding")
    with get_db() as db:
        user = db.query(User).filter(User.id == st.session_state['user']['id']).first()
        st.write(f"**Username:** {user.username}")
        st.write(f"**Email:** {user.email}")
        st.write(f"**Mobile:** {user.mobile or '-'}")
        st.write(f"**Subscription:** {'Subscribed' if user.is_subscribed else 'Free'}")
        if user.is_subscribed:
            logo = st.file_uploader("Upload Company Logo", type=["png","jpg","jpeg"])
            info = st.text_area("Company Info (footer)")
            if st.button("💾 Save Branding"):
                set_company_branding(db, user.id, company_info=info or None,
                                     company_logo_bytes=logo.read() if logo else None)
                st.success("Branding saved ✅")

def page_admin_users():
    if not is_admin():
        st.error("Admins only."); return
    st.header("👮 Admin – Users")
    with get_db() as db:
        users = db.query(User).order_by(User.created_at.desc()).all()
        for u in users:
            with st.expander(f"{u.full_name} (@{u.username}) – {u.role} [{u.status}] – {'Subscribed' if u.is_subscribed else 'Free'}"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button(("Disable" if u.status == "active" else "Activate"), key=f"status_{u.id}"):
                        u.status = "active" if u.status != "active" else "disabled"; db.commit(); st.rerun()
                with col2:
                    if st.button("Make Subscribed" if not u.is_subscribed else "Make Free", key=f"sub_{u.id}"):
                        toggle_subscription(db, u.id, not u.is_subscribed); st.rerun()
                with col3:
                    st.write(f"📧 {u.email}")

# ===================== 🚀 Main =====================
def sidebar_nav():
    st.sidebar.title("Navigation")
    if 'user' in st.session_state and st.session_state['user']:
        st.sidebar.markdown(f"👤 **{st.session_state['user']['full_name']}**")
        return st.sidebar.radio("Go to", [
            "Dashboard", "New Inspection", "Profile & Branding",
            "Admin – Users" if is_admin() else "", "Logout"
        ], index=0)
    return None

def main():
    init_db()
    if 'user' not in st.session_state or st.session_state['user'] is None:
        st.session_state['user'] = {'id':1,'username':'demo','full_name':'Demo Inspector','role':'inspector'}

    nav = sidebar_nav() or "Dashboard"
    if nav == "Dashboard": page_dashboard()
    elif nav == "New Inspection": page_new_inspection()
    elif nav == "Profile & Branding": page_profile()
    elif nav == "Admin – Users": page_admin_users()
    elif nav == "Logout": st.session_state.clear(); st.rerun()

if __name__ == "__main__":
    main()
