import io, os, csv
from datetime import datetime, date
from typing import List

import streamlit as st
from PIL import Image
from streamlit_drawable_canvas import st_canvas
from sqlalchemy.orm import Session
from sqlalchemy import func

from dotenv import load_dotenv
load_dotenv()

from db import init_db, SessionLocal
from models import User, Inspection, InspectionItem
from auth import (
    create_user_and_send_confirmation, confirm_email, authenticate,
    toggle_subscription, set_company_branding
)
from report import generate_inspection_pdf

APP_NAME = os.getenv("APP_NAME", "The Guardian – Safety & Compliance")

def get_db() -> Session:
    return SessionLocal()

def require_login():
    if 'user' not in st.session_state or st.session_state['user'] is None:
        st.stop()

def is_admin() -> bool:
    return st.session_state.get('user', {}).get('role') == 'admin'

def load_checklist() -> List[dict]:
    rows = []
    with open("checklist.csv", "r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)
    return rows

def handle_confirm_param():
    qp = st.query_params
    token = qp.get("confirm", None)
    if token:
        with get_db() as db:
            ok = confirm_email(db, token)
            if ok:
                st.success("Email confirmed! You can now sign in.")
            else:
                st.error("Invalid or expired confirmation link.")

def login_ui():
    st.title(APP_NAME)
    st.subheader("Sign in")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login", use_container_width=True):
        with get_db() as db:
            user = authenticate(db, username, password)
            if user:
                st.session_state['user'] = {
                    'id': user.id,
                    'username': user.username,
                    'full_name': user.full_name,
                    'role': user.role,
                }
                st.success(f"Welcome, {user.full_name}")
                st.rerun()
            else:
                st.error("Invalid credentials or email not confirmed / account disabled.")

    st.divider()
    st.caption("No account? Create one below and confirm via email.")
    if st.button("Create an account", type="secondary"):
        st.session_state['page'] = 'signup'
        st.rerun()

def signup_ui():
    st.title(APP_NAME)
    st.subheader("Sign up")
    with st.form("signup_form"):
        full_name = st.text_input("Full name *")
        civil_id = st.text_input("Civil Defense ID (optional)")
        username = st.text_input("Username *")
        email = st.text_input("Email *")
        mobile = st.text_input("Mobile number")
        pwd1 = st.text_input("Password *", type="password")
        pwd2 = st.text_input("Confirm Password *", type="password")
        submitted = st.form_submit_button("Sign up", use_container_width=True)
        if submitted:
            if not full_name or not username or not email or not pwd1:
                st.error("Please fill all required fields (*)")
            elif pwd1 != pwd2:
                st.error("Passwords do not match")
            else:
                with get_db() as db:
                    try:
                        create_user_and_send_confirmation(
                            db,
                            username=username,
                            email=email,
                            mobile=mobile or None,
                            full_name=full_name,
                            civil_defense_id=civil_id or None,
                            raw_password=pwd1,
                        )
                        st.success("Account created! Please check your email and click the confirmation link.")
                    except Exception as e:
                        st.error(str(e))
    if st.button("Back to login"):
        st.session_state['page'] = 'login'
        st.rerun()

def sidebar_nav():
    st.sidebar.title("Navigation")
    if 'user' in st.session_state and st.session_state['user']:
        st.sidebar.markdown(f"**Logged in:** {st.session_state['user']['full_name']}")
        choice = st.sidebar.radio("Go to", [
            "Dashboard",
            "New Inspection",
            "Profile & Branding",
            "Admin – Users" if is_admin() else "",
            "Logout"
        ], index=0)
        return choice
    return None

def page_dashboard():
    st.header("Inspector Dashboard")
    with get_db() as db:
        uid = st.session_state['user']['id']

        # Past inspections
        st.subheader("Past Inspections")
        past = db.query(Inspection).filter(Inspection.inspector_id == uid).order_by(Inspection.created_at.desc()).all()
        if not past:
            st.write("No inspections yet.")
        else:
            for insp in past:
                with st.expander(f"#{insp.id} – {insp.building_name} – {insp.created_at.date()}"):
                    st.write(f"Address: {insp.building_address or '-'}")
                    st.write(f"Notes: {insp.notes or '-'}")
                    if insp.pdf_blob:
                        st.download_button("Download PDF", data=insp.pdf_blob, file_name=f"inspection_{insp.id}.pdf", mime="application/pdf")

        # Upcoming inspections (scheduled)
        st.subheader("Upcoming Inspections")
        upcoming = db.query(Inspection).filter(Inspection.inspector_id == uid, Inspection.scheduled_for != None).order_by(Inspection.scheduled_for.asc()).all()
        if not upcoming:
            st.write("No upcoming inspections scheduled.")
        else:
            for insp in upcoming:
                st.write(f"{insp.scheduled_for} – {insp.building_name}")

def page_new_inspection():
    st.header("New Inspection")
    with st.form("new_insp_form"):
        building_name = st.text_input("Building Name *")
        building_address = st.text_input("Address")
        scheduled_for = st.date_input("Schedule for (optional)")
        notes = st.text_area("General Notes")

        # Branding assets
        col1, col2 = st.columns(2)
        with col1:
            logo_file = st.file_uploader("Report Logo (optional)", type=["png", "jpg", "jpeg"])
        with col2:
            hero_file = st.file_uploader("Hero Image (optional)", type=["png", "jpg", "jpeg"])

        # Signature canvas
        st.markdown("**Inspector Signature**")
        canvas = st_canvas(height=150, width=600, background_color="#FFFFFF", stroke_color="#000000", stroke_width=2, drawing_mode="freedraw", key="sig")

        submitted = st.form_submit_button("Create Inspection", use_container_width=True)
        if submitted:
            if not building_name:
                st.error("Building name is required")
                return
            # Convert optional images to bytes
            def file_to_bytes(f):
                if not f: return None
                return f.read()

            sig_bytes = None
            if canvas and canvas.image_data is not None:
                try:
                    from PIL import Image
                    import numpy as np
                    img = Image.fromarray((canvas.image_data[:, :, :3]).astype("uint8"))
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    sig_bytes = buf.getvalue()
                except Exception:
                    sig_bytes = None

            with get_db() as db:
                insp = Inspection(
                    building_name=building_name,
                    building_address=building_address or None,
                    scheduled_for=datetime.combine(scheduled_for, datetime.min.time()) if isinstance(scheduled_for, date) else None,
                    inspector_id=st.session_state['user']['id'],
                    inspector_civil_id=None,
                    logo_image=file_to_bytes(logo_file),
                    hero_image=file_to_bytes(hero_file),
                    signature_image=sig_bytes,
                    notes=notes or None,
                )
                db.add(insp); db.commit(); db.refresh(insp)

                # Load checklist and create items
                for row in load_checklist():
                    item = InspectionItem(
                        inspection_id=insp.id,
                        question_en=row.get("EnglishQuestion", ""),
                        question_ar=row.get("ArabicQuestion", ""),
                        status="Pending",
                        observation_text=None,
                        code_ref=None,
                        photo=None,
                    )
                    db.add(item)
                db.commit()

                st.success(f"Inspection #{insp.id} created. Proceed to fill the checklist below.")
                st.session_state['current_insp_id'] = insp.id
                st.rerun()

    # If an inspection was just created or selected, show checklist editor
    cur_id = st.session_state.get('current_insp_id')
    if cur_id:
        with get_db() as db:
            insp = db.query(Inspection).filter(Inspection.id == cur_id).first()
            if insp:
                st.subheader(f"Checklist – {insp.building_name}")
                items = db.query(InspectionItem).filter(InspectionItem.inspection_id == insp.id).all()
                for it in items:
                    with st.expander(it.question_en):
                        it.status = st.selectbox("Status", ["Compliant", "Non-Compliant", "Pending"], index=["Compliant","Non-Compliant","Pending"].index(it.status), key=f"st_{it.id}")
                        it.observation_text = st.text_area("Observation", value=it.observation_text or "", key=f"obs_{it.id}")
                        it.code_ref = st.text_input("NFPA/UAE Code reference", value=it.code_ref or "", key=f"code_{it.id}")
                        up = st.file_uploader("Photo (optional)", type=["png","jpg","jpeg"], key=f"ph_{it.id}")
                        if up:
                            it.photo = up.read()
                        if st.button("Save item", key=f"sv_{it.id}"):
                            db.commit()
                            st.success("Saved")

                if st.button("Export PDF", type="primary"):
                    # Refresh items, generate PDF
                    items = db.query(InspectionItem).filter(InspectionItem.inspection_id == insp.id).all()
                    user = db.query(User).filter(User.id == insp.inspector_id).first()
                    pdf_bytes = generate_inspection_pdf(insp=insp, items=items, user=user)
                    insp.pdf_blob = pdf_bytes
                    insp.completed_at = datetime.utcnow()
                    db.commit()
                    st.download_button("Download PDF", data=pdf_bytes, file_name=f"inspection_{insp.id}.pdf", mime="application/pdf")

def page_profile():
    st.header("Profile & Branding")
    with get_db() as db:
        user = db.query(User).filter(User.id == st.session_state['user']['id']).first()
        st.write(f"**Username:** {user.username}")
        st.write(f"**Email:** {user.email}")
        st.write(f"**Mobile:** {user.mobile or '-'}")
        st.write(f"**Subscription:** {'Subscribed' if user.is_subscribed else 'Free'}")

        if user.is_subscribed:
            st.subheader("Company Branding")
            logo = st.file_uploader("Upload Company Logo (PNG/JPG)", type=["png","jpg","jpeg"])
            info = st.text_area("Company Info (footer)")
            if st.button("Save Branding"):
                set_company_branding(db, user.id, company_info=info or None, company_logo_bytes=logo.read() if logo else None)
                st.success("Branding saved.")
        else:
            st.info("Upgrade to a subscription to enable custom logo and company info in PDF exports.")

def page_admin_users():
    if not is_admin():
        st.error("Admins only."); return
    st.header("Admin – Users")
    with get_db() as db:
        users = db.query(User).order_by(User.created_at.desc()).all()
        for u in users:
            with st.expander(f"{u.full_name} (@{u.username}) – {u.role} [{u.status}] – {'Subscribed' if u.is_subscribed else 'Free'}"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button(("Disable" if u.status == "active" else "Activate"), key=f"status_{u.id}"):
                        u.status = "active" if u.status != "active" else "disabled"
                        db.commit(); st.rerun()
                with col2:
                    if st.button("Make Subscribed" if not u.is_subscribed else "Make Free", key=f"sub_{u.id}"):
                        toggle_subscription(db, u.id, not u.is_subscribed); st.rerun()
                with col3:
                    st.write(f"Email: {u.email}")

def main():
    st.set_page_config(page_title=APP_NAME, page_icon="🛡️", layout="wide")
    init_db()
    handle_confirm_param()

    if 'user' not in st.session_state: st.session_state['user'] = None
    if 'page' not in st.session_state: st.session_state['page'] = 'login'

    if st.session_state['page'] == 'signup':
        signup_ui(); return

    if st.session_state['user'] is None:
        login_ui(); return

    nav = sidebar_nav()
    if nav == "Logout":
        st.session_state['user'] = None
        st.session_state['page'] = 'login'
        st.rerun()
    elif nav == "Dashboard":
        page_dashboard()
    elif nav == "New Inspection":
        page_new_inspection()
    elif nav == "Profile & Branding":
        page_profile()
    elif nav == "Admin – Users":
        page_admin_users()

if __name__ == "__main__":
    main()
