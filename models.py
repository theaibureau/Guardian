from __future__ import annotations
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import declarative_base, relationship, Mapped, mapped_column
from sqlalchemy import (
    String, Integer, DateTime, ForeignKey, LargeBinary, Text, Boolean
)

Base = declarative_base()

# =========================
# User
# =========================
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    mobile: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)

    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    civil_defense_id: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)

    role: Mapped[str] = mapped_column(String(20), nullable=False, default="inspector")
    # signup without admin approval -> default 'active'
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")  # active / disabled

    # Subscription & white-label
    is_subscribed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    company_logo: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)
    company_info: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Email confirmation (if you use email verification links)
    confirmation_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Auth
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    inspections: Mapped[List["Inspection"]] = relationship(
        "Inspection", back_populates="inspector", cascade="all, delete-orphan"
    )


# =========================
# Inspection (header & report-wide assets)
# =========================
class Inspection(Base):
    __tablename__ = "inspections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    scheduled_for: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    building_name: Mapped[str] = mapped_column(String(200), nullable=False)
    building_address: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    inspector_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    inspector_civil_id: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)

    # Report assets
    logo_image: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)     # company logo (top-left)
    hero_image: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)     # building/site hero image (large)
    signature_image: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pdf_blob: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    inspector: Mapped["User"] = relationship("User", back_populates="inspections")
    items: Mapped[List["InspectionItem"]] = relationship(
        "InspectionItem", back_populates="inspection", cascade="all, delete-orphan"
    )
    corrective_actions: Mapped[List["CorrectiveAction"]] = relationship(
        "CorrectiveAction", back_populates="inspection", cascade="all, delete-orphan"
    )


# =========================
# InspectionItem (per-checklist line)
# =========================
class InspectionItem(Base):
    __tablename__ = "inspection_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inspection_id: Mapped[int] = mapped_column(ForeignKey("inspections.id"), nullable=False)

    question_en: Mapped[str] = mapped_column(String(500), nullable=False)
    question_ar: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Compliant / Non-Compliant / Pending
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Pending")

    observation_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Legacy/general code field (kept for backward compatibility)
    code_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # NEW: Structured code selections
    code_ref_nfpa: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    code_ref_uae:  Mapped[Optional[str]] = mapped_column(String(80), nullable=True)

    # Optional evidence photo for this item
    photo: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    inspection: Mapped["Inspection"] = relationship("Inspection", back_populates="items")


# =========================
# CorrectiveAction (optional follow-up tasks)
# =========================
class CorrectiveAction(Base):
    __tablename__ = "corrective_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inspection_id: Mapped[int] = mapped_column(ForeignKey("inspections.id"), nullable=False)
    item_id: Mapped[int] = mapped_column(ForeignKey("inspection_items.id"), nullable=False)

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    responsible_person: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    status: Mapped[str] = mapped_column(String(30), default="Open", nullable=False)
    due_date: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.utcnow() + timedelta(days=7),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    inspection: Mapped["Inspection"] = relationship("Inspection", back_populates="corrective_actions")
