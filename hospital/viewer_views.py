from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
import json
from .models import *
from django.db.models import Count
#from django.db.models import Max
from django.shortcuts import get_object_or_404
import os
import tempfile
from django.http import HttpResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from PyPDF2 import PdfMerger
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Count, Q, Sum
from django.utils import timezone
import calendar
from django.core.mail import send_mail
from django.conf import settings
from django.core.mail import EmailMessage
from django.forms import ValidationError
from django.core.validators import validate_email
import logging

logger = logging.getLogger(__name__)
def landing(request):
    return render(request, "landing.html")

def login_view(request):

    if request.method == "POST":

        data = json.loads(request.body)

        username = data.get("username")
        password = data.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            if user.role == "viewer":
                redirect_url = "/viewer/dashboard/"
            elif user.role == "operator":
                redirect_url = "/operator/dashboard/"
            else:
                redirect_url = "/"

            return JsonResponse({
                "success": True,
                "redirect_url": redirect_url
            })

        return JsonResponse({
            "success": False,
            "error": "Invalid credentials"
        })

    return JsonResponse({"error": "Invalid request"}, status=400)

def logout_view(request):
    logout(request)
    return redirect('landing')

@login_required
def viewer_dashboard(request):

    if request.user.role == "operator":
        return redirect("operator_dashboard")

    hospital = request.user.hospital

    if not hospital:
        return render(request, "hospital/viewer_dashboard.html", {
            "hospital_name": "N/A",
            "total_patients": 0,
            "total_reports": 0,
            "total_shares": 0,
            "total_doctors": 0,
        })

    visits = PatientVisit.objects.filter(hospital=hospital)

    total_patients = visits.values('patient_id').distinct().count()
    total_reports = visits.count()
    total_doctors = Doctor.objects.filter(hospital=hospital).count()
    total_shares = SharedReport.objects.filter(visit__hospital=hospital).count()

    context = {
        "hospital_name": hospital.name,
        "total_patients": total_patients,
        "total_reports": total_reports,
        "total_shares": total_shares,
        "total_doctors": total_doctors,
    }

    return render(request, "hospital/viewer_dashboard.html", context)

@login_required
def depts_list(request):

    hospital = request.user.hospital

    if not hospital:
        return render(request, "hospital/Total_Patients/depts_list.html", {"departments": []})

    departments = Department.objects.filter(hospital=hospital)
    visits = PatientVisit.objects.filter(hospital=hospital)

    dept_data = []

    total_patients = visits.values('patient_id').distinct().count()

    total_cured = visits.filter(status='cured').count()

    for dept in departments:

        dept_visits = visits.filter(department=dept)

        patients_count = dept_visits.values('patient_id').distinct().count()

        cured_count = dept_visits.filter(status='cured').count()

        dept_data.append({
            "id": dept.id,
            "name": dept.name,
            "patients": patients_count,
            "cured": cured_count,
        })

    context = {
        "hospital_name": hospital.name,
        "departments": dept_data,
        "dept_count": len(dept_data),
        "hospital_address": hospital.address,
        "hospital_phone": hospital.phone,
        "total_patients": total_patients,
        "total_cured": total_cured,
    }

    return render(request, "hospital/depts_list.html", context)

@login_required
def department_detail(request, dept_id):
    hospital = request.user.hospital

    department = Department.objects.get(id=dept_id, hospital=hospital)

    visits = PatientVisit.objects.filter(
        hospital=hospital,
        department=department
    ).select_related("doctor")

    patient_map = {}

    for visit in visits.order_by('-visit_date'):

        pid = visit.patient_id

        if pid not in patient_map:
            patient_map[pid] = {
                "patient_id": pid,  # ✅ keep this
                "name": visit.patient_name,
                "gender": visit.gender,
                "doctor": visit.doctor.name,
                "diagnosis": visit.diagnosis,
                "join_date": str(visit.visit_date),
                "discharge_date": str(visit.discharge_date),
                "status": visit.status,
            }

    patient_data = list(patient_map.values())

    context = {
        "department": department,
        "patients": patient_data,
        "total": len(patient_data),
        "cured": len([p for p in patient_data if p["status"] == "cured"])
    }

    return render(request, "hospital/patient_list.html", context)

@login_required
def patient_details(request, pt_id):
    hospital = request.user.hospital

    visit = PatientVisit.objects.select_related(
        "doctor", "department", "hospital"
    ).get(patient_id=pt_id, hospital=hospital)

    attachments = Attachment.objects.filter(visit=visit)
    shared_reports = SharedReport.objects.filter(visit=visit)

    context = {
        "visit": visit,
        "attachments": attachments,
        "shared_reports": shared_reports,
    }

    return render(request, "hospital/patient_details.html", context)

@login_required
def download_full_report(request, pt_id):
    hospital = request.user.hospital

    visit = PatientVisit.objects.select_related(
        "doctor", "department", "hospital"
    ).get(patient_id=pt_id, hospital=hospital)

    attachments = Attachment.objects.filter(visit=visit)

    # -----------------------------
    # STEP 1: CREATE SUMMARY PDF
    # -----------------------------
    # Create temp file but close it immediately – we only need the name
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        temp_summary_path = tmp.name
        # File is now closed; ReportLab will reopen it

    try:
        doc = SimpleDocTemplate(temp_summary_path)
        styles = getSampleStyleSheet()
        content = []

        content.append(Paragraph("<b>Patient Report</b>", styles['Title']))
        content.append(Spacer(1, 10))

        content.append(Paragraph(f"Name: {visit.patient_name}", styles['Normal']))
        content.append(Paragraph(f"Patient ID: {visit.patient_id}", styles['Normal']))
        content.append(Paragraph(f"Gender: {visit.gender}", styles['Normal']))
        content.append(Paragraph(f"Phone: {visit.phone}", styles['Normal']))
        content.append(Spacer(1, 10))

        content.append(Paragraph(f"Hospital: {visit.hospital.name}", styles['Normal']))
        content.append(Paragraph(f"Department: {visit.department.name}", styles['Normal']))
        content.append(Paragraph(f"Doctor: {visit.doctor.name}", styles['Normal']))
        content.append(Spacer(1, 10))

        content.append(Paragraph(f"Visit Date: {visit.visit_date}", styles['Normal']))
        content.append(Paragraph(f"Discharge Date: {visit.discharge_date}", styles['Normal']))
        content.append(Paragraph(f"Status: {visit.status}", styles['Normal']))
        content.append(Spacer(1, 10))

        content.append(Paragraph("<b>Diagnosis:</b>", styles['Heading2']))
        content.append(Paragraph(visit.diagnosis, styles['Normal']))
        content.append(Spacer(1, 10))

        content.append(Paragraph("<b>Notes:</b>", styles['Heading2']))
        content.append(Paragraph(visit.notes or "No notes", styles['Normal']))

        doc.build(content)   # This closes the file after writing

        # -----------------------------
        # STEP 2: MERGE PDFs
        # -----------------------------
        merger = PdfMerger()
        # Add summary first
        merger.append(temp_summary_path)

        # Add all attachments (only PDFs)
        for att in attachments:
            if att.file.path.endswith(".pdf"):
                merger.append(att.file.path)

        # -----------------------------
        # STEP 3: RETURN FINAL PDF
        # -----------------------------
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{visit.patient_id}_report.pdf"'

        merger.write(response)
        merger.close()   # Closes any open file handles from appended PDFs

    finally:
        # Ensure the temporary file is deleted, even if an error occurred
        if os.path.exists(temp_summary_path):
            os.unlink(temp_summary_path)

    return response

@login_required
def reports_list(request):
    hospital = request.user.hospital
    departments = Department.objects.filter(hospital=hospital).order_by('name')
    patients = PatientVisit.objects.filter(hospital=hospital).select_related('doctor', 'department')

    patients_list = []
    for p in patients:
        patients_list.append({
            'id': p.patient_id,
            'name': p.patient_name,
            'gender': p.gender or '—',
            'doctor': p.doctor.name if p.doctor else '—',
            'diagnosis': p.diagnosis,                     # <-- add this line
            'joinDate': p.visit_date.strftime('%Y-%m-%d') if p.visit_date else '—',
            'dischargeDate': p.discharge_date.strftime('%Y-%m-%d') if p.discharge_date else '—',
            'status': p.status,
            'department': p.department.name if p.department else '—',
        })

    context = {
        'departments': departments,
        'patients_json': patients_list, 
    }
    return render(request, 'hospital/reports_list.html', context)

@login_required
def shares_list(request):
    hospital = request.user.hospital
    departments = Department.objects.filter(hospital=hospital).order_by('name')
    patients = PatientVisit.objects.filter(hospital=hospital).select_related('doctor', 'department')
    patients_list = []
    for p in patients:
        patients_list.append({
            'id': p.patient_id,
            'name': p.patient_name,
            'gender': p.gender or '—',
            'department': p.department.name if p.department else '—',
            'doctor': p.doctor.name if p.doctor else '—',
            'diagnosis': p.diagnosis,
            'joinDate': p.visit_date.strftime('%Y-%m-%d') if p.visit_date else '—',
            'dischargeDate': p.discharge_date.strftime('%Y-%m-%d') if p.discharge_date else '—',
            'status': p.status,
        })
    context = {
        'departments': departments,
        'patients_json': patients_list,   # list, not json.dumps
    }
    return render(request, 'hospital/shares_list.html', context)

@login_required
@require_POST
def share_patient(request):
    """
    AJAX endpoint to share patient details via email.
    Expects JSON: { patient_id, email, subject, message }
    """
    try:
        data = json.loads(request.body)
        patient_id = data.get('patient_id')
        recipient_email = data.get('email')
        subject = data.get('subject', '').strip()
        message = data.get('message', '').strip()

        # Basic validation
        if not patient_id or not recipient_email:
            return JsonResponse(
                {'success': False, 'error': 'Patient ID and email are required.'},
                status=400
            )

        # Validate email format
        try:
            validate_email(recipient_email)
        except ValidationError:
            return JsonResponse(
                {'success': False, 'error': 'Invalid email address.'},
                status=400
            )

        # Ensure the patient exists and belongs to the user's hospital
        try:
            visit = PatientVisit.objects.get(
                patient_id=patient_id,
                hospital=request.user.hospital
            )
        except PatientVisit.DoesNotExist:
            return JsonResponse(
                {'success': False, 'error': 'Patient not found.'},
                status=404
            )

        # --- Build the email content ---
        # Use getattr to safely handle missing fields (adjust field names as needed)
        patient_info = f"""
Patient Name: {getattr(visit, 'patient_name', 'N/A')}
Patient ID: {visit.patient_id}
Gender: {getattr(visit, 'gender', 'Not specified')}
Date of Birth: {getattr(visit, 'date_of_birth', 'Not specified')}
Phone: {getattr(visit, 'phone', 'Not provided')}
Visit Date: {getattr(visit, 'visit_date', 'N/A')}
Diagnosis: {getattr(visit, 'diagnosis', 'N/A')}
Status: {visit.get_status_display() if hasattr(visit, 'get_status_display') else 'N/A'}
Discharge Date: {getattr(visit, 'discharge_date', 'N/A')}
        """

        full_message = f"{message}\n\n--- Patient Details ---\n{patient_info}"

        # --- Prepare email ---
        email_sent = False
        email_error = None

        if not settings.DEFAULT_FROM_EMAIL:
            email_error = "Email from address is not configured."
        else:
            try:
                email = EmailMessage(
                    subject=subject,
                    body=full_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[recipient_email],
                )

                # Attach files
                attachments = Attachment.objects.filter(visit=visit)
                for attachment in attachments:
                    if attachment.file and os.path.exists(attachment.file.path):
                        email.attach_file(attachment.file.path)
                    else:
                        logger.warning(
                            "Attachment file missing for attachment ID %s: %s",
                            attachment.id, attachment.file_name
                        )

                email.send(fail_silently=False)
                email_sent = True

            except Exception as e:
                email_error = str(e)
                logger.exception("Failed to send email for visit %s", visit.id)

        # --- Record the share attempt ---
        # Only create share record if email was sent (or always, depending on requirements)
        # Here we create it regardless, but we store the outcome.
        share = SharedReport.objects.create(
            visit=visit,
            shared_email=recipient_email,
            shared_by=request.user,
            # If you want to store subject/message, ensure these fields exist on SharedReport
            # subject=subject,
            # message=message
        )

        if email_sent:
            return JsonResponse({
                'success': True,
                'message': 'Patient details shared successfully via email.'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': f'Email could not be sent: {email_error}'
            }, status=500)

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON.'}, status=400)
    except Exception as e:
        logger.exception("Unexpected error in share_patient")
        return JsonResponse({'success': False, 'error': 'An internal error occurred.'}, status=500)

@login_required
def this_month(request):
    """
    View for displaying monthly department overview with statistics
    """
    # Get current month and year
    today = timezone.now().date()
    current_month = today.month
    current_year = today.year
    month_name = calendar.month_name[current_month]
    
    # Get user's hospital
    hospital = request.user.hospital
    
    # Get hospital details
    hospital_name = hospital.name if hospital else "Hospital"
    hospital_address = hospital.address if hospital else "Address not available"
    hospital_phone = hospital.phone if hospital else "Phone not available"
    
    # Get all departments for this hospital
    departments = Department.objects.filter(hospital=hospital)
    
    # Calculate monthly statistics
    monthly_departments = []
    total_monthly_patients = 0
    total_monthly_cured = 0
    
    for dept in departments:
        # Get patients for this department in current month
        monthly_patients = PatientVisit.objects.filter(
            hospital=hospital,
            department=dept,
            visit_date__month=current_month,
            visit_date__year=current_year
        )
        
        # Count patients
        patient_count = monthly_patients.count()
        
        # Count cured patients this month
        cured_count = monthly_patients.filter(status='cured').count()
        
        # Calculate percentage (avoid division by zero)
        if patient_count > 0:
            percentage = round((cured_count / patient_count) * 100)
        else:
            percentage = 0
        
        # Only include departments with activity this month
        if patient_count > 0:
            # Determine icon based on department name (you can customize this)
            icon = get_department_icon(dept.name)
            
            # Determine image class for background
            image_class = get_department_image_class(dept.name)
            
            monthly_departments.append({
                'id': dept.id,
                'name': dept.name,
                'monthly_patients': patient_count,
                'monthly_cured': cured_count,
                'percentage': percentage,
                'icon': icon,
                'image_class': image_class,
            })
            
            # Add to totals
            total_monthly_patients += patient_count
            total_monthly_cured += cured_count
    
    # Sort departments by patient count (highest first)
    monthly_departments.sort(key=lambda x: x['monthly_patients'], reverse=True)
    
    # Count active departments (those with patients this month)
    active_dept_count = len(monthly_departments)
    
    context = {
        'hospital_name': hospital_name,
        'hospital_address': hospital_address,
        'hospital_phone': hospital_phone,
        'month_name': month_name,
        'year': current_year,
        'month': current_month,
        'monthly_departments': monthly_departments,
        'monthly_dept_count': active_dept_count,
        'monthly_patients': total_monthly_patients,
        'monthly_cured': total_monthly_cured,
    }
    
    return render(request, "hospital/this_month.html", context)


def get_department_icon(department_name):
    """
    Return appropriate Font Awesome icon based on department name
    """
    icon_mapping = {
        'cardiology': 'fa-heart',
        'neurology': 'fa-brain',
        'orthopedics': 'fa-bone',
        'pediatrics': 'fa-child',
        'emergency': 'fa-truck-medical',
        'radiology': 'fa-x-ray',
        'surgery': 'fa-scalpel',
        'icu': 'fa-monitor-heart-rate',
        'oncology': 'fa-ribbon',
        'dermatology': 'fa-allergies',
        'gastroenterology': 'fa-stomach',
        'pulmonology': 'fa-lungs',
        'urology': 'fa-kidneys',
        'psychiatry': 'fa-heart',
        'nephrology': 'fa-kidneys',
        'endocrinology': 'fa-droplet',
        'ophthalmology': 'fa-eye',
        'ent': 'fa-ear-listen',
        'gynecology': 'fa-venus',
        'dentistry': 'fa-tooth',
    }
    
    # Convert department name to lowercase for matching
    name_lower = department_name.lower()
    
    # Find matching icon
    for key, icon in icon_mapping.items():
        if key in name_lower:
            return icon
    
    # Default icon
    return 'fa-stethoscope'


def get_department_image_class(department_name):
    """
    Return appropriate image CSS class based on department name
    """
    image_mapping = {
        'cardiology': 'img-cardiology',
        'neurology': 'img-neurology',
        'orthopedics': 'img-orthopedics',
        'pediatrics': 'img-pediatrics',
        'emergency': 'img-emergency',
        'radiology': 'img-radiology',
        'surgery': 'img-surgery',
        'icu': 'img-icu',
        'oncology': 'img-oncology',
        'dermatology': 'img-dermatology',
        'gastroenterology': 'img-gastro',
        'pulmonology': 'img-pulmonology',
        'urology': 'img-urology',
        'psychiatry': 'img-psychiatry',
        'nephrology': 'img-nephrology',
        'endocrinology': 'img-endocrinology',
    }
    
    # Convert department name to lowercase for matching
    name_lower = department_name.lower()
    
    # Find matching image class
    for key, img_class in image_mapping.items():
        if key in name_lower:
            return img_class
    
    # Default image class
    return 'img-default'

@login_required
def department_month_detail(request, dept_id, month, year):
    """
    View for showing department details for a specific month
    """
    hospital = request.user.hospital
    department = get_object_or_404(Department, id=dept_id, hospital=hospital)
    
    # Get patients for this department in the specified month
    patients = PatientVisit.objects.filter(
        hospital=hospital,
        department=department,
        visit_date__month=month,
        visit_date__year=year
    ).select_related('doctor')
    
    month_name = calendar.month_name[month]
    
    context = {
        'department': department,
        'month_name': month_name,
        'year': year,
        'month': month,
        'patients': patients,
        'patient_count': patients.count(),
        'cured_count': patients.filter(status='cured').count(),
    }
    
    return render(request, 'hospital/department_month_detail.html', context)

@login_required
def summary(request):
    hospital = request.user.hospital
    departments = Department.objects.filter(hospital=hospital).order_by('name')
    patients = PatientVisit.objects.filter(hospital=hospital).select_related('doctor', 'department')

    patients_list = []
    for p in patients:
        patients_list.append({
            'id': p.patient_id,
            'name': p.patient_name,
            'gender': p.gender or '—',
            'doctor': p.doctor.name if p.doctor else '—',
            'diagnosis': p.diagnosis,                     # <-- add this line
            'joinDate': p.visit_date.strftime('%Y-%m-%d') if p.visit_date else '—',
            'dischargeDate': p.discharge_date.strftime('%Y-%m-%d') if p.discharge_date else '—',
            'status': p.status,
            'department': p.department.name if p.department else '—',
        })

    context = {
        'departments': departments,
        'patients_json': patients_list, 
    }   
    return render(request, "hospital/summary.html", context)

@login_required
def master(request):
    hospital = request.user.hospital
    context = {
        'doctor_count': Doctor.objects.filter(hospital=hospital).count(),
        'patient_count': PatientVisit.objects.filter(hospital=hospital).count(),
        'department_count': Department.objects.filter(hospital=hospital).count(),
    }
    return render(request, 'hospital/master.html', context)

@login_required
def doctors_list(request):
    hospital = request.user.hospital
    doctors = Doctor.objects.filter(hospital=hospital).select_related('department')
    departments = Department.objects.filter(hospital=hospital).order_by('name')

    doctors_data = []
    for doc in doctors:
        doctors_data.append({
            'id': doc.pk,
            'display_id': doc.doctor_id or f'DOC{str(doc.pk).zfill(3)}',
            'name': doc.name,
            'gender': doc.gender,
            'specialization': doc.specialization,
            'department_id': doc.department_id,
            'department_name': doc.department.name if doc.department else '—',
            'email': doc.email,
            'phone': doc.phone,
            'date_of_birth': doc.date_of_birth.isoformat() if doc.date_of_birth else '',
            'address': doc.address,
            'qualification': doc.qualification,
            'registration_number': doc.registration_number,
            'experience_years': doc.experience_years,
            'previous_hospital': doc.previous_hospital,
            'designation': doc.designation,
            'joining_date': doc.joining_date.isoformat() if doc.joining_date else '',
            'working_days': doc.working_days,
        })

    context = {
        'hospital_name': hospital.name,
        'departments': departments,
        'doctors_json': doctors_data,   # pass the list, not JSON string
    }
    return render(request, 'hospital/doctors_list.html', context)


@login_required
@require_POST
def doctor_add(request):
    data = json.loads(request.body)
    hospital = request.user.hospital

    # Required fields
    required = ['name', 'gender', 'email', 'phone', 'specialization', 'department_id']
    for field in required:
        if not data.get(field):
            return JsonResponse({'success': False, 'error': f'{field} is required.'})

    try:
        department = Department.objects.get(pk=data['department_id'], hospital=hospital)
    except Department.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Invalid department.'})

    doctor = Doctor(
        hospital=hospital,
        department=department,
        doctor_id=data.get('doctor_id', ''),
        name=data['name'],
        gender=data['gender'],
        date_of_birth=data.get('date_of_birth') or None,
        phone=data['phone'],
        email=data['email'],
        address=data.get('address', ''),
        qualification=data.get('qualification', ''),
        specialization=data['specialization'],
        registration_number=data.get('registration_number', ''),
        experience_years=data.get('experience_years') or None,
        previous_hospital=data.get('previous_hospital', ''),
        designation=data.get('designation', ''),
        joining_date=data.get('joining_date') or None,
        working_days=data.get('working_days', ''),
    )
    doctor.save()
    
    # Refresh to get converted Python objects (dates become date, ints become int)
    doctor.refresh_from_db()

    return JsonResponse({
        'success': True,
        'doctor': {
            'id': doctor.pk,
            'display_id': doctor.doctor_id or f'DOC{str(doctor.pk).zfill(3)}',
            'name': doctor.name,
            'gender': doctor.gender,
            'specialization': doctor.specialization,
            'department_id': doctor.department_id,
            'department_name': doctor.department.name,
            'email': doctor.email,
            'phone': doctor.phone,
            'date_of_birth': doctor.date_of_birth.isoformat() if doctor.date_of_birth else '',
            'address': doctor.address,
            'qualification': doctor.qualification,
            'registration_number': doctor.registration_number,
            'experience_years': doctor.experience_years,
            'previous_hospital': doctor.previous_hospital,
            'designation': doctor.designation,
            'joining_date': doctor.joining_date.isoformat() if doctor.joining_date else '',
            'working_days': doctor.working_days,
        }
    })


@login_required
@require_POST
def doctor_edit(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk, hospital=request.user.hospital)
    data = json.loads(request.body)

    required = ['name', 'gender', 'email', 'phone', 'specialization', 'department_id']
    for field in required:
        if not data.get(field):
            return JsonResponse({'success': False, 'error': f'{field} is required.'})

    try:
        department = Department.objects.get(pk=data['department_id'], hospital=request.user.hospital)
    except Department.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Invalid department.'})

    doctor.doctor_id = data.get('doctor_id', '')
    doctor.name = data['name']
    doctor.gender = data['gender']
    doctor.date_of_birth = data.get('date_of_birth') or None
    doctor.phone = data['phone']
    doctor.email = data['email']
    doctor.address = data.get('address', '')
    doctor.qualification = data.get('qualification', '')
    doctor.specialization = data['specialization']
    doctor.registration_number = data.get('registration_number', '')
    doctor.experience_years = data.get('experience_years') or None
    doctor.previous_hospital = data.get('previous_hospital', '')
    doctor.designation = data.get('designation', '')
    doctor.joining_date = data.get('joining_date') or None
    doctor.working_days = data.get('working_days', '')
    doctor.department = department
    doctor.save()
    
    doctor.refresh_from_db()

    return JsonResponse({
        'success': True,
        'doctor': {
            'id': doctor.pk,
            'display_id': doctor.doctor_id or f'DOC{str(doctor.pk).zfill(3)}',
            'name': doctor.name,
            'gender': doctor.gender,
            'specialization': doctor.specialization,
            'department_id': doctor.department_id,
            'department_name': doctor.department.name,
            'email': doctor.email,
            'phone': doctor.phone,
            'date_of_birth': doctor.date_of_birth.isoformat() if doctor.date_of_birth else '',
            'address': doctor.address,
            'qualification': doctor.qualification,
            'registration_number': doctor.registration_number,
            'experience_years': doctor.experience_years,
            'previous_hospital': doctor.previous_hospital,
            'designation': doctor.designation,
            'joining_date': doctor.joining_date.isoformat() if doctor.joining_date else '',
            'working_days': doctor.working_days,
        }
    })

@login_required
@require_POST
def doctor_delete(request, pk):
    """AJAX: delete a doctor."""
    doctor = get_object_or_404(Doctor, pk=pk, hospital=request.user.hospital)
    doctor.delete()
    return JsonResponse({'success': True})


@login_required
def patients_list(request):
    hospital = request.user.hospital
    patients = PatientVisit.objects.filter(hospital=hospital).select_related('doctor', 'department')
    doctors = Doctor.objects.filter(hospital=hospital)
    departments = Department.objects.filter(hospital=hospital)

    patients_data = []
    for p in patients:
        patients_data.append({
            'id': p.pk,                           # primary key (not patient_id)
            'patient_id': p.patient_id,
            'name': p.patient_name,
            'gender': p.gender or '',
            'date_of_birth': p.date_of_birth.isoformat() if p.date_of_birth else '',
            'phone': p.phone or '',
            'doctor_id': p.doctor_id,
            'doctor_name': p.doctor.name if p.doctor else '',
            'department_id': p.department_id,
            'department_name': p.department.name if p.department else '',
            'visit_date': p.visit_date.isoformat() if p.visit_date else '',
            'diagnosis': p.diagnosis,
            'notes': p.notes,
            'status': p.status,
            'discharge_date': p.discharge_date.isoformat() if p.discharge_date else '',
        })

    context = {
        'hospital_name': hospital.name,
        'doctors': doctors,
        'departments': departments,
        'patients_json': patients_data,            # list, not JSON string
    }
    return render(request, 'hospital/patients_list.html', context)


@login_required
@require_POST
def patient_edit(request, pk):
    patient = get_object_or_404(PatientVisit, pk=pk, hospital=request.user.hospital)
    data = json.loads(request.body)

    required = ['patient_id', 'name', 'gender', 'doctor_id', 'department_id', 'visit_date', 'diagnosis', 'status']
    for field in required:
        if not data.get(field):
            return JsonResponse({'success': False, 'error': f'{field} is required.'})

    try:
        doctor = Doctor.objects.get(pk=data['doctor_id'], hospital=request.user.hospital)
    except Doctor.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Invalid doctor.'})

    try:
        department = Department.objects.get(pk=data['department_id'], hospital=request.user.hospital)
    except Department.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Invalid department.'})

    patient.patient_id = data['patient_id']
    patient.patient_name = data['name']
    patient.gender = data.get('gender', '')
    patient.date_of_birth = data.get('date_of_birth') or None
    patient.phone = data.get('phone', '')
    patient.doctor = doctor
    patient.department = department
    patient.visit_date = data['visit_date']
    patient.diagnosis = data['diagnosis']
    patient.notes = data.get('notes', '')
    patient.status = data['status']
    patient.discharge_date = data.get('discharge_date') or None
    patient.save()

    # 🔁 Refresh to get Python objects (date, datetime)
    patient.refresh_from_db()

    return JsonResponse({
        'success': True,
        'patient': {
            'id': patient.pk,
            'patient_id': patient.patient_id,
            'name': patient.patient_name,
            'gender': patient.gender,
            'date_of_birth': patient.date_of_birth.isoformat() if patient.date_of_birth else '',
            'phone': patient.phone,
            'doctor_id': patient.doctor_id,
            'doctor_name': patient.doctor.name if patient.doctor else '',
            'department_id': patient.department_id,
            'department_name': patient.department.name if patient.department else '',
            'visit_date': patient.visit_date.isoformat() if patient.visit_date else '',
            'diagnosis': patient.diagnosis,
            'notes': patient.notes,
            'status': patient.status,
            'discharge_date': patient.discharge_date.isoformat() if patient.discharge_date else '',
        }
    })

@login_required
def departments_list(request):
    hospital = request.user.hospital
    departments = Department.objects.filter(hospital=hospital).annotate(
        doctor_count=Count('doctor'),
        patient_count=Count('patientvisit')
    ).order_by('name')

    depts_data = []
    for dept in departments:
        depts_data.append({
            'id': dept.pk,
            'name': dept.name,
            'description': dept.description,
            'doctor_count': dept.doctor_count,
            'patient_count': dept.patient_count,
        })

    context = {
        'hospital_name': hospital.name,
        'departments_json': depts_data,   # list, not JSON string
    }
    return render(request, 'hospital/departments_list.html', context)


@login_required
@require_POST
def department_add(request):
    data = json.loads(request.body)
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()

    if not name:
        return JsonResponse({'success': False, 'error': 'Department name is required.'})

    hospital = request.user.hospital

    # Check if department with same name already exists for this hospital
    if Department.objects.filter(hospital=hospital, name__iexact=name).exists():
        return JsonResponse({'success': False, 'error': 'A department with this name already exists.'})

    dept = Department.objects.create(
        hospital=hospital,
        name=name,
        description=description
    )

    return JsonResponse({
        'success': True,
        'department': {
            'id': dept.pk,
            'name': dept.name,
            'description': dept.description,
            'doctor_count': 0,
            'patient_count': 0,
        }
    })


@login_required
@require_POST
def department_edit(request, pk):
    dept = get_object_or_404(Department, pk=pk, hospital=request.user.hospital)
    data = json.loads(request.body)
    new_name = data.get('name', '').strip()
    description = data.get('description', '').strip()

    if not new_name:
        return JsonResponse({'success': False, 'error': 'Department name is required.'})

    # Check for duplicate name (excluding current)
    if Department.objects.filter(hospital=request.user.hospital, name__iexact=new_name).exclude(pk=pk).exists():
        return JsonResponse({'success': False, 'error': 'Another department with this name already exists.'})

    dept.name = new_name
    dept.description = description
    dept.save()

    # Re‑fetch counts
    doctor_count = dept.doctor_set.count()
    patient_count = dept.patientvisit_set.count()

    return JsonResponse({
        'success': True,
        'department': {
            'id': dept.pk,
            'name': dept.name,
            'description': dept.description,
            'doctor_count': doctor_count,
            'patient_count': patient_count,
        }
    })


@login_required
@require_POST
def department_delete(request, pk):
    dept = get_object_or_404(Department, pk=pk, hospital=request.user.hospital)
    dept.delete()
    return JsonResponse({'success': True})


import json
import random
import string
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import render
from django.conf import settings
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_exempt
from django.views.decorators.http import require_POST

User = get_user_model()

@ensure_csrf_cookie
def forgot_password(request):
    """Render the password reset page and ensure CSRF cookie is set."""
    return render(request, 'forgot_password.html')


@require_POST
def send_otp(request):
    """
    Accept email, generate 6‑digit OTP, store in session, send email.
    Always returns a generic success message to prevent email enumeration.
    """
    data = json.loads(request.body)
    email = data.get('email')
    print(email)
    if not email:
        return JsonResponse({'error': 'Email is required.'}, status=400)

    try:
        user = User.objects.get(email=email)
        print("user present")
    except User.DoesNotExist:
        # Still return success – do not reveal whether the email exists
        return JsonResponse({'message': 'If an account with this email exists, an OTP has been sent.'})

    # Generate a 6‑digit OTP
    otp = ''.join(random.choices(string.digits, k=6))

    # Store OTP and email in session with expiry (10 minutes)
    request.session['reset_otp'] = {
        'email': email,
        'otp': otp,
        'expires': (datetime.now() + timedelta(minutes=10)).isoformat()
    }

    # Send email
    subject = 'Password Reset OTP'
    message = f'Your OTP for password reset is: {otp}. It expires in 10 minutes.'
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [email]

    send_mail(subject, message, from_email, recipient_list, fail_silently=False)

    return JsonResponse({'message': 'OTP sent successfully.'})


@require_POST
def verify_otp(request):
    """
    Verify the OTP entered by the user against the one stored in the session.
    Marks the session as verified if correct.
    """
    data = json.loads(request.body)
    email = data.get('email')
    print(email)
    # Combine the six individual OTP fields
    otp_entered = ''.join([data.get(f'otp{i}', '') for i in range(1, 7)])
    reset_data = request.session.get('reset_otp')
    if not reset_data:
        return JsonResponse({'error': 'No OTP request found. Please request a new OTP.'}, status=400)

    if reset_data['email'] != email:
        return JsonResponse({'error': 'Email mismatch.'}, status=400)

    # Check expiry
    expires = datetime.fromisoformat(reset_data['expires'])
    if datetime.now() > expires:
        return JsonResponse({'error': 'OTP has expired. Please request a new one.'}, status=400)
    
    print(reset_data['otp'], " ",otp_entered)
    
    if reset_data['otp'] == otp_entered:
        # Mark as verified in session
        request.session['reset_verified'] = True
        return JsonResponse({'message': 'OTP verified successfully.'})
    else:
        return JsonResponse({'error': 'Invalid OTP.'}, status=400)


@require_POST
def reset_password(request):
    """
    Reset the user's password after OTP verification.
    Expects newPassword and confirmPassword in the request body.
    """
    data = json.loads(request.body)
    new_password = data.get('newPassword')
    confirm_password = data.get('confirmPassword')

    if new_password != confirm_password:
        return JsonResponse({'error': 'Passwords do not match.'}, status=400)

    # Ensure the OTP was verified
    if not request.session.get('reset_verified'):
        return JsonResponse({'error': 'OTP not verified. Please complete the OTP step first.'}, status=403)

    reset_data = request.session.get('reset_otp')
    if not reset_data:
        return JsonResponse({'error': 'No reset request found.'}, status=400)

    email = reset_data['email']
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found.'}, status=404)

    # Update password
    user.password = make_password(new_password)
    user.save()

    # Clear session data
    del request.session['reset_otp']
    del request.session['reset_verified']

    return JsonResponse({'message': 'Password reset successfully.'})