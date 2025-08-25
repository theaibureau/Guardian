import io
from io import BytesIO
from typing import List
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Spacer, Image as RLImage, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
import arabic_reshaper
from bidi.algorithm import get_display

from models import Inspection, InspectionItem, User

styles = getSampleStyleSheet()
styleN = styles["Normal"]
styleH = styles["Heading2"]

def _rtl(text: str) -> str:
    if not text: return ""
    return get_display(arabic_reshaper.reshape(text))

def generate_inspection_pdf(*, insp: Inspection, items: List[InspectionItem], user: User) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    margin = 20 * mm
    y = height - margin

    # ================= HEADER =================
    if insp.logo_image:
        try:
            logo_reader = ImageReader(io.BytesIO(insp.logo_image))
            c.drawImage(logo_reader, margin, y-40, width=60, height=40, preserveAspectRatio=True, mask='auto')
        except: pass

    c.setFont("Helvetica-Bold", 14)
    c.drawRightString(width - margin, y-20, "Safety Lines & The AI Bureau")

    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(width/2, y-60, "INSPECTION REPORT")
    y -= 100

    # ================= HERO IMAGE =================
    if insp.hero_image:
        try:
            hero_reader = ImageReader(io.BytesIO(insp.hero_image))
            c.drawImage(hero_reader, margin, y-200, width=width-2*margin, height=150,
                        preserveAspectRatio=True, mask='auto')
            y -= 220
        except: pass

    # ================= BUILDING INFO =================
    c.setFont("Helvetica", 11)
    c.drawString(margin, y, f"Building: {insp.building_name}")
    y -= 15
    if insp.building_address:
        c.drawString(margin, y, f"Address: {insp.building_address}")
        y -= 15
    c.drawString(margin, y, f"Inspector: {user.full_name}")
    y -= 25

    # ================= CHECKLIST =================
    from reportlab.platypus import SimpleDocTemplate
    story = []
    story.append(Spacer(1, 12))

    for idx, it in enumerate(items, start=1):
        left_content = f"<b>{idx}. {it.question_en}</b><br/>Status: {it.status}"
        if it.observation_text:
            left_content += f"<br/>Notes: {it.observation_text}"
        nfpa = getattr(it, "code_ref_nfpa", None) or ""
        uae = getattr(it, "code_ref_uae", None) or it.code_ref or ""
        if nfpa or uae:
            left_content += f"<br/>Codes: {nfpa} {('| ' + uae) if uae else ''}"

        row = [
            Paragraph(left_content, styleN),
            RLImage(io.BytesIO(it.photo), width=120, height=90) if it.photo else ""
        ]
        table = Table([row], colWidths=[350, 150])
        table.setStyle(TableStyle([
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("BOX", (0,0), (-1,-1), 0.5, colors.grey),
            ("INNERGRID", (0,0), (-1,-1), 0.25, colors.grey),
        ]))
        story.append(table)
        story.append(Spacer(1, 12))

    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=margin, rightMargin=margin,
                            topMargin=margin, bottomMargin=40)
    doc.build(story, onFirstPage=lambda c, d: _footer(c, width),
              onLaterPages=lambda c, d: _footer(c, width))

    return buf.getvalue()

# ================= FOOTER =================
def _footer(c, width):
    c.setFont("Helvetica", 9)
    c.setFillColor(colors.grey)
    c.drawCentredString(width/2, 20, "Powered by Safety Lines & The AI Bureau")
