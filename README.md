# Smart Healthcare Management & Disease Prediction System — PRO V2

A professional, responsive Flask-based healthcare management and educational disease-prediction platform for academic/demo use.

## Included PRO modules
- AI symptom-based disease prediction (demonstration model)
- Explainable prediction result flow and confidence display
- **131-topic Disease Library** with symptoms, risk factors, prevention, management guidance and urgent warning signs
- Patient dashboard, health history and printable digital health report
- Complete health profile with emergency-contact fields, allergies, medications and consent/preferences
- Doctor directory with specialty/city search
- Hospital finder and appointment request workflow
- Admin command center with patient/prediction/appointment statistics
- Admin appointment approve/reject/complete workflow + patient notifications
- Patient account management from admin
- PRO educational health chatbot with emergency-safety response rules
- Multi-language preference switcher (UI preference architecture)
- SEO-ready public `sitemap.xml` and `robots.txt`
- Password hashing, login protection, role-based admin authorization and audit logging
- SQLite indexes and future-ready tables for profiles, notifications, doctors and audit logs
- Responsive healthcare UI and print-friendly reporting

## Important medical disclaimer
This project is an **educational/demo system**. The bundled disease model uses synthetic/demo data and is not clinically validated. Predictions are not diagnoses and must not be used to start, stop or change treatment. Disease-library content is educational and should be checked against authoritative health organizations and qualified clinicians. Emergency symptoms require urgent professional care.

## Windows / VS Code setup

```powershell
python -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python train_model.py
python app.py
```

Then open `http://127.0.0.1:5000`.

### Demo admin
- Email: `admin@smarthealth.local`
- Password: `admin123`

Change the secret key and demo password before any real deployment.

## Public SEO endpoints
- `/sitemap.xml`
- `/robots.txt`
- `/diseases`
- `/diseases/<slug>`
- `/doctors`
- `/hospitals`

Private patient/admin areas are disallowed in `robots.txt`.

## Architecture notes
The current release remains easy to run as a student/demo Flask project while adding migration-ready tables and indexes. For production scale, move from SQLite to PostgreSQL, place secrets in environment variables, add CSRF protection, rate limiting, proper migrations, secure cookie settings, HTTPS, backups, monitoring, clinically reviewed datasets/content, and a professionally validated AI/medical workflow.

## Folder structure

```text
Smart-Healthcare-System/
├── app.py
├── disease_data.py
├── train_model.py
├── requirements.txt
├── README.md
├── model/
├── data/
├── templates/
└── static/
```
