import io
from io import BytesIO
from typing import List
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Spacer, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
import arabic_reshaper
from bidi.algorithm import get_display

from models import Inspection, InspectionItem, User

styles = getSampleStyleSheet()
styleN = styles["Normal"]
styleH = styles["Heading2"]

def _rtl(text: str) -> str:
    if not text:
        return ""
    return get_display(arabic_reshaper.reshape(text))

def generate_inspection_pdf(*, insp: Inspection, items: List[InspectionItem], user: User) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    margin = 15 * mm
    y = height - margin

    # --- Header: Logo + Hero image ---
    if insp.logo_image:
        try:
            logo_reader = ImageReader(io.BytesIO(insp.logo_image))
            c.drawImage(logo_reader, margin, y - 20*mm, width=30*mm, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass
    if insp.hero_image:
        try:
            hero_reader = ImageReader(io.BytesIO(insp.hero_image))
            c.drawImage(hero_reader, margin + 40*mm, y - 40*mm, width=100*mm, height=40*mm, preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin, y, "Inspection Report / تقرير التفتيش")
    y -= 50*mm

    # --- Building info ---
    c.setFont("Helvetica", 10)
    c.drawString(margin, y, f"Building: {insp.building_name}")
    y -= 6*mm
    if insp.building_address:
        c.drawString(margin, y, f"Address: {insp.building_address}")
        y -= 6*mm
    c.drawString(margin, y, f"Inspector: {user.full_name}")
    y -= 12*mm

    # --- Checklist ---
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, "Checklist / قائمة الفحص")
    y -= 8*mm

    for idx, it in enumerate(items, start=1):
        c.setFont("Helvetica", 10)
        q = f"{idx}. {it.question_en} — [{it.status}]"
        c.drawString(margin, y, q)
        y -= 5*mm
        if it.question_ar:
            c.drawString(margin, y, _rtl(it.question_ar))
            y -= 5*mm
        if it.observation_text:
            c.drawString(margin+10, y, f"Obs: {it.observation_text}")
            y -= 5*mm
        if it.code_ref:
            c.drawString(margin+10, y, f"Code: {it.code_ref}")
            y -= 5*mm

        # --- Checklist photo ---
        if it.photo:
            try:
                photo_reader = ImageReader(io.BytesIO(it.photo))
                c.drawImage(photo_reader, margin+10, y-40*mm, width=60*mm, height=40*mm, preserveAspectRatio=True, mask='auto')
                y -= 45*mm
            except Exception:
                pass

        # page break check
        if y < 40*mm:
            c.showPage()
            y = height - margin

    # --- Signature ---
    if insp.signature_image:
        try:
            sig_reader = ImageReader(io.BytesIO(insp.signature_image))
            c.drawString(margin, y-10, "Inspector Signature:")
            c.drawImage(sig_reader, margin+40*mm, y-20*mm, width=50*mm, height=20*mm, mask='auto')
            y -= 30*mm
        except Exception:
            pass

    # --- Footer ---
    c.line(margin, 20*mm, width - margin, 20*mm)
    if user.is_subscribed and user.company_info:
        c.setFont("Helvetica", 9)
        c.drawString(margin, 15*mm, user.company_info)
    else:
        c.setFont("Helvetica", 9)
        c.drawString(margin, 15*mm, "Powered by The AI Bureau + Safety Lines")

    c.showPage()
    c.save()
    return buf.getvalue()
