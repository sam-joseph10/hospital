from django.db import models
from django.contrib.auth.models import AbstractUser


# -------------------------
# Hospital
# -------------------------
class Hospital(models.Model):
    name = models.CharField(max_length=255)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# -------------------------
# Custom User
# -------------------------
class User(AbstractUser):

    ROLE_CHOICES = (
        ('viewer', 'Viewer'),
        ('operator', 'Operator'),
    )

    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, null=True, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)

    def __str__(self):
        return self.username


# -------------------------
# Department
# -------------------------
class Department(models.Model):
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name
    
    class Meta:
        unique_together = ['hospital', 'name']

# -------------------------
# Doctor
# -------------------------
class Doctor(models.Model):
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)

    # -------------------------
    # BASIC DETAILS
    # -------------------------
    doctor_id = models.CharField(max_length=50, blank=True, null=True)  # ✅ Unique ID

    name = models.CharField(max_length=200)
    gender = models.CharField(max_length=10, blank=True)

    date_of_birth = models.DateField(null=True, blank=True)

    phone = models.CharField(max_length=20)
    email = models.EmailField()

    address = models.TextField(blank=True)

    # -------------------------
    # PROFESSIONAL DETAILS
    # -------------------------
    qualification = models.CharField(max_length=200, blank=True)  
    specialization = models.CharField(max_length=200)

    registration_number = models.CharField(max_length=100, blank=True)

    experience_years = models.PositiveIntegerField(null=True, blank=True)

    previous_hospital = models.CharField(max_length=255, blank=True)

    # -------------------------
    # WORK DETAILS
    # -------------------------
    designation = models.CharField(max_length=100, blank=True)  # Consultant, Surgeon

    joining_date = models.DateField(null=True, blank=True)

    working_days = models.CharField(max_length=100, blank=True)  # e.g. Mon-Fri

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.specialization})"


# -------------------------
# Patient
# -------------------------
class PatientVisit(models.Model):

    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)

    # External Patient ID from hospital system
    patient_id = models.CharField(max_length=100, db_index=True)

    # Patient snapshot info
    patient_name = models.CharField(max_length=200)
    gender = models.CharField(max_length=10, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)

    visit_date = models.DateField()

    diagnosis = models.TextField()
    notes = models.TextField(blank=True)

    STATUS_CHOICES = (
        ('cured', 'Cured'),
        ('dead', 'Deceased'),
        ('shifted', 'Shifted'),
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    discharge_date = models.DateField()

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient_name} ({self.patient_id}) - {self.visit_date}"

    class Meta:
        ordering = ['-visit_date']
        indexes = [
            models.Index(fields=['patient_id']),
            models.Index(fields=['hospital', 'department']),
        ]


# -------------------------
# Attachments
# -------------------------
class Attachment(models.Model):
    visit = models.ForeignKey(PatientVisit, on_delete=models.CASCADE)

    file = models.FileField(upload_to="patient_attachments/")
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)
    REPORT_TYPE_CHOICES = (
        ('blood', 'Blood Report'),
        ('scan', 'Scan Report'),
        ('discharge', 'Discharge Summary'),
        ('other', 'Other'),
    )
    # ... existing fields ...
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES, default='other')
    
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file_name


# -------------------------
# Shared Reports
# -------------------------
class SharedReport(models.Model):
    visit = models.ForeignKey(PatientVisit, on_delete=models.CASCADE)

    shared_email = models.EmailField()
    shared_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    subject = models.CharField(max_length=255, blank=True)
    message = models.TextField(blank=True)

    shared_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.visit.patient_name} shared to {self.shared_email}"


# -------------------------
# Audit Logs
# -------------------------
class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    action_type = models.CharField(max_length=100)
    description = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.action_type