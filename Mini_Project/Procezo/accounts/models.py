# accounts/models.py

import os
from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password

# -----------------------------------
# CHOICES
# -----------------------------------
ROLE_CHOICES = (
    ('Admin', 'Admin'),
    ('Staff', 'Staff'),
)

ATTENDANCE_STATUS = (
    ('Present', 'Present'),
    ('Absent', 'Absent'),
    ('Leave', 'Leave'),
)

# -----------------------------------
# UPLOAD PATH FUNCTIONS
# -----------------------------------
def profile_upload_to(instance, filename):
    # instance is Register, so instance.staff_id is a Staff object
    return os.path.join('profiles', instance.staff_id, filename)

def face_upload_to(instance, filename):
    return os.path.join('faces', instance.staff_id, filename)

# ============================================================
#  1) STAFF MODEL
# ============================================================
class Staff(models.Model):
    staff_id = models.CharField(max_length=10, primary_key=True, editable=False)
    name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(unique=True, blank=True, null=True)
    profile_image = models.ImageField(upload_to=profile_upload_to, null=True, blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='Staff')
    job_type = models.CharField(max_length=100, blank=True, null=True)
    gender = models.CharField(max_length=50, blank=True, null=True)
    system_id = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Auto-generate S001, S002...
    def save(self, *args, **kwargs):
        if not self.staff_id:
            last_staff = Staff.objects.order_by('-staff_id').first()

            if last_staff and last_staff.staff_id.startswith('S'):
                last_number = int(last_staff.staff_id[1:])
                new_number = last_number + 1
            else:
                new_number = 1

            self.staff_id = f"S{new_number:03d}"

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.staff_id} - {self.name}"


# ============================================================
#  2) REGISTER MODEL (Login + Extra Data)
# ============================================================
class Register(models.Model):
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="staff_records")
    register_id = models.AutoField(primary_key=True)

    # Login fields
    name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(unique=True, blank=True, null=True)
    password = models.CharField(max_length=255, blank=True)

    # Face recognition
    profile_image = models.ImageField(upload_to=profile_upload_to, null=True, blank=True)
    face_embedding = models.JSONField(null=True, blank=True) # list of floats
    # store the live camera-capture image used at registration/login
    face_capture = models.ImageField(upload_to=face_upload_to, null=True, blank=True)

    # Personal
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='Staff')
    job_type = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True) 
    dob = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=50, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    place = models.CharField(max_length=255, blank=True, null=True)
    pin_code = models.CharField(max_length=20, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    
    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return f"{self.staff.staff_id} - {self.name}"


# ==============================================
#   3) Attendance Model
# ==============================================
class Attendance(models.Model):
    attendance_id = models.AutoField(primary_key=True)
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='attendances')
    date = models.DateField(default=timezone.localdate)
    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    overtime_hours = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=10, choices=ATTENDANCE_STATUS, default='Present')

    class Meta:
        unique_together = ('staff', 'date')

    def __str__(self):
        return f"Attendance - {self.staff.name} - {self.date}"