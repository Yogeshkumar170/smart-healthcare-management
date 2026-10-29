import os
import sqlite3
import pickle
from datetime import datetime
from functools import wraps

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    jsonify,
    make_response,
)
from werkzeug.security import generate_password_hash, check_password_hash
from disease_data import DISEASES, DISEASES_BY_SLUG


# =========================================================
# APP CONFIGURATION
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(
    BASE_DIR,
    "data",
    "healthcare.db"
)

MODEL_PATH = os.path.join(
    BASE_DIR,
    "model",
    "disease_model.pkl"
)

app = Flask(__name__)

# Change this in production.
app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "change-this-secret-key-in-production"
)


# =========================================================
# SYMPTOMS
# =========================================================

SYMPTOMS = [
    "fever",
    "cough",
    "fatigue",
    "headache",
    "sore_throat",
    "runny_nose",
    "body_pain",
    "nausea",
    "vomiting",
    "diarrhea",
    "abdominal_pain",
    "chest_pain",
    "shortness_of_breath",
    "dizziness",
    "skin_rash",
    "joint_pain",
    "loss_of_smell",
    "loss_of_taste",
    "frequent_urination",
    "increased_thirst",
]


SYMPTOM_LABELS = {
    "fever": "Fever",
    "cough": "Cough",
    "fatigue": "Fatigue",
    "headache": "Headache",
    "sore_throat": "Sore Throat",
    "runny_nose": "Runny Nose",
    "body_pain": "Body Pain",
    "nausea": "Nausea",
    "vomiting": "Vomiting",
    "diarrhea": "Diarrhea",
    "abdominal_pain": "Abdominal Pain",
    "chest_pain": "Chest Pain",
    "shortness_of_breath": "Shortness of Breath",
    "dizziness": "Dizziness",
    "skin_rash": "Skin Rash",
    "joint_pain": "Joint Pain",
    "loss_of_smell": "Loss of Smell",
    "loss_of_taste": "Loss of Taste",
    "frequent_urination": "Frequent Urination",
    "increased_thirst": "Increased Thirst",
}


# =========================================================
# DATABASE
# =========================================================

def get_db():
    """
    Create and return SQLite database connection.
    """
    os.makedirs(
        os.path.dirname(DB_PATH),
        exist_ok=True
    )

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    return conn


def init_db():
    """
    Create database tables and ensure demo admin exists.

    Important:
    If admin@smarthealth.local already exists as a patient,
    this function automatically repairs the account and makes
    it an admin.
    """

    os.makedirs(
        os.path.dirname(DB_PATH),
        exist_ok=True
    )

    conn = get_db()

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'patient',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS health_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            age INTEGER,
            gender TEXT,
            height REAL,
            weight REAL,
            blood_pressure TEXT,
            glucose REAL,
            symptoms TEXT,
            prediction TEXT,
            confidence REAL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            doctor_name TEXT NOT NULL,
            appointment_date TEXT NOT NULL,
            reason TEXT,
            status TEXT DEFAULT 'Pending',
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """
    )

    # Future-ready modules
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id INTEGER PRIMARY KEY,
            dob TEXT,
            gender TEXT,
            phone TEXT,
            alternate_phone TEXT,
            address TEXT,
            city TEXT,
            state TEXT,
            pin_code TEXT,
            blood_group TEXT,
            allergies TEXT,
            existing_conditions TEXT,
            current_medications TEXT,
            emergency_notes TEXT,
            emergency_contact_name TEXT,
            emergency_contact_relation TEXT,
            emergency_contact_number TEXT,
            preferred_language TEXT DEFAULT 'English',
            notifications INTEGER DEFAULT 1,
            consent INTEGER DEFAULT 1,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            specialty TEXT NOT NULL,
            hospital TEXT,
            city TEXT,
            experience INTEGER DEFAULT 0,
            languages TEXT,
            available INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            target TEXT,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_health_user_created
        ON health_records(user_id, created_at);

        CREATE INDEX IF NOT EXISTS idx_appt_user_date
        ON appointments(user_id, appointment_date);

        CREATE INDEX IF NOT EXISTS idx_notifications_user_read
        ON notifications(user_id, is_read);
        """
    )

    # ---------------------------------------------------------
    # DOCTOR DIRECTORY SEED
    # ---------------------------------------------------------

    if conn.execute(
        "SELECT COUNT(*) AS c FROM doctors"
    ).fetchone()["c"] == 0:

        doctors = [
            (
                "Dr. Aarav Sharma",
                "General Medicine",
                "AIIMS Rishikesh",
                "Rishikesh",
                "Dehradun",
                "Uttarakhand",
                10,
                "Hindi, English",
                1,
                "0135-2462929",
                "https://aiimsrishikesh.edu.in/a1_1/hospital_directory.php"
            ),
            (
                "Dr. Ananya Verma",
                "Cardiology",
                "AIIMS Rishikesh",
                "Rishikesh",
                "Dehradun",
                "Uttarakhand",
                12,
                "Hindi, English",
                1,
                "0135-2462503",
                "https://aiimsrishikesh.edu.in/a1_1/?page_id=2330"
            ),
            (
                "Dr. Rohan Gupta",
                "Pulmonary Medicine",
                "AIIMS Rishikesh",
                "Rishikesh",
                "Dehradun",
                "Uttarakhand",
                14,
                "Hindi, English",
                1,
                "0135-2462984",
                "https://aiimsrishikesh.edu.in/a1_1/hospital_directory.php"
            ),
            (
                "Dr. Meera Singh",
                "General Medicine",
                "AIIMS New Delhi",
                "New Delhi",
                "New Delhi",
                "Delhi",
                9,
                "Hindi, English",
                1,
                "011-26588500",
                "https://www.aiims.edu/index.php/hi/2026-08-27-10-44-00"
            ),
            (
                "Dr. Kabir Khan",
                "Neurology",
                "PGIMER Chandigarh",
                "Chandigarh",
                "Chandigarh",
                "Chandigarh",
                11,
                "Hindi, English",
                1,
                "+91-172-2755656",
                "https://www.pgimer.edu.in/"
            ),
            (
                "Dr. Isha Patel",
                "General Medicine",
                "AIIMS Patna",
                "Patna",
                "Patna",
                "Bihar",
                13,
                "Hindi, English",
                1,
                "+91-612-2451070",
                "https://aiimspatna.edu.in/contact"
            ),
            (
                "Dr. Neeraj Verma",
                "General Medicine",
                "AIIMS Gorakhpur",
                "Gorakhpur",
                "Gorakhpur",
                "Uttar Pradesh",
                10,
                "Hindi, English",
                1,
                "5512205501/02/03",
                "https://aiimsgorakhpur.edu.in/"
            ),
            (
                "Dr. Priya Singh",
                "Emergency Medicine",
                "AIIMS Rishikesh",
                "Rishikesh",
                "Dehradun",
                "Uttarakhand",
                8,
                "Hindi, English",
                1,
                "0135-2462503",
                "https://aiimsrishikesh.edu.in/a1_1/?page_id=2330"
            ),
        ]

        conn.executemany(
            """
            INSERT INTO doctors(
                name,
                specialty,
                hospital,
                city,
                district,
                state,
                experience,
                languages,
                available,
                contact,
                source_url
            )
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            doctors
        )

    conn.commit()

    # =====================================================
    # DOCTOR SCHEMA MIGRATION
    # =====================================================

    doctor_columns = {
        row["name"]
        for row in conn.execute(
            "PRAGMA table_info(doctors)"
        ).fetchall()
    }

    doctor_migrations = {
        "district": "ALTER TABLE doctors ADD COLUMN district TEXT",
        "state": "ALTER TABLE doctors ADD COLUMN state TEXT",
        "contact": "ALTER TABLE doctors ADD COLUMN contact TEXT",
        "source_url": "ALTER TABLE doctors ADD COLUMN source_url TEXT",
        "photo_url": "ALTER TABLE doctors ADD COLUMN photo_url TEXT",
        "show_in_directory": "ALTER TABLE doctors ADD COLUMN show_in_directory INTEGER DEFAULT 1",
        "show_in_emergency": "ALTER TABLE doctors ADD COLUMN show_in_emergency INTEGER DEFAULT 0",
        "emergency_available": "ALTER TABLE doctors ADD COLUMN emergency_available INTEGER DEFAULT 0",
        "emergency_hours": "ALTER TABLE doctors ADD COLUMN emergency_hours TEXT",
    }

    for column, sql in doctor_migrations.items():
        if column not in doctor_columns:
            try:
                conn.execute(sql)
            except sqlite3.OperationalError:
                pass

    # Existing doctors should remain visible in normal directory.
    try:
        conn.execute(
            """
            UPDATE doctors
            SET show_in_directory=1
            WHERE show_in_directory IS NULL
            """
        )

        conn.execute(
            """
            UPDATE doctors
            SET show_in_emergency=1,
                emergency_available=1
            WHERE LOWER(COALESCE(specialty,'')) LIKE '%emergency%'
            """
        )
    except sqlite3.OperationalError:
        pass

    # =====================================================
    # EMERGENCY MODULE TABLES
    # =====================================================

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS emergency_helplines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            number TEXT NOT NULL,
            use_text TEXT,
            description TEXT,
            official_url TEXT,
            available_24x7 INTEGER DEFAULT 1,
            active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS emergency_hospitals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            city TEXT,
            district TEXT,
            state TEXT,
            address TEXT,
            emergency_contact TEXT,
            emergency_available INTEGER DEFAULT 1,
            official_url TEXT,
            map_url TEXT,
            active INTEGER DEFAULT 1,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS emergency_admissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            patient_name TEXT,
            age TEXT,
            dob TEXT,
            gender TEXT,
            mobile TEXT,
            emergency_contact TEXT,
            blood_group TEXT,
            address TEXT,
            emergency_problem TEXT,
            existing_conditions TEXT,
            medicines TEXT,
            allergies TEXT,
            emergency_notes TEXT,
            preferred_hospital TEXT,
            consent INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Request Sent',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE INDEX IF NOT EXISTS idx_emergency_admissions_user
        ON emergency_admissions(user_id, created_at);

        CREATE INDEX IF NOT EXISTS idx_emergency_admissions_status
        ON emergency_admissions(status);
        """
    )

    # =====================================================
    # EMERGENCY HELPLINE SEED DATA
    # =====================================================

    helpline_count = conn.execute(
        "SELECT COUNT(*) AS c FROM emergency_helplines"
    ).fetchone()["c"]

    if helpline_count == 0:

        helplines = [
            (
                "National Emergency",
                "112",
                "Police, ambulance and other emergency assistance",
                "Unified national emergency response number.",
                "https://112.gov.in/",
                1,
                1,
            ),
            (
                "National Ambulance Service",
                "102",
                "Ambulance / medical transport",
                "National ambulance service.",
                "https://www.india.gov.in/",
                1,
                1,
            ),
            (
                "Police",
                "100",
                "Police emergency",
                "Police assistance.",
                "https://www.india.gov.in/",
                1,
                1,
            ),
            (
                "Fire",
                "101",
                "Fire and rescue emergency",
                "Fire emergency assistance.",
                "https://www.india.gov.in/",
                1,
                1,
            ),
            (
                "Disaster Management",
                "1078",
                "Disaster-related emergency assistance",
                "Disaster management helpline.",
                "https://www.india.gov.in/",
                1,
                1,
            ),
            (
                "Women Helpline",
                "181",
                "Women in distress / support",
                "Women helpline.",
                "https://www.india.gov.in/",
                1,
                1,
            ),
            (
                "Child Helpline",
                "1098",
                "Children in distress",
                "Child protection emergency support.",
                "https://www.india.gov.in/",
                1,
                1,
            ),
            (
                "Senior Citizens Helpline",
                "14567",
                "Senior citizen support",
                "Elderly support helpline.",
                "https://www.india.gov.in/",
                1,
                1,
            ),
            (
                "HIV/AIDS Helpline",
                "1097",
                "HIV/AIDS information and support",
                "National HIV/AIDS helpline.",
                "https://naco.gov.in/",
                1,
                1,
            ),
            (
                "Ayushman Bharat",
                "14555",
                "Health scheme assistance",
                "Ayushman Bharat support.",
                "https://pmjay.gov.in/",
                1,
                1,
            ),
            (
                "National Health Mission",
                "104",
                "Health information / assistance",
                "Health-related helpline.",
                "https://nhm.gov.in/",
                1,
                1,
            ),
            (
                "Cyber Crime",
                "1930",
                "Cyber fraud / cyber crime reporting",
                "National cyber crime helpline.",
                "https://www.cybercrime.gov.in/",
                1,
                1,
            ),
            (
                "Railway Helpline",
                "139",
                "Railway assistance",
                "Indian Railways public assistance.",
                "https://www.indianrail.gov.in/",
                1,
                1,
            ),
            (
                "LPG Leak Emergency",
                "1906",
                "LPG gas leakage",
                "Emergency LPG leakage assistance.",
                "https://www.india.gov.in/",
                1,
                1,
            ),
            (
                "Road Accident",
                "1073",
                "Road accident assistance",
                "Road accident emergency assistance.",
                "https://www.india.gov.in/",
                1,
                1,
            ),
            (
                "Disability Helpline",
                "14456",
                "Disability-related support",
                "National disability helpline.",
                "https://depwd.gov.in/",
                1,
                1,
            ),
            (
                "National De-addiction Helpline",
                "1800-11-0031",
                "Substance-use / de-addiction support",
                "National de-addiction helpline.",
                "https://socialjustice.gov.in/",
                1,
                1,
            ),
        ]

        conn.executemany(
            """
            INSERT INTO emergency_helplines(
                name,
                number,
                use_text,
                description,
                official_url,
                available_24x7,
                active,
                created_at
            )
            VALUES (?,?,?,?,?,?,?,?)
            """,
            [
                (*item, datetime.now().isoformat(timespec="seconds"))
                for item in helplines
            ]
        )

    conn.commit()

    # =====================================================
    # CREATE / REPAIR ADMIN ACCOUNT
    # =====================================================

    admin_email = "admin@smarthealth.local"

    admin_password = generate_password_hash(
        "admin123"
    )

    admin = conn.execute(
        "SELECT id FROM users WHERE email=?",
        (admin_email,)
    ).fetchone()

    if admin:

        conn.execute(
            """
            UPDATE users
            SET name=?,
                role=?
            WHERE email=?
            """,
            (
                "System Admin",
                "admin",
                admin_email
            )
        )

    else:

        conn.execute(
            """
            INSERT INTO users
            (
                name,
                email,
                password,
                role,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "System Admin",
                admin_email,
                admin_password,
                "admin",
                datetime.now().isoformat(),
            )
        )

    conn.commit()
    conn.close()


# =========================================================
# MACHINE LEARNING MODEL
# =========================================================

def load_model():

    try:

        if not os.path.exists(MODEL_PATH):
            return None

        with open(MODEL_PATH, "rb") as file:
            return pickle.load(file)

    except Exception:
        return None


# Optional real LLM integration
try:
    from openai import OpenAI
except Exception:
    OpenAI = None


OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-5.6-luna"
)

MODEL = None


# =========================================================
# AUTHENTICATION
# =========================================================

def login_required(view):

    @wraps(view)
    def wrapped(*args, **kwargs):

        if "user_id" not in session:

            flash(
                "Please login to continue.",
                "warning"
            )

            return redirect(
                url_for("login")
            )

        return view(*args, **kwargs)

    return wrapped


def admin_required(view):

    @wraps(view)
    def wrapped(*args, **kwargs):

        if session.get("role") != "admin":

            flash(
                "Admin access required.",
                "danger"
            )

            return redirect(
                url_for("dashboard")
            )

        return view(*args, **kwargs)

    return wrapped


# =========================================================
# DISEASE PREDICTION
# =========================================================

def predict_disease(selected):

    """
    Educational/demo prediction only.

    The bundled model is trained on synthetic data and must
    not be used for real diagnosis or treatment decisions.
    """

    global MODEL

    if MODEL is None:
        MODEL = load_model()

    selected = set(selected)

    vector = [
        1 if symptom in selected else 0
        for symptom in SYMPTOMS
    ]

    # =====================================================
    # MACHINE LEARNING MODEL
    # =====================================================

    if MODEL is not None:

        try:

            prediction = MODEL.predict(
                [vector]
            )[0]

            probabilities = MODEL.predict_proba(
                [vector]
            )[0]

            confidence = float(
                max(probabilities) * 100
            )

            return (
                str(prediction),
                round(confidence, 1)
            )

        except Exception:
            pass

    # =====================================================
    # SAFE FALLBACK RULE SYSTEM
    # =====================================================

    rules = {

        "Common Cold": {
            "cough",
            "runny_nose",
            "sore_throat",
            "headache",
        },

        "Flu-like Illness": {
            "fever",
            "body_pain",
            "fatigue",
            "headache",
            "cough",
        },

        "Gastrointestinal Illness": {
            "nausea",
            "vomiting",
            "diarrhea",
            "abdominal_pain",
        },

        "Respiratory Illness": {
            "cough",
            "shortness_of_breath",
            "chest_pain",
        },

        "Possible Diabetes Risk": {
            "frequent_urination",
            "increased_thirst",
            "fatigue",
        },

        "Allergy-like Symptoms": {
            "skin_rash",
            "runny_nose",
            "sore_throat",
        },
    }

    scores = {}

    for disease, disease_symptoms in rules.items():

        scores[disease] = len(
            disease_symptoms.intersection(
                selected
            )
        )

    best = max(
        scores,
        key=scores.get
    )

    if scores[best] == 0:

        return (
            "Insufficient information",
            0.0
        )

    confidence = min(
        95.0,
        45 + scores[best] * 12
    )

    return (
        best,
        round(confidence, 1)
    )


# =========================================================
# PRO SERVICES
# =========================================================

def audit(action, target=""):

    if not session.get("user_id"):
        return

    conn = get_db()

    conn.execute(
        """
        INSERT INTO audit_logs(
            user_id,
            action,
            target,
            created_at
        )
        VALUES (?,?,?,?)
        """,
        (
            session["user_id"],
            action,
            target,
            datetime.now().isoformat(
                timespec="seconds"
            )
        )
    )

    conn.commit()
    conn.close()


def add_notification(
    user_id,
    title,
    message
):

    conn = get_db()

    conn.execute(
        """
        INSERT INTO notifications(
            user_id,
            title,
            message,
            created_at
        )
        VALUES (?,?,?,?)
        """,
        (
            user_id,
            title,
            message,
            datetime.now().isoformat(
                timespec="seconds"
            )
        )
    )

    conn.commit()
    conn.close()


# =========================================================
# PROFILE
# =========================================================

@app.route(
    "/profile",
    methods=["GET", "POST"]
)
@login_required
def profile():

    conn = get_db()

    if request.method == "POST":

        fields = {
            k: (
                request.form.get(k) or ""
            ).strip()

            for k in [
                "dob",
                "gender",
                "phone",
                "alternate_phone",
                "address",
                "city",
                "state",
                "pin_code",
                "blood_group",
                "allergies",
                "existing_conditions",
                "current_medications",
                "emergency_notes",
                "emergency_contact_name",
                "emergency_contact_relation",
                "emergency_contact_number",
                "preferred_language",
            ]
        }

        notifications = (
            1
            if request.form.get("notifications")
            else 0
        )

        consent = (
            1
            if request.form.get("consent")
            else 0
        )

        conn.execute(
            """
            INSERT INTO user_profiles(
                user_id,
                dob,
                gender,
                phone,
                alternate_phone,
                address,
                city,
                state,
                pin_code,
                blood_group,
                allergies,
                existing_conditions,
                current_medications,
                emergency_notes,
                emergency_contact_name,
                emergency_contact_relation,
                emergency_contact_number,
                preferred_language,
                notifications,
                consent
            )
            VALUES(
                ?,?,?,?,?,?,?,?,?,?,
                ?,?,?,?,?,?,?,?,?,?
            )
            ON CONFLICT(user_id)
            DO UPDATE SET
                dob=excluded.dob,
                gender=excluded.gender,
                phone=excluded.phone,
                alternate_phone=excluded.alternate_phone,
                address=excluded.address,
                city=excluded.city,
                state=excluded.state,
                pin_code=excluded.pin_code,
                blood_group=excluded.blood_group,
                allergies=excluded.allergies,
                existing_conditions=excluded.existing_conditions,
                current_medications=excluded.current_medications,
                emergency_notes=excluded.emergency_notes,
                emergency_contact_name=excluded.emergency_contact_name,
                emergency_contact_relation=excluded.emergency_contact_relation,
                emergency_contact_number=excluded.emergency_contact_number,
                preferred_language=excluded.preferred_language,
                notifications=excluded.notifications,
                consent=excluded.consent
            """,
            (
                session["user_id"],
                *fields.values(),
                notifications,
                consent
            )
        )

        conn.commit()
        conn.close()

        audit("Updated profile")

        flash(
            "Profile updated successfully.",
            "success"
        )

        return redirect(
            url_for("profile")
        )

    row = conn.execute(
        """
        SELECT
            u.name,
            u.email,
            p.*
        FROM users u
        LEFT JOIN user_profiles p
            ON u.id=p.user_id
        WHERE u.id=?
        """,
        (
            session["user_id"],
        )
    ).fetchone()

    conn.close()

    return render_template(
        "profile.html",
        profile=row
    )


# =========================================================
# NOTIFICATIONS
# =========================================================

@app.route(
    "/notifications",
    methods=["GET", "POST"]
)
@login_required
def notifications():

    user_id = session["user_id"]

    conn = get_db()

    if request.method == "POST":

        notification_id = request.form.get(
            "notification_id",
            type=int
        )

        if request.form.get(
            "mark_all"
        ) == "1":

            conn.execute(
                """
                UPDATE notifications
                SET is_read=1
                WHERE user_id=?
                """,
                (user_id,)
            )

            flash(
                "All notifications marked as read.",
                "success"
            )

        elif notification_id:

            conn.execute(
                """
                UPDATE notifications
                SET is_read=1
                WHERE id=?
                AND user_id=?
                """,
                (
                    notification_id,
                    user_id
                )
            )

            flash(
                "Notification marked as read.",
                "success"
            )

        conn.commit()
        conn.close()

        return redirect(
            url_for("notifications")
        )

    rows = conn.execute(
        """
        SELECT
            id,
            title,
            message,
            is_read,
            created_at
        FROM notifications
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT 100
        """,
        (user_id,)
    ).fetchall()

    unread = conn.execute(
        """
        SELECT COUNT(*) AS c
        FROM notifications
        WHERE user_id=?
        AND is_read=0
        """,
        (user_id,)
    ).fetchone()["c"]

    conn.close()

    return render_template(
        "notifications.html",
        notifications=rows,
        unread_count=unread
    )


@app.route(
    "/notifications/read/<int:notification_id>",
    methods=["POST", "GET"]
)
@login_required
def notification_read(
    notification_id
):

    conn = get_db()

    conn.execute(
        """
        UPDATE notifications
        SET is_read=1
        WHERE id=?
        AND user_id=?
        """,
        (
            notification_id,
            session["user_id"]
        )
    )

    conn.commit()
    conn.close()

    return redirect(
        url_for("notifications")
    )


# =========================================================
# DOCTOR DIRECTORY
# =========================================================

@app.route("/doctors")
def doctors():

    q = (
        request.args.get("q") or ""
    ).strip()

    district = (
        request.args.get("district") or ""
    ).strip()

    conn = get_db()

    where = [
        "COALESCE(show_in_directory,1)=1"
    ]

    params = []

    if q:

        like = f"%{q}%"

        where.append(
            """
            (
                name LIKE ?
                OR specialty LIKE ?
                OR hospital LIKE ?
                OR city LIKE ?
                OR district LIKE ?
                OR state LIKE ?
            )
            """
        )

        params.extend([
            like,
            like,
            like,
            like,
            like,
            like
        ])

    if district:

        where.append(
            "district = ?"
        )

        params.append(
            district
        )

    sql = """
        SELECT *
        FROM doctors
        WHERE
    """

    sql += " AND ".join(where)

    sql += """
        ORDER BY
            available DESC,
            name
    """

    rows = conn.execute(
        sql,
        params
    ).fetchall()

    districts = [
        row["district"]

        for row in conn.execute(
            """
            SELECT DISTINCT district
            FROM doctors
            WHERE district IS NOT NULL
            AND TRIM(district) != ''
            ORDER BY district
            """
        ).fetchall()
    ]

    conn.close()

    return render_template(
        "doctors.html",
        doctors=rows,
        query=q,
        district=district,
        districts=districts
    )


# =========================================================
# CHATBOT
# =========================================================

@app.route(
    "/chatbot",
    methods=["GET", "POST"]
)
def chatbot():

    return render_template(
        "chatbot.html"
    )


@app.route(
    "/api/chat",
    methods=["POST"]
)
def api_chat():

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    message = str(
        data.get(
            "message",
            ""
        )
    ).strip()[:3000]

    history = data.get(
        "history",
        []
    )

    if not message:

        return jsonify({
            "reply": "Please type a health question.",
            "risk": "low"
        })

    emergency_terms = [
        "chest pain",
        "difficulty breathing",
        "shortness of breath",
        "can't breathe",
        "cannot breathe",
        "unconscious",
        "severe bleeding",
        "stroke",
        "fainted",
        "seizure",
        "suicide",
        "self harm",
        "आत्महत्या",
        "सांस नहीं",
        "सीने में तेज दर्द",
    ]

    if any(
        term in message.lower()
        for term in emergency_terms
    ):

        return jsonify({
            "reply": (
                "⚠️ This may be an emergency. "
                "Please contact local emergency services "
                "or go to the nearest emergency department now. "
                "Do not rely on this chatbot for emergency diagnosis."
            ),
            "risk": "high"
        })

    # ---------------------------------------------------------
    # REAL LLM
    # ---------------------------------------------------------

    if (
        OpenAI is not None
        and os.getenv("OPENAI_API_KEY")
    ):

        try:

            client = OpenAI(
                api_key=os.getenv(
                    "OPENAI_API_KEY"
                )
            )

            lang = (
                "Hindi"
                if session.get(
                    "language"
                ) == "Hindi"
                else "English"
            )

            system = (
                f"You are SmartHealth AI, "
                f"an educational healthcare assistant. "
                f"Respond in {lang} unless the user asks "
                f"for another language. "
                f"Be concise but useful. "
                f"Do not diagnose, prescribe, "
                f"or claim certainty. "
                f"Explain symptoms, prevention, "
                f"general health information, "
                f"and what to discuss with a clinician. "
                f"For red-flag symptoms advise urgent medical care. "
                f"Never invent medical test results. "
                f"Mention that this is educational support "
                f"when appropriate."
            )

            msgs = [
                {
                    "role": "system",
                    "content": system
                }
            ]

            for item in history[-8:]:

                if (
                    isinstance(item, dict)
                    and item.get("role")
                    in ("user", "assistant")
                    and item.get("content")
                ):

                    msgs.append({
                        "role": item["role"],
                        "content": str(
                            item["content"]
                        )[:1500]
                    })

            msgs.append({
                "role": "user",
                "content": message
            })

            response = client.responses.create(
                model=OPENAI_MODEL,
                input=msgs,
                max_output_tokens=700
            )

            text = (
                getattr(
                    response,
                    "output_text",
                    None
                )
                or
                "I could not generate a response right now."
            )

            return jsonify({
                "reply": text,
                "risk": "low",
                "mode": "llm"
            })

        except Exception as exc:

            app.logger.exception(
                "OpenAI chat failed: %s",
                exc
            )

            return jsonify({
                "reply": (
                    "The AI service is temporarily unavailable. "
                    "Check OPENAI_API_KEY and your internet connection, "
                    "then try again."
                ),
                "risk": "error",
                "mode": "fallback"
            }), 503

    # ---------------------------------------------------------
    # SAFE LOCAL FALLBACK
    # ---------------------------------------------------------

    msg = message.lower()

    replies = []

    if any(
        x in msg
        for x in [
            "fever",
            "bukhar",
            "बुखार"
        ]
    ):

        replies.append(
            "For fever, monitor temperature, "
            "stay hydrated and rest. "
            "Persistent, very high, or worsening "
            "fever should be assessed by a clinician."
        )

    if any(
        x in msg
        for x in [
            "cough",
            "khansi",
            "खांसी"
        ]
    ):

        replies.append(
            "For cough, note duration and associated "
            "fever, wheezing or breathing difficulty. "
            "Persistent or worsening cough should be evaluated."
        )

    if any(
        x in msg
        for x in [
            "dengue",
            "mosquito"
        ]
    ):

        replies.append(
            "Dengue prevention includes avoiding mosquito "
            "bites and removing standing water. "
            "Suspected dengue needs medical evaluation."
        )

    if not replies:

        replies.append(
            "I can help with symptoms, prevention, "
            "disease information and questions to discuss "
            "with a doctor. For full AI chat, configure "
            "OPENAI_API_KEY in the environment."
        )

    return jsonify({
        "reply": " ".join(replies),
        "risk": "low",
        "mode": "local"
    })


# =========================================================
# ADMIN APPOINTMENT ACTION
# =========================================================

@app.route(
    "/admin/appointment/<int:appointment_id>/<action>"
)
@login_required
@admin_required
def appointment_action(
    appointment_id,
    action
):

    allowed = {
        "approve": "Approved",
        "reject": "Rejected",
        "complete": "Completed",
        "pending": "Pending"
    }

    if action not in allowed:

        flash(
            "Invalid appointment action.",
            "danger"
        )

        return redirect(
            url_for("admin")
        )

    conn = get_db()

    ap = conn.execute(
        """
        SELECT user_id
        FROM appointments
        WHERE id=?
        """,
        (appointment_id,)
    ).fetchone()

    if not ap:

        conn.close()

        flash(
            "Appointment not found.",
            "danger"
        )

        return redirect(
            url_for("admin")
        )

    conn.execute(
        """
        UPDATE appointments
        SET status=?
        WHERE id=?
        """,
        (
            allowed[action],
            appointment_id
        )
    )

    conn.commit()
    conn.close()

    add_notification(
        ap["user_id"],
        "Appointment Update",
        (
            f"Your appointment #{appointment_id} "
            f"is now {allowed[action]}."
        )
    )

    audit(
        f"Appointment {allowed[action]}",
        str(appointment_id)
    )

    flash(
        f"Appointment marked {allowed[action]}.",
        "success"
    )

    return redirect(
        url_for("admin")
    )


# =========================================================
# DELETE PATIENT
# =========================================================

@app.route(
    "/admin/delete-user/<int:user_id>"
)
@login_required
@admin_required
def delete_user(user_id):

    if user_id == session["user_id"]:

        flash(
            "You cannot delete your own admin account.",
            "danger"
        )

        return redirect(
            url_for("admin")
        )

    conn = get_db()

    conn.execute(
        """
        DELETE FROM health_records
        WHERE user_id=?
        """,
        (user_id,)
    )

    conn.execute(
        """
        DELETE FROM appointments
        WHERE user_id=?
        """,
        (user_id,)
    )

    conn.execute(
        """
        DELETE FROM notifications
        WHERE user_id=?
        """,
        (user_id,)
    )

    conn.execute(
        """
        DELETE FROM user_profiles
        WHERE user_id=?
        """,
        (user_id,)
    )

    conn.execute(
        """
        DELETE FROM users
        WHERE id=?
        AND role!='admin'
        """,
        (user_id,)
    )

    conn.commit()
    conn.close()

    audit(
        "Deleted patient",
        str(user_id)
    )

    flash(
        "Patient account deleted.",
        "success"
    )

    return redirect(
        url_for("admin")
    )


# =========================================================
# LANGUAGE
# =========================================================

@app.route(
    "/set-language/<lang>"
)
def set_language(lang):

    allowed = {
        "English",
        "Hindi"
    }

    if lang in allowed:
        session["language"] = lang

    return redirect(
        request.referrer
        or url_for("index")
    )


# =========================================================
# SITEMAP
# =========================================================

@app.route("/sitemap.xml")
def sitemap():

    pages = [
        url_for(
            "index",
            _external=True
        ),
        url_for(
            "disease_library",
            _external=True
        ),
        url_for(
            "doctors",
            _external=True
        ),
        url_for(
            "hospitals",
            _external=True
        ),
    ]

    pages += [
        url_for(
            "disease_detail",
            slug=d["slug"],
            _external=True
        )
        for d in DISEASES
    ]

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        +
        "".join(
            f"<url><loc>{p}</loc></url>"
            for p in pages
        )
        +
        "</urlset>"
    )

    return make_response(
        xml,
        200,
        {
            "Content-Type":
                "application/xml"
        }
    )


# =========================================================
# ROBOTS
# =========================================================

@app.route("/robots.txt")
def robots():

    text = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /dashboard\n"
        "Disallow: /profile\n"
        "Disallow: /history\n"
        "Disallow: /appointments\n"
        "Disallow: /admin\n"
        "Disallow: /health-report\n"
        "Disallow: /notifications\n"
        "Sitemap: "
        +
        url_for(
            "sitemap",
            _external=True
        )
        +
        "\n"
    )

    return make_response(
        text,
        200,
        {
            "Content-Type":
                "text/plain"
        }
    )


# =========================================================
# GLOBAL TEMPLATE VARIABLES
# =========================================================

def _notification_count():

    user_id = session.get(
        "user_id"
    )

    if not user_id:
        return 0

    try:

        conn = get_db()

        count = conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM notifications
            WHERE user_id=?
            AND is_read=0
            """,
            (user_id,)
        ).fetchone()["c"]

        conn.close()

        return int(count)

    except Exception:

        return 0


@app.context_processor
def inject_globals():

    return {

        "symptoms":
            SYMPTOMS,

        "symptom_labels":
            SYMPTOM_LABELS,

        "current_user":
            session.get("name"),

        "role":
            session.get("role"),

        "disease_count":
            len(DISEASES),

        "language":
            session.get(
                "language",
                "English"
            ),

        "openai_enabled":
            bool(
                os.getenv(
                    "OPENAI_API_KEY"
                )
            )
            and OpenAI is not None,

        "notification_count":
            _notification_count(),
    }


# =========================================================
# HOME
# =========================================================

@app.route("/")
def index():

    return render_template(
        "index.html"
    )


# =========================================================
# REGISTER
# =========================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        if (
            not name
            or not email
            or len(password) < 6
        ):

            flash(
                "Enter all details. Password must be at least 6 characters.",
                "danger"
            )

            return redirect(
                url_for("register")
            )

        conn = get_db()

        try:

            conn.execute(
                """
                INSERT INTO users
                (
                    name,
                    email,
                    password,
                    role,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    name,
                    email,
                    generate_password_hash(
                        password
                    ),
                    "patient",
                    datetime.now().isoformat(),
                )
            )

            conn.commit()

            flash(
                "Registration successful. Please login.",
                "success"
            )

        except sqlite3.IntegrityError:

            flash(
                "An account with this email already exists.",
                "danger"
            )

        finally:

            conn.close()

        return redirect(
            url_for("login")
        )

    return render_template(
        "register.html"
    )


# =========================================================
# LOGIN
# =========================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        conn = get_db()

        user = conn.execute(
            """
            SELECT *
            FROM users
            WHERE email=?
            """,
            (email,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]

            flash(
                "Welcome back!",
                "success"
            )

            if user["role"] == "admin":

                return redirect(
                    url_for("admin")
                )

            return redirect(
                url_for("dashboard")
            )

        flash(
            "Invalid email or password.",
            "danger"
        )

    return render_template(
        "login.html"
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("index")
    )


# =========================================================
# PATIENT DASHBOARD
# =========================================================

@app.route("/dashboard")
@login_required
def dashboard():

    conn = get_db()

    records = conn.execute(
        """
        SELECT *
        FROM health_records
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT 5
        """,
        (
            session["user_id"],
        )
    ).fetchall()

    appointments = conn.execute(
        """
        SELECT *
        FROM appointments
        WHERE user_id=?
        ORDER BY appointment_date DESC
        LIMIT 5
        """,
        (
            session["user_id"],
        )
    ).fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        records=records,
        appointments=appointments
    )
    # =========================================================
# PREDICTION PAGE
# =========================================================

@app.route(
    "/predict",
    methods=["GET", "POST"]
)
@login_required
def predict():

    if request.method == "POST":

        age = request.form.get(
            "age",
            type=int
        )

        gender = (
            request.form.get(
                "gender"
            )
            or ""
        ).strip()

        height = request.form.get(
            "height",
            type=float
        )

        weight = request.form.get(
            "weight",
            type=float
        )

        blood_pressure = (
            request.form.get(
                "blood_pressure"
            )
            or ""
        ).strip()

        glucose = request.form.get(
            "glucose",
            type=float
        )

        selected_symptoms = request.form.getlist(
            "symptoms"
        )

        # Remove invalid symptoms
        selected_symptoms = [
            s for s in selected_symptoms
            if s in SYMPTOMS
        ]

        if not selected_symptoms:

            flash(
                "Please select at least one symptom.",
                "warning"
            )

            return redirect(
                url_for("predict")
            )

        prediction, confidence = predict_disease(
            selected_symptoms
        )

        conn = get_db()

        conn.execute(
            """
            INSERT INTO health_records(
                user_id,
                age,
                gender,
                height,
                weight,
                blood_pressure,
                glucose,
                symptoms,
                prediction,
                confidence,
                created_at
            )
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                session["user_id"],
                age,
                gender,
                height,
                weight,
                blood_pressure,
                glucose,
                ", ".join(
                    selected_symptoms
                ),
                prediction,
                confidence,
                datetime.now().isoformat(
                    timespec="seconds"
                )
            )
        )

        conn.commit()
        conn.close()

        audit(
            "Disease prediction",
            prediction
        )

        return render_template(
            "result.html",
            prediction=prediction,
            confidence=confidence,
            symptoms=selected_symptoms,
            age=age,
            gender=gender,
            height=height,
            weight=weight,
            blood_pressure=blood_pressure,
            glucose=glucose
        )

    return render_template(
        "predict.html"
    )


# =========================================================
# API PREDICTION
# =========================================================

@app.route(
    "/api/predict",
    methods=["POST"]
)
@login_required
def api_predict():

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    selected_symptoms = data.get(
        "symptoms",
        []
    )

    if isinstance(
        selected_symptoms,
        str
    ):
        selected_symptoms = [
            selected_symptoms
        ]

    selected_symptoms = [
        s for s in selected_symptoms
        if s in SYMPTOMS
    ]

    if not selected_symptoms:

        return jsonify({
            "error":
                "At least one symptom is required."
        }), 400

    prediction, confidence = predict_disease(
        selected_symptoms
    )

    return jsonify({
        "prediction": prediction,
        "confidence": confidence,
        "educational_only": True
    })


# =========================================================
# HEALTH HISTORY
# =========================================================

@app.route("/history")
@login_required
def history():

    conn = get_db()

    records = conn.execute(
        """
        SELECT *
        FROM health_records
        WHERE user_id=?
        ORDER BY id DESC
        """,
        (
            session["user_id"],
        )
    ).fetchall()

    conn.close()

    return render_template(
        "history.html",
        records=records
    )


# =========================================================
# APPOINTMENTS
# =========================================================

@app.route(
    "/appointments",
    methods=["GET", "POST"]
)
@login_required
def appointments():

    conn = get_db()

    if request.method == "POST":

        doctor_name = (
            request.form.get(
                "doctor_name"
            )
            or ""
        ).strip()

        appointment_date = (
            request.form.get(
                "appointment_date"
            )
            or ""
        ).strip()

        reason = (
            request.form.get(
                "reason"
            )
            or ""
        ).strip()

        if not doctor_name or not appointment_date:

            conn.close()

            flash(
                "Doctor and appointment date are required.",
                "danger"
            )

            return redirect(
                url_for("appointments")
            )

        conn.execute(
            """
            INSERT INTO appointments(
                user_id,
                doctor_name,
                appointment_date,
                reason,
                status,
                created_at
            )
            VALUES(?,?,?,?,?,?)
            """,
            (
                session["user_id"],
                doctor_name,
                appointment_date,
                reason,
                "Pending",
                datetime.now().isoformat(
                    timespec="seconds"
                )
            )
        )

        conn.commit()

        conn.close()

        audit(
            "Created appointment",
            doctor_name
        )

        flash(
            "Appointment request submitted.",
            "success"
        )

        return redirect(
            url_for("appointments")
        )

    rows = conn.execute(
        """
        SELECT *
        FROM appointments
        WHERE user_id=?
        ORDER BY appointment_date DESC
        """,
        (
            session["user_id"],
        )
    ).fetchall()

    conn.close()

    return render_template(
        "appointments.html",
        appointments=rows
    )


# =========================================================
# DISEASE LIBRARY
# =========================================================

@app.route("/diseases")
@app.route("/disease-library")
def disease_library():

    q = (
        request.args.get(
            "q"
        )
        or ""
    ).strip().lower()

    diseases = DISEASES

    if q:

        diseases = [
            d for d in DISEASES
            if q in str(
                d.get("name", "")
            ).lower()
            or q in str(
                d.get("slug", "")
            ).lower()
            or q in str(
                d.get("description", "")
            ).lower()
            or any(
                q in str(x).lower()
                for x in d.get(
                    "symptoms",
                    []
                )
            )
        ]

    return render_template(
        "diseases.html",
        diseases=diseases,
        query=q
    )


# =========================================================
# DISEASE DETAIL
# =========================================================

@app.route(
    "/diseases/<slug>"
)
def disease_detail(slug):

    disease = DISEASES_BY_SLUG.get(
        slug
    )

    if not disease:

        return render_template(
            "404.html"
        ), 404

    return render_template(
        "disease_detail.html",
        disease=disease
    )


# =========================================================
# HOSPITAL FINDER
# =========================================================

@app.route("/hospitals")
def hospitals():

    return render_template(
        "hospitals.html"
    )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin")
@login_required
@admin_required
def admin():

    conn = get_db()

    users = conn.execute(
        """
        SELECT
            id,
            name,
            email,
            role,
            created_at
        FROM users
        ORDER BY id DESC
        """
    ).fetchall()

    records = conn.execute(
        """
        SELECT
            hr.*,
            u.name AS user_name,
            u.email AS user_email
        FROM health_records hr
        JOIN users u
            ON u.id=hr.user_id
        ORDER BY hr.id DESC
        LIMIT 100
        """
    ).fetchall()

    appointments = conn.execute(
        """
        SELECT
            a.*,
            u.name AS user_name,
            u.email AS user_email
        FROM appointments a
        JOIN users u
            ON u.id=a.user_id
        ORDER BY a.id DESC
        LIMIT 100
        """
    ).fetchall()

    user_count = conn.execute(
        """
        SELECT COUNT(*) AS c
        FROM users
        WHERE role='patient'
        """
    ).fetchone()["c"]

    prediction_count = conn.execute(
        """
        SELECT COUNT(*) AS c
        FROM health_records
        """
    ).fetchone()["c"]

    appointment_count = conn.execute(
        """
        SELECT COUNT(*) AS c
        FROM appointments
        """
    ).fetchone()["c"]

    doctor_count = conn.execute(
        """
        SELECT COUNT(*) AS c
        FROM doctors
        """
    ).fetchone()["c"]

    conn.close()

    return render_template(
        "admin.html",
        users=users,
        records=records,
        appointments=appointments,
        user_count=user_count,
        prediction_count=prediction_count,
        appointment_count=appointment_count,
        doctor_count=doctor_count
    )


# =========================================================
# ADMIN PASSWORD CHANGE
# =========================================================

@app.route(
    "/admin/change-password",
    methods=["GET", "POST"]
)
@login_required
@admin_required
def admin_change_password():

    if request.method == "POST":

        current_password = request.form.get(
            "current_password",
            ""
        )

        new_password = request.form.get(
            "new_password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        conn = get_db()

        admin_user = conn.execute(
            """
            SELECT password
            FROM users
            WHERE id=?
            """,
            (
                session["user_id"],
            )
        ).fetchone()

        if not admin_user:

            conn.close()

            flash(
                "Admin account not found.",
                "danger"
            )

            return redirect(
                url_for("admin")
            )

        if not check_password_hash(
            admin_user["password"],
            current_password
        ):

            conn.close()

            flash(
                "Current password is incorrect.",
                "danger"
            )

            return redirect(
                url_for(
                    "admin_change_password"
                )
            )

        if len(new_password) < 10:

            conn.close()

            flash(
                "New password must contain at least 10 characters.",
                "danger"
            )

            return redirect(
                url_for(
                    "admin_change_password"
                )
            )

        if new_password != confirm_password:

            conn.close()

            flash(
                "New passwords do not match.",
                "danger"
            )

            return redirect(
                url_for(
                    "admin_change_password"
                )
            )

        conn.execute(
            """
            UPDATE users
            SET password=?
            WHERE id=?
            """,
            (
                generate_password_hash(
                    new_password
                ),
                session["user_id"]
            )
        )

        conn.commit()
        conn.close()

        audit(
            "Changed admin password"
        )

        flash(
            "Admin password changed successfully.",
            "success"
        )

        return redirect(
            url_for("admin")
        )

    return render_template(
        "admin_change_password.html"
    )


# =========================================================
# EMERGENCY MODULE
# =========================================================

EMERGENCY_STATUSES = [
    "Request Sent",
    "Hospital Preparing",
    "Accepted",
    "Arrived",
    "Admitted"
]


# =========================================================
# EMERGENCY MAIN PAGE
# =========================================================

@app.route("/emergency")
def emergency():

    conn = get_db()

    helplines = conn.execute(
        """
        SELECT *
        FROM emergency_helplines
        WHERE active=1
        ORDER BY id
        """
    ).fetchall()

    emergency_doctors = conn.execute(
        """
        SELECT *
        FROM doctors
        WHERE COALESCE(show_in_emergency,0)=1
        ORDER BY
            emergency_available DESC,
            available DESC,
            name
        """
    ).fetchall()

    hospitals = conn.execute(
        """
        SELECT *
        FROM emergency_hospitals
        WHERE active=1
        ORDER BY
            emergency_available DESC,
            name
        """
    ).fetchall()

    conn.close()

    return render_template(
        "emergency.html",
        helplines=helplines,
        emergency_doctors=emergency_doctors,
        hospitals=hospitals,
        emergency_statuses=EMERGENCY_STATUSES
    )


# =========================================================
# EMERGENCY ADMISSION REQUEST
# =========================================================

@app.route(
    "/emergency/admission",
    methods=["GET", "POST"]
)
@login_required
def emergency_admission():

    if request.method == "POST":

        fields = [
            "patient_name",
            "age",
            "dob",
            "gender",
            "mobile",
            "emergency_contact",
            "blood_group",
            "address",
            "emergency_problem",
            "existing_conditions",
            "medicines",
            "allergies",
            "emergency_notes",
            "preferred_hospital"
        ]

        data = {}

        for field in fields:

            data[field] = (
                request.form.get(
                    field
                )
                or ""
            ).strip()

        consent = (
            1
            if request.form.get(
                "consent"
            )
            else 0
        )

        if not data["patient_name"]:

            flash(
                "Patient name is required.",
                "danger"
            )

            return redirect(
                url_for(
                    "emergency_admission"
                )
            )

        if not data["emergency_problem"]:

            flash(
                "Please describe the emergency problem.",
                "danger"
            )

            return redirect(
                url_for(
                    "emergency_admission"
                )
            )

        if not consent:

            flash(
                "Please confirm the emergency information consent.",
                "warning"
            )

            return redirect(
                url_for(
                    "emergency_admission"
                )
            )

        now = datetime.now().isoformat(
            timespec="seconds"
        )

        conn = get_db()

        cursor = conn.execute(
            """
            INSERT INTO emergency_admissions(
                user_id,
                patient_name,
                age,
                dob,
                gender,
                mobile,
                emergency_contact,
                blood_group,
                address,
                emergency_problem,
                existing_conditions,
                medicines,
                allergies,
                emergency_notes,
                preferred_hospital,
                consent,
                status,
                created_at,
                updated_at
            )
            VALUES(
                ?,?,?,?,?,?,?,?,?,?,
                ?,?,?,?,?,?,?,?,?
            )
            """,
            (
                session["user_id"],
                data["patient_name"],
                data["age"],
                data["dob"],
                data["gender"],
                data["mobile"],
                data["emergency_contact"],
                data["blood_group"],
                data["address"],
                data["emergency_problem"],
                data["existing_conditions"],
                data["medicines"],
                data["allergies"],
                data["emergency_notes"],
                data["preferred_hospital"],
                consent,
                "Request Sent",
                now,
                now
            )
        )

        admission_id = cursor.lastrowid

        conn.commit()
        conn.close()

        audit(
            "Emergency admission request",
            str(admission_id)
        )

        flash(
            "Emergency admission request created. Please contact emergency services immediately for life-threatening situations.",
            "success"
        )

        return redirect(
            url_for(
                "emergency_request",
                admission_id=admission_id
            )
        )

    conn = get_db()

    hospitals = conn.execute(
        """
        SELECT *
        FROM emergency_hospitals
        WHERE active=1
        ORDER BY
            emergency_available DESC,
            name
        """
    ).fetchall()

    conn.close()

    return render_template(
        "emergency_admission.html",
        hospitals=hospitals
    )


# =========================================================
# EMERGENCY REQUEST STATUS
# =========================================================

@app.route(
    "/emergency/request/<int:admission_id>"
)
@login_required
def emergency_request(admission_id):

    conn = get_db()

    row = conn.execute(
        """
        SELECT *
        FROM emergency_admissions
        WHERE id=?
        AND user_id=?
        """,
        (
            admission_id,
            session["user_id"]
        )
    ).fetchone()

    conn.close()

    if not row:

        flash(
            "Emergency request not found.",
            "danger"
        )

        return redirect(
            url_for("emergency")
        )

    return render_template(
        "emergency_request.html",
        request_data=row,
        statuses=EMERGENCY_STATUSES
    )


# =========================================================
# PATIENT EMERGENCY REQUEST HISTORY
# =========================================================

@app.route(
    "/emergency/my-requests"
)
@login_required
def emergency_my_requests():

    conn = get_db()

    rows = conn.execute(
        """
        SELECT *
        FROM emergency_admissions
        WHERE user_id=?
        ORDER BY id DESC
        """,
        (
            session["user_id"],
        )
    ).fetchall()

    conn.close()

    return render_template(
        "emergency_requests.html",
        requests=rows,
        statuses=EMERGENCY_STATUSES
    )


# =========================================================
# EMERGENCY VOICE PARSER
# =========================================================

@app.route(
    "/api/emergency/voice",
    methods=["POST"]
)
@login_required
def emergency_voice():

    data = (
        request.get_json(
            silent=True
        )
        or {}
    )

    transcript = str(
        data.get(
            "transcript",
            ""
        )
    ).strip()

    if not transcript:

        return jsonify({
            "error":
                "No transcript was provided."
        }), 400

    text = transcript.lower()

    detected = {}

    # -----------------------------------------------------
    # NAME
    # -----------------------------------------------------

    import re

    name_patterns = [
        r"(?:my name is|name is|mera naam|मेरा नाम)\s+([a-zA-Z][a-zA-Z .'-]{1,60})",
    ]

    for pattern in name_patterns:

        match = re.search(
            pattern,
            transcript,
            re.IGNORECASE
        )

        if match:

            detected["patient_name"] = (
                match.group(1)
                .strip()
            )

            break

    # -----------------------------------------------------
    # AGE
    # -----------------------------------------------------

    age_match = re.search(
        r"(?:age|umar|उम्र)\s*(?:is|hai|है)?\s*(\d{1,3})",
        text,
        re.IGNORECASE
    )

    if age_match:

        detected["age"] = age_match.group(1)

    # -----------------------------------------------------
    # PHONE
    # -----------------------------------------------------

    phone_match = re.search(
        r"(?:\+91[\s-]?)?[6-9]\d{9}",
        transcript
    )

    if phone_match:

        detected["mobile"] = (
            phone_match.group(0)
            .strip()
        )

    # -----------------------------------------------------
    # GENDER
    # -----------------------------------------------------

    if any(
        x in text
        for x in [
            "male",
            "man",
            "पुरुष",
            "आदमी"
        ]
    ):

        detected["gender"] = "Male"

    elif any(
        x in text
        for x in [
            "female",
            "woman",
            "महिला",
            "औरत"
        ]
    ):

        detected["gender"] = "Female"

    # -----------------------------------------------------
    # BLOOD GROUP
    # -----------------------------------------------------

    blood_match = re.search(
        r"\b(A|B|AB|O)\s*(positive|negative|\+|-)\b",
        transcript,
        re.IGNORECASE
    )

    if blood_match:

        group = (
            blood_match.group(1).upper()
        )

        sign = blood_match.group(2).lower()

        if sign in [
            "positive",
            "+"
        ]:
            sign = "+"

        else:
            sign = "-"

        detected["blood_group"] = (
            group + sign
        )

    # -----------------------------------------------------
    # EMERGENCY PROBLEM
    # -----------------------------------------------------

    problem_keywords = [
        "chest pain",
        "breathing",
        "shortness of breath",
        "bleeding",
        "unconscious",
        "accident",
        "injury",
        "stroke",
        "seizure",
        "poison",
        "burn",
        "heart attack",
        "सीने में दर्द",
        "सांस",
        "खून",
        "बेहोश",
        "दुर्घटना",
        "चोट",
        "दौरा",
        "जहर",
        "जलना",
    ]

    found_problems = [
        keyword
        for keyword in problem_keywords
        if keyword in text
    ]

    if found_problems:

        detected[
            "emergency_problem"
        ] = transcript

    # -----------------------------------------------------
    # NEVER INVENT MISSING DATA
    # -----------------------------------------------------

    missing = [
        field
        for field in [
            "patient_name",
            "age",
            "gender",
            "emergency_problem"
        ]
        if not detected.get(field)
    ]

    return jsonify({
        "detected": detected,
        "missing": missing,
        "requires_review": True,
        "source": "user_voice_transcript"
    })


# =========================================================
# ADMIN EMERGENCY DASHBOARD
# =========================================================

@app.route(
    "/admin/emergency"
)
@login_required
@admin_required
def admin_emergency():

    conn = get_db()

    helplines = conn.execute(
        """
        SELECT *
        FROM emergency_helplines
        ORDER BY id DESC
        """
    ).fetchall()

    hospitals = conn.execute(
        """
        SELECT *
        FROM emergency_hospitals
        ORDER BY id DESC
        """
    ).fetchall()

    doctors = conn.execute(
        """
        SELECT *
        FROM doctors
        WHERE COALESCE(show_in_emergency,0)=1
        ORDER BY id DESC
        """
    ).fetchall()

    admissions = conn.execute(
        """
        SELECT
            ea.*,
            u.name AS account_name,
            u.email AS account_email
        FROM emergency_admissions ea
        LEFT JOIN users u
            ON u.id=ea.user_id
        ORDER BY ea.id DESC
        LIMIT 200
        """
    ).fetchall()

    conn.close()

    return render_template(
        "admin_emergency.html",
        helplines=helplines,
        hospitals=hospitals,
        doctors=doctors,
        admissions=admissions,
        statuses=EMERGENCY_STATUSES
    )


# =========================================================
# ADMIN EMERGENCY HELPLINE SAVE
# =========================================================

@app.route(
    "/admin/emergency/helpline/save",
    methods=["POST"]
)
@login_required
@admin_required
def admin_emergency_helpline_save():

    helpline_id = request.form.get(
        "id",
        type=int
    )

    name = (
        request.form.get(
            "name"
        )
        or ""
    ).strip()

    number = (
        request.form.get(
            "number"
        )
        or ""
    ).strip()

    use_text = (
        request.form.get(
            "use_text"
        )
        or ""
    ).strip()

    description = (
        request.form.get(
            "description"
        )
        or ""
    ).strip()

    official_url = (
        request.form.get(
            "official_url"
        )
        or ""
    ).strip()

    available_24x7 = (
        1
        if request.form.get(
            "available_24x7"
        )
        else 0
    )

    active = (
        1
        if request.form.get(
            "active"
        )
        else 0
    )

    if not name or not number:

        flash(
            "Helpline name and number are required.",
            "danger"
        )

        return redirect(
            url_for("admin_emergency")
        )

    conn = get_db()

    if helpline_id:

        conn.execute(
            """
            UPDATE emergency_helplines
            SET
                name=?,
                number=?,
                use_text=?,
                description=?,
                official_url=?,
                available_24x7=?,
                active=?
            WHERE id=?
            """,
            (
                name,
                number,
                use_text,
                description,
                official_url,
                available_24x7,
                active,
                helpline_id
            )
        )

        action = "Updated emergency helpline"

    else:

        conn.execute(
            """
            INSERT INTO emergency_helplines(
                name,
                number,
                use_text,
                description,
                official_url,
                available_24x7,
                active,
                created_at
            )
            VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                name,
                number,
                use_text,
                description,
                official_url,
                available_24x7,
                active,
                datetime.now().isoformat(
                    timespec="seconds"
                )
            )
        )

        action = "Added emergency helpline"

    conn.commit()
    conn.close()

    audit(
        action,
        name
    )

    flash(
        "Emergency helpline saved successfully.",
        "success"
    )

    return redirect(
        url_for("admin_emergency")
    )


# =========================================================
# ADMIN EMERGENCY HELPLINE DELETE
# =========================================================

@app.route(
    "/admin/emergency/helpline/delete/<int:helpline_id>",
    methods=["POST", "GET"]
)
@login_required
@admin_required
def admin_emergency_helpline_delete(
    helpline_id
):

    conn = get_db()

    row = conn.execute(
        """
        SELECT name
        FROM emergency_helplines
        WHERE id=?
        """,
        (helpline_id,)
    ).fetchone()

    conn.execute(
        """
        DELETE FROM emergency_helplines
        WHERE id=?
        """,
        (helpline_id,)
    )

    conn.commit()
    conn.close()

    if row:

        audit(
            "Deleted emergency helpline",
            row["name"]
        )

    flash(
        "Emergency helpline deleted.",
        "success"
    )

    return redirect(
        url_for("admin_emergency")
    )


# =========================================================
# ADMIN EMERGENCY HOSPITAL SAVE
# =========================================================

@app.route(
    "/admin/emergency/hospital/save",
    methods=["POST"]
)
@login_required
@admin_required
def admin_emergency_hospital_save():

    hospital_id = request.form.get(
        "id",
        type=int
    )

    data = {
        field: (
            request.form.get(
                field
            )
            or ""
        ).strip()

        for field in [
            "name",
            "city",
            "district",
            "state",
            "address",
            "emergency_contact",
            "official_url",
            "map_url"
        ]
    }

    emergency_available = (
        1
        if request.form.get(
            "emergency_available"
        )
        else 0
    )

    active = (
        1
        if request.form.get(
            "active"
        )
        else 0
    )

    if not data["name"]:

        flash(
            "Hospital name is required.",
            "danger"
        )

        return redirect(
            url_for("admin_emergency")
        )

    conn = get_db()

    if hospital_id:

        conn.execute(
            """
            UPDATE emergency_hospitals
            SET
                name=?,
                city=?,
                district=?,
                state=?,
                address=?,
                emergency_contact=?,
                emergency_available=?,
                official_url=?,
                map_url=?,
                active=?
            WHERE id=?
            """,
            (
                data["name"],
                data["city"],
                data["district"],
                data["state"],
                data["address"],
                data["emergency_contact"],
                emergency_available,
                data["official_url"],
                data["map_url"],
                active,
                hospital_id
            )
        )

        action = "Updated emergency hospital"

    else:

        conn.execute(
            """
            INSERT INTO emergency_hospitals(
                name,
                city,
                district,
                state,
                address,
                emergency_contact,
                emergency_available,
                official_url,
                map_url,
                active,
                created_at
            )
            VALUES(?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                data["name"],
                data["city"],
                data["district"],
                data["state"],
                data["address"],
                data["emergency_contact"],
                emergency_available,
                data["official_url"],
                data["map_url"],
                active,
                datetime.now().isoformat(
                    timespec="seconds"
                )
            )
        )

        action = "Added emergency hospital"

    conn.commit()
    conn.close()

    audit(
        action,
        data["name"]
    )

    flash(
        "Emergency hospital saved successfully.",
        "success"
    )

    return redirect(
        url_for("admin_emergency")
    )


# =========================================================
# ADMIN EMERGENCY HOSPITAL DELETE
# =========================================================

@app.route(
    "/admin/emergency/hospital/delete/<int:hospital_id>",
    methods=["POST", "GET"]
)
@login_required
@admin_required
def admin_emergency_hospital_delete(
    hospital_id
):

    conn = get_db()

    row = conn.execute(
        """
        SELECT name
        FROM emergency_hospitals
        WHERE id=?
        """,
        (hospital_id,)
    ).fetchone()

    conn.execute(
        """
        DELETE FROM emergency_hospitals
        WHERE id=?
        """,
        (hospital_id,)
    )

    conn.commit()
    conn.close()

    if row:

        audit(
            "Deleted emergency hospital",
            row["name"]
        )

    flash(
        "Emergency hospital deleted.",
        "success"
    )

    return redirect(
        url_for("admin_emergency")
    )


# =========================================================
# ADMIN EMERGENCY DOCTOR SAVE
# =========================================================

@app.route(
    "/admin/emergency/doctor/save",
    methods=["POST"]
)
@login_required
@admin_required
def admin_emergency_doctor_save():

    doctor_id = request.form.get(
        "id",
        type=int
    )

    data = {
        field: (
            request.form.get(
                field
            )
            or ""
        ).strip()

        for field in [
            "name",
            "specialty",
            "hospital",
            "city",
            "district",
            "state",
            "languages",
            "contact",
            "source_url",
            "emergency_hours"
        ]
    }

    experience = request.form.get(
        "experience",
        type=int
    ) or 0

    available = (
        1
        if request.form.get(
            "available"
        )
        else 0
    )

    show_in_directory = (
        1
        if request.form.get(
            "show_in_directory"
        )
        else 0
    )

    show_in_emergency = (
        1
        if request.form.get(
            "show_in_emergency"
        )
        else 0
    )

    emergency_available = (
        1
        if request.form.get(
            "emergency_available"
        )
        else 0
    )

    photo_permission = (
        1
        if request.form.get(
            "photo_permission"
        )
        else 0
    )

    if not data["name"] or not data["specialty"]:

        flash(
            "Doctor name and specialty are required.",
            "danger"
        )

        return redirect(
            url_for("admin_emergency")
        )

    # -----------------------------------------------------
    # PHOTO UPLOAD
    # -----------------------------------------------------

    photo_url = ""

    photo = request.files.get(
        "photo"
    )

    if photo and photo.filename:

        if not photo_permission:

            flash(
                "Photo upload requires authorization/permission confirmation.",
                "danger"
            )

            return redirect(
                url_for("admin_emergency")
            )

        filename = photo.filename

        extension = (
            filename.rsplit(
                ".",
                1
            )[-1].lower()
            if "." in filename
            else ""
        )

        allowed_extensions = {
            "jpg",
            "jpeg",
            "png",
            "webp"
        }

        if extension not in allowed_extensions:

            flash(
                "Only JPG, JPEG, PNG and WEBP images are allowed.",
                "danger"
            )

            return redirect(
                url_for("admin_emergency")
            )

        upload_dir = os.path.join(
            BASE_DIR,
            "static",
            "uploads",
            "doctors"
        )

        os.makedirs(
            upload_dir,
            exist_ok=True
        )

        safe_name = (
            f"doctor_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.{extension}"
        )

        save_path = os.path.join(
            upload_dir,
            safe_name
        )

        photo.save(
            save_path
        )

        photo_url = (
            "/static/uploads/doctors/"
            + safe_name
        )

    conn = get_db()

    if doctor_id:

        if photo_url:

            conn.execute(
                """
                UPDATE doctors
                SET
                    name=?,
                    specialty=?,
                    hospital=?,
                    city=?,
                    district=?,
                    state=?,
                    experience=?,
                    languages=?,
                    available=?,
                    contact=?,
                    source_url=?,
                    photo_url=?,
                    show_in_directory=?,
                    show_in_emergency=?,
                    emergency_available=?,
                    emergency_hours=?
                WHERE id=?
                """,
                (
                    data["name"],
                    data["specialty"],
                    data["hospital"],
                    data["city"],
                    data["district"],
                    data["state"],
                    experience,
                    data["languages"],
                    available,
                    data["contact"],
                    data["source_url"],
                    photo_url,
                    show_in_directory,
                    show_in_emergency,
                    emergency_available,
                    data["emergency_hours"],
                    doctor_id
                )
            )

        else:

            conn.execute(
                """
                UPDATE doctors
                SET
                    name=?,
                    specialty=?,
                    hospital=?,
                    city=?,
                    district=?,
                    state=?,
                    experience=?,
                    languages=?,
                    available=?,
                    contact=?,
                    source_url=?,
                    show_in_directory=?,
                    show_in_emergency=?,
                    emergency_available=?,
                    emergency_hours=?
                WHERE id=?
                """,
                (
                    data["name"],
                    data["specialty"],
                    data["hospital"],
                    data["city"],
                    data["district"],
                    data["state"],
                    experience,
                    data["languages"],
                    available,
                    data["contact"],
                    data["source_url"],
                    show_in_directory,
                    show_in_emergency,
                    emergency_available,
                    data["emergency_hours"],
                    doctor_id
                )
            )

        action = "Updated emergency doctor"

    else:

        conn.execute(
            """
            INSERT INTO doctors(
                name,
                specialty,
                hospital,
                city,
                district,
                state,
                experience,
                languages,
                available,
                contact,
                source_url,
                photo_url,
                show_in_directory,
                show_in_emergency,
                emergency_available,
                emergency_hours
            )
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                data["name"],
                data["specialty"],
                data["hospital"],
                data["city"],
                data["district"],
                data["state"],
                experience,
                data["languages"],
                available,
                data["contact"],
                data["source_url"],
                photo_url,
                show_in_directory,
                show_in_emergency,
                emergency_available,
                data["emergency_hours"]
            )
        )

        action = "Added emergency doctor"

    conn.commit()
    conn.close()

    audit(
        action,
        data["name"]
    )

    flash(
        "Emergency doctor saved successfully.",
        "success"
    )

    return redirect(
        url_for("admin_emergency")
    )


# =========================================================
# ADMIN EMERGENCY DOCTOR DELETE
# =========================================================

@app.route(
    "/admin/emergency/doctor/delete/<int:doctor_id>",
    methods=["POST", "GET"]
)
@login_required
@admin_required
def admin_emergency_doctor_delete(
    doctor_id
):

    conn = get_db()

    row = conn.execute(
        """
        SELECT name
        FROM doctors
        WHERE id=?
        """,
        (doctor_id,)
    ).fetchone()

    conn.execute(
        """
        DELETE FROM doctors
        WHERE id=?
        """,
        (doctor_id,)
    )

    conn.commit()
    conn.close()

    if row:

        audit(
            "Deleted emergency doctor",
            row["name"]
        )

    flash(
        "Emergency doctor deleted.",
        "success"
    )

    return redirect(
        url_for("admin_emergency")
    )


# =========================================================
# ADMIN EMERGENCY ADMISSION STATUS
# =========================================================

@app.route(
    "/admin/emergency/admission/<int:admission_id>/<status>",
    methods=["POST", "GET"]
)
@login_required
@admin_required
def admin_emergency_admission_status(
    admission_id,
    status
):

    if status not in EMERGENCY_STATUSES:

        flash(
            "Invalid emergency status.",
            "danger"
        )

        return redirect(
            url_for("admin_emergency")
        )

    conn = get_db()

    row = conn.execute(
        """
        SELECT user_id
        FROM emergency_admissions
        WHERE id=?
        """,
        (admission_id,)
    ).fetchone()

    if not row:

        conn.close()

        flash(
            "Emergency request not found.",
            "danger"
        )

        return redirect(
            url_for("admin_emergency")
        )

    conn.execute(
        """
        UPDATE emergency_admissions
        SET
            status=?,
            updated_at=?
        WHERE id=?
        """,
        (
            status,
            datetime.now().isoformat(
                timespec="seconds"
            ),
            admission_id
        )
    )

    conn.commit()
    conn.close()

    if row["user_id"]:

        add_notification(
            row["user_id"],
            "Emergency Request Update",
            (
                f"Emergency request #{admission_id} "
                f"is now: {status}."
            )
        )

    audit(
        "Updated emergency admission status",
        f"{admission_id}: {status}"
    )

    flash(
        f"Emergency request updated to {status}.",
        "success"
    )

    return redirect(
        url_for("admin_emergency")
    )
    # =========================================================
# ERROR HANDLERS
# =========================================================

@app.errorhandler(404)
def page_not_found(error):

    try:
        return render_template(
            "404.html"
        ), 404
    except Exception:
        return (
            "404 - Page Not Found",
            404
        )


@app.errorhandler(413)
def request_entity_too_large(error):

    flash(
        "Uploaded file is too large. Please use a smaller file.",
        "danger"
    )

    return redirect(
        request.referrer
        or url_for("admin_emergency")
    )


@app.errorhandler(500)
def internal_server_error(error):

    app.logger.exception(
        "Internal server error: %s",
        error
    )

    try:

        return render_template(
            "500.html"
        ), 500

    except Exception:

        return (
            "500 - Internal Server Error",
            500
        )


# =========================================================
# APPLICATION HEALTH CHECK
# =========================================================

@app.route("/health")
def health():

    try:

        conn = get_db()

        conn.execute(
            "SELECT 1"
        ).fetchone()

        conn.close()

        return jsonify({
            "status": "ok",
            "service": "Smart Healthcare Management & Disease Prediction System"
        })

    except Exception as exc:

        app.logger.exception(
            "Health check failed: %s",
            exc
        )

        return jsonify({
            "status": "error"
        }), 500


# =========================================================
# EMERGENCY HEALTH CHECK
# =========================================================

@app.route("/api/emergency/status/<int:admission_id>")
@login_required
def emergency_status_api(admission_id):

    conn = get_db()

    row = conn.execute(
        """
        SELECT
            id,
            status,
            updated_at
        FROM emergency_admissions
        WHERE id=?
        AND user_id=?
        """,
        (
            admission_id,
            session["user_id"]
        )
    ).fetchone()

    conn.close()

    if not row:

        return jsonify({
            "error": "Emergency request not found."
        }), 404

    return jsonify({
        "id": row["id"],
        "status": row["status"],
        "updated_at": row["updated_at"]
    })


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

try:
    init_db()

except Exception as exc:

    print(
        "\n================================================="
    )
    print(
        "DATABASE INITIALIZATION ERROR"
    )
    print(
        "================================================="
    )
    print(
        str(exc)
    )
    print(
        "=================================================\n"
    )

    raise


# =========================================================
# APPLICATION START
# =========================================================

if __name__ == "__main__":

    print(
        "\n================================================="
    )

    print(
        " Smart Healthcare Management & "
        "Disease Prediction System"
    )

    print(
        "================================================="
    )

    print(
        " Server: http://127.0.0.1:5000"
    )

    print(
        " Emergency: http://127.0.0.1:5000/emergency"
    )

    print(
        " Admin: http://127.0.0.1:5000/admin"
    )

    print(
        "=================================================\n"
    )

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )