# The Guardian – Safety & Compliance

## What you get
- Open signup (email + mobile) with **email confirmation link** (no admin approval).
- Inspector Dashboard: past inspections, upcoming inspections, new inspection.
- Inspection workflow with logo upload, hero image, **75-question bilingual checklist** (CSV-powered), per-question photo, observation, NFPA/UAE code reference.
- **PDF Export (ReportLab)** bilingual; free users get a footer watermark `Powered by The AI Bureau + Safety Lines`; subscribed users get their **logo + company info** instead.
- Admin panel to disable/reactivate users and toggle **subscription**.

## Run locally
```bash
pip install -r requirements.txt
cp .env.example .env  # fill values (SECRET_KEY, SMTP, APP_BASE_URL)
streamlit run app.py
```

## Deploy on Render
- Build: `pip install -r requirements.txt`
- Start: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
- Set env vars from `.env.example` in Render dashboard.
