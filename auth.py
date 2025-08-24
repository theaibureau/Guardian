import os, smtplib, ssl
from email.message import EmailMessage
from typing import Optional
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from email_validator import validate_email, EmailNotValidError
from sqlalchemy.orm import Session
from passlib.hash import bcrypt

from models import User

SECRET_KEY = os.getenv("SECRET_KEY", "change_me")
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8501")

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER or "no-reply@example.com")

def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(SECRET_KEY, salt="guardian-email-confirm")

def generate_token(email: str) -> str:
    return _serializer().dumps(email)

def verify_token(token: str, max_age_seconds: int = 60 * 60 * 24) -> Optional[str]:
    try:
        email = _serializer().loads(token, max_age=max_age_seconds)
        return email
    except (BadSignature, SignatureExpired):
        return None

def send_confirmation_email(to_email: str, token: str):
    confirm_link = f"{APP_BASE_URL}?confirm={token}"
    subject = "Confirm your account – The Guardian"
    body = f"""Hello,

Please confirm your account by clicking the link below:
{confirm_link}

If you didn't sign up, you can ignore this message.

The Guardian"""

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = to_email
    msg.set_content(body)

    context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls(context=context)
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)

def create_user_and_send_confirmation(db: Session, *, username: str, email: str, mobile: str | None,
                                      full_name: str, civil_defense_id: str | None, raw_password: str) -> User:
    # validate email format
    try:
        validate_email(email, check_deliverability=False)
    except EmailNotValidError as e:
        raise ValueError(str(e))

    if db.query(User).filter((User.username == username) | (User.email == email)).first():
        raise ValueError("Username or email already exists")

    token = generate_token(email)
    user = User(
        username=username,
        email=email,
        mobile=mobile,
        full_name=full_name,
        civil_defense_id=civil_defense_id,
        role="inspector",
        status="pending",   # will become 'active' after email confirmation
        is_subscribed=False,
        confirmation_token=token,
        password_hash=bcrypt.hash(raw_password),
    )
    db.add(user)
    db.commit()

    # Send email
    send_confirmation_email(email, token)
    return user

def confirm_email(db: Session, token: str) -> bool:
    email = verify_token(token)
    if not email:
        return False
    user = db.query(User).filter(User.email == email, User.confirmation_token == token).first()
    if not user:
        return False
    user.status = "active"
    user.confirmation_token = None
    db.commit()
    return True

def authenticate(db: Session, username: str, raw_password: str) -> Optional[User]:
    user = db.query(User).filter(User.username == username).first()
    if user and bcrypt.verify(raw_password, user.password_hash) and user.status == "active":
        return user
    return None

def toggle_subscription(db: Session, user_id: int, subscribed: bool):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("User not found")
    user.is_subscribed = subscribed
    db.commit()

def set_company_branding(db: Session, user_id: int, *, company_info: str | None, company_logo_bytes: bytes | None):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError("User not found")
    if company_info is not None:
        user.company_info = company_info
    if company_logo_bytes is not None:
        user.company_logo = company_logo_bytes
    db.commit()
