from django.contrib import admin
from .models import *

admin.site.register(Hospital)
admin.site.register(User)
admin.site.register(Department)
admin.site.register(Doctor)
admin.site.register(PatientVisit)
admin.site.register(Attachment)
admin.site.register(SharedReport)
admin.site.register(AuditLog)