from __future__ import annotations
from io import BytesIO
from typing import List, Optional
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import arabic_reshaper
from bidi.algorithm import get_display

from models import Inspection, InspectionItem, User

# Try to register a Unicode font (must be present on server)
# You can upload 'DejaVuSans.ttf' or 'Amiri-Regular.ttf' next to the app for better Arabic rendering.
def _register_fonts():
    try:
        pdfmetrics.registerFont(TTFont("DejaVuSans", "DejaVuSans.ttf"))
        return "DejaVuSans"
    except Exception:
        # Fallback to Helvetica (Arabic won't render properly without a Unicode font)
        return "Helvetica"

FONT_NAME = _register_fonts()

def _draw_text(c, x, y, text, size=10, rtl=False):
    c.setFont(FONT_NAME, size)
    if rtl and FONT_NAME != "Helvetica":
        reshaped = arabic_reshaper.reshape(text or "")
        bidi_text = get_display(reshaped)
        c.drawString(x, y, bidi_text)
    else:
        c.drawString(x, y, text or "")

def generate_inspection_pdf(*, insp: Inspection, items: List[InspectionItem], user: User) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    margin = 15 * mm
    y = height - margin

    # Header: logo or title
    c.setFont(FONT_NAME, 16)
    header_title = "Inspection Report / تقرير التفتيش"
    c.drawString(margin, y, header_title)
    y -= 10 * mm

    # Building & Inspector info
    _draw_text(c, margin, y, f"Building: {insp.building_name}", 11); y -= 6 * mm
    _draw_text(c, margin, y, f"Address: {insp.building_address or '-'}", 10); y -= 6 * mm
    _draw_text(c, margin, y, f"Inspector: {insp.inspector.full_name}  (Civil ID: {insp.inspector_civil_id or '-'})", 10); y -= 6 * mm

    # Company footer logic handled at end

    # Checklist header
    y -= 4 * mm
    _draw_text(c, margin, y, "Checklist / قائمة الفحص", 12); y -= 8 * mm

    # Items
    for idx, it in enumerate(items, start=1):
        line = f"{idx}. {it.question_en} — [{it.status}]"
        _draw_text(c, margin, y, line, 10)
        y -= 5 * mm
        if it.question_ar:
            _draw_text(c, margin, y, it.question_ar, 10, rtl=True)
            y -= 5 * mm
        if it.observation_text:
            _draw_text(c, margin + 5 * mm, y, f"Obs: {it.observation_text}", 9)
            y -= 5 * mm
        if it.code_ref:
            _draw_text(c, margin + 5 * mm, y, f"Code: {it.code_ref}", 9)
            y -= 5 * mm
        # add page if needed
        if y < 40 * mm:
            c.showPage()
            y = height - margin
            _draw_text(c, margin, y, "Checklist (cont.) / متابعة قائمة الفحص", 12); y -= 8 * mm

    # Footer
    c.line(margin, 20 * mm, width - margin, 20 * mm)
    if user.is_subscribed and (user.company_info or user.company_logo):
        # White-label footer
        _draw_text(c, margin, 15 * mm, user.company_info or "", 9)
        # (Logo rendering could be added by saving logo to temp and drawingImage)
    else:
        # Free watermark
        _draw_text(c, margin, 15 * mm, "Powered by The AI Bureau + Safety Lines", 9)

    c.showPage()
    c.save()
    return buf.getvalue()
