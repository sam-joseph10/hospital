import os
import django
import random
from datetime import date, timedelta

# -----------------------------
# DJANGO SETUP
# -----------------------------
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hospital_system.settings")
django.setup()

from hospital.models import Hospital, Department, Doctor, PatientVisit, Attachment
from django.contrib.auth import get_user_model
from django.core.files import File

User = get_user_model()

# -----------------------------
# CONFIG
# -----------------------------
DOCS_PATH = r"C:\Users\medar\OneDrive\Documents\Docs"

PATIENT_NAMES = [
    "Ravi Kumar", "Anita Sharma", "Suresh Reddy", "Meena Iyer",
    "Kiran Patel", "Pooja Gupta", "Rahul Verma", "Sneha Das",
    "Vikram Singh", "Neha Joshi"
]

DIAGNOSIS_LIST = [
    "Fever", "Diabetes", "Hypertension", "Fracture",
    "Skin Allergy", "Migraine", "Infection", "Asthma"
]

STATUS_LIST = ["cured", "dead", "shifted"]
GENDERS = ["Male", "Female"]

# -----------------------------
# FETCH BASE DATA
# -----------------------------
hospital = Hospital.objects.first()
if not hospital:
    print("❌ No hospital found!")
    exit()

departments = Department.objects.filter(hospital=hospital)
user = User.objects.filter(hospital=hospital).first()

if not user:
    print("❌ No user found!")
    exit()

files = [f for f in os.listdir(DOCS_PATH) if f.endswith(".pdf")]

# -----------------------------
# CREATE PATIENTS (ONLY DISCHARGED)
# -----------------------------
patient_counter = 1000

for dept in departments:
    print(f"Processing department: {dept.name}")
    doctors = Doctor.objects.filter(department=dept)
    
    if not doctors:
        continue

    for i in range(5):  # 5 patients per department

        doctor = random.choice(doctors)

        patient_name = random.choice(PATIENT_NAMES)
        diagnosis = random.choice(DIAGNOSIS_LIST)
        status = random.choice(STATUS_LIST)

        visit_date = date.today() - timedelta(days=random.randint(10, 40))
        discharge_date = visit_date + timedelta(days=random.randint(1, 7))

        # -----------------------------
        # CREATE PATIENT VISIT
        # -----------------------------
        patient = PatientVisit.objects.create(
            hospital=hospital,
            department=dept,
            doctor=doctor,
            patient_id=f"PAT{patient_counter}",
            patient_name=patient_name,
            gender=random.choice(GENDERS),
            date_of_birth=date(1990, 1, 1),
            phone=str(9000000000 + patient_counter),
            visit_date=visit_date,
            diagnosis=diagnosis,
            notes="Finalized case record (post discharge)",
            status=status,
            discharge_date=discharge_date,
            created_by=user
        )

        patient_counter += 1

        # -----------------------------
        # CREATE PATIENT-SPECIFIC FOLDER (LOGICAL STRUCTURE)
        # -----------------------------
        # media/patient_attachments/<patient_id>/
        folder_path = f"patient_attachments/{patient.patient_id}"

        # -----------------------------
        # ADD ATTACHMENTS (LINKED TO PATIENTVISIT)
        # -----------------------------
        attach_count = random.randint(2, 4)
        selected_files = random.sample(files, min(attach_count, len(files)))

        for file_name in selected_files:
            file_path = os.path.join(DOCS_PATH, file_name)

            with open(file_path, 'rb') as f:
                Attachment.objects.create(
                    visit=patient,
                    file=File(f, name=f"{folder_path}/{file_name}"),
                    file_name=file_name,
                    file_type="pdf",
                    uploaded_by=user
                )

print("✅ Discharged patients with structured reports created successfully!")

'''
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hospital_system.settings")
django.setup()

from django.contrib.auth import get_user_model
from hospital.models import Hospital, Department, Doctor
import random

User = get_user_model()

hospital = Hospital.objects.first()

if not hospital:
    print("Hospital not found!")
    exit()

departments = list(Department.objects.filter(hospital=hospital))

doctors = [
    ("Dr. Rajesh Kumar", "rajesh@hospital.com", "Cardiology"),
    ("Dr. Priya Reddy", "priya@hospital.com", "Neurology"),
    ("Dr. Arjun Mehta", "arjun@hospital.com", "Orthopedics"),
    ("Dr. Sneha Iyer", "sneha@hospital.com", "Pediatrics"),
    ("Dr. Vivek Sharma", "vivek@hospital.com", "General Medicine"),
    ("Dr. Neha Gupta", "neha@hospital.com", "Dermatology"),
]

phone = 9000000000

for i, (name, email, spec) in enumerate(doctors):
    dept = random.choice(departments)

    Doctor.objects.get_or_create(
        hospital=hospital,
        department=dept,
        name=name,
        email=email,
        phone=str(phone + i),
        specialization=spec
    )

print("6 demo doctors created successfully!")

from django.contrib.auth import get_user_model
from hospital.models import Hospital

User = get_user_model()

# Get or create hospital
hospital = Hospital.objects.first()

if not hospital:
    hospital = Hospital.objects.create(
        name="CityCare Multi Speciality Hospital",
        address="Bangalore, Karnataka",
        phone="9876543210",
        email="admin@citycare.com"
    )

# Viewer Users
viewer_users = [
    ("viewer1", "viewer1@hospital.com"),
]

# Operator Users
operator_users = [
    ("operator1", "operator1@hospital.com"),
]

password = "123"

for username, email in viewer_users:
    if not User.objects.filter(username=username).exists():
        User.objects.create_user(
            username=username,
            email=email,
            password=password,
            hospital=hospital,
            role="viewer"
        )

for username, email in operator_users:
    if not User.objects.filter(username=username).exists():
        User.objects.create_user(
            username=username,
            email=email,
            password=password,
            hospital=hospital,
            role="operator"
        )

print("Demo users created successfully!")

from hospital.models import Hospital, Department

hospital = Hospital.objects.first()

if not hospital:
    hospital = Hospital.objects.create(
        name="CityCare Multi Speciality Hospital",
        address="Bangalore, Karnataka",
        phone="9876543210",
        email="admin@citycare.com"
    )

print("Departments seeded successfully!")'''