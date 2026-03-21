from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import *
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.files.storage import default_storage
import json


@login_required
def operator_dashboard(request):

    if request.user.role == "viewer":
        return redirect("viewer_dashboard")
    
    departments = Department.objects.filter(hospital=request.user.hospital)
    doctors = Doctor.objects.filter(hospital=request.user.hospital)
    return render(request, 'operator/dashboard.html', {
        'departments': departments,
        'doctors': doctors,
    })

@login_required
@require_POST
def create_patient_visit(request):
    try:
        # Extract form data (files are in request.FILES)
        data = request.POST
        files = request.FILES

        # Required fields
        required_fields = ['patient_id', 'patient_name', 'gender', 'date_of_birth',
                          'phone', 'department', 'doctor', 'visit_date', 'diagnosis',
                          'status', 'discharge_date']
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({'error': f'{field} is required.'}, status=400)

        # Get foreign key instances
        try:
            department = Department.objects.get(id=data['department'], hospital=request.user.hospital)
            doctor = Doctor.objects.get(id=data['doctor'], hospital=request.user.hospital)
        except (Department.DoesNotExist, Doctor.DoesNotExist):
            return JsonResponse({'error': 'Invalid department or doctor.'}, status=400)

        # Create PatientVisit
        visit = PatientVisit.objects.create(
            hospital=request.user.hospital,
            department=department,
            doctor=doctor,
            patient_id=data['patient_id'],
            patient_name=data['patient_name'],
            gender=data['gender'],
            date_of_birth=data['date_of_birth'],
            phone=data['phone'],
            visit_date=data['visit_date'],
            diagnosis=data['diagnosis'],
            notes=data.get('notes', ''),
            status=data['status'],
            discharge_date=data['discharge_date'],
            created_by=request.user,
        )

        # Process attachments
        attachment_count = 0
        # Files are named like attachment_blood_0, attachment_scan_1, etc.
        # We'll iterate through all keys in request.FILES
        for key, file_list in files.lists():
            if key.startswith('attachment_'):
                # Extract category from key (e.g., 'blood' from 'attachment_blood_0')
                parts = key.split('_')
                if len(parts) >= 3:
                    category = parts[1]  # blood, scan, discharge
                    for f in file_list:
                        # Save file
                        file_path = default_storage.save(f"patient_attachments/{visit.id}/{f.name}", f)
                        # Create Attachment record
                        Attachment.objects.create(
                            visit=visit,
                            file=file_path,
                            file_name=f.name,
                            file_type=f.content_type,
                            report_type=category,
                            uploaded_by=request.user,
                        )
                        attachment_count += 1

        return JsonResponse({
            'success': True,
            'visit_id': visit.id,
            'patient_id': visit.patient_id,
            'attachments_count': attachment_count,
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)