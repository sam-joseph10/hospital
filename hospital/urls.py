from django.urls import path
from hospital import viewer_views,operator_views

urlpatterns = [
    # Public
    path('', viewer_views.landing, name='landing'),
    
    # Authentication
    path('login/', viewer_views.login_view, name='login'),
    path('logout/', viewer_views.logout_view, name='logout'),

    # 
    path('forgot-password/', viewer_views.forgot_password, name='forgot_password'),
    path('api/send-otp/', viewer_views.send_otp, name='send_otp'),
    path('api/verify-otp/', viewer_views.verify_otp, name='verify_otp'),
    path('api/reset-password/', viewer_views.reset_password, name='reset_password'),

    # Viewer Dashboard & Overview
    path('viewer/dashboard/', viewer_views.viewer_dashboard, name='viewer_dashboard'),
    path('viewer/summary/',viewer_views.summary,name="summary"),
    path('viewer/this_month/', viewer_views.this_month, name='this_month'),

    # Viewer Departments
    path('viewer/depts/', viewer_views.depts_list, name='depts_list'),
    path('viewer/departments/<int:dept_id>/', viewer_views.department_detail, name='department_detail'),
    path('viewer/department/<int:dept_id>/<int:month>/<int:year>/', viewer_views.department_month_detail, name='department_month_detail'),
    
    # Viewer Patients
    path('viewer/patient/<str:pt_id>/', viewer_views.patient_details, name='patient_details'),
    path('viewer/patient/<str:pt_id>/download_report/', viewer_views.download_full_report, name='download_full_report'),
    path('viewer/share-patient/', viewer_views.share_patient, name='share_patient'),

    # Viewer Doctors, Reports, Shares
    #path('viewer/doctors/', views.doctor_list, name='doctors_list'),
    path('viewer/reports/', viewer_views.reports_list, name='reports_list'),
    path('viewer/shares/', viewer_views.shares_list, name='shares_list'),
    path('viewer/master/', viewer_views.master, name='master'),

    # viewer master
    path('viewer/patients/', viewer_views.patients_list, name='patients_list'),
    path('viewer/departments/', viewer_views.departments_list, name='departments_list'),
    path('viewer/patients/<int:pk>/edit/', viewer_views.patient_edit, name='patient_edit'),

    path('doctors/', viewer_views.doctors_list, name='doctors_list'),
    path('doctors/add/', viewer_views.doctor_add, name='doctor_add'),
    path('doctors/<int:pk>/edit/', viewer_views.doctor_edit, name='doctor_edit'),
    path('doctors/<int:pk>/delete/', viewer_views.doctor_delete, name='doctor_delete'),

    path('departments/', viewer_views.departments_list, name='departments_list'),
    path('departments/add/', viewer_views.department_add, name='department_add'),
    path('departments/<int:pk>/edit/', viewer_views.department_edit, name='department_edit'),
    path('departments/<int:pk>/delete/', viewer_views.department_delete, name='department_delete'),

    # Operator Dashboard
    path('operator/dashboard/', operator_views.operator_dashboard, name='operator_dashboard'),
    path('api/patient-visits/', operator_views.create_patient_visit, name='create_patient_visit'),
]