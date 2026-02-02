# accounts/models.py

import os
from decimal import Decimal
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
    ('Active', 'Active'),
    ('Inactive', 'Inactive'),
    ('Late', 'Late'),
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

    check_in = models.TimeField(null=True, blank=True)
    check_out = models.TimeField(null=True, blank=True)
    
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
    status = models.CharField(max_length=10, choices=ATTENDANCE_STATUS, default='Inactive')

    class Meta:
        pass


# ==============================================
#   4) GoogleMeet Model
# ==============================================
class GoogleMeet(models.Model):
    meet_id = models.AutoField(primary_key=True)
    job_type = models.CharField(max_length=100)
    meet_time = models.DateTimeField()
    meet_title = models.CharField(max_length=255)
    meet_description = models.TextField(blank=True, null=True)
    meet_link = models.CharField(max_length=500, blank=True, null=True)

    def __str__(self):
        return f"{self.meet_title} - {self.job_type}"


# ==============================================
#   5) WorkSchedule Model
# ==============================================
WORK_STATUS_CHOICES = [
    ('Pending','Pending'),
    ('Completed','Completed'),
    ('Rescheduled','Rescheduled'),
    ('Incomplete','Incomplete'),
]

EVENT_TYPE_CHOICES = [
    ('Office','Office'),
    ('Client','Client'),
    ('Leave','Leave'),
    ('WFH','WFH'),
    ('Other','Other'),
]

REPEAT_CHOICES = [
    ('none','None'),
    ('daily','Daily'),
    ('weekly','Weekly'),
    ('monthly','Monthly'),
]

class WorkSchedule(models.Model):
    schedule_id = models.AutoField(primary_key=True)
    staff = models.ForeignKey('Staff', on_delete=models.CASCADE, related_name='work_schedules')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)

    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES, default='Office')
    repeat = models.CharField(max_length=16, choices=REPEAT_CHOICES, default='none')
    repeat_until = models.DateField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=WORK_STATUS_CHOICES, default='Pending')
    admin_notes = models.TextField(blank=True, null=True)
    staff_response = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def duration_minutes(self):
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return max(0, int(delta.total_seconds() // 60))
        return 0

    def __str__(self):
        return f"{self.title} ({self.staff}) - {self.start_time.date() if self.start_time else ''}"


# ==============================================
#   5) Emotion Model
# ==============================================
class Emotion(models.Model):
    EMOTION_CHOICES = [
        ('Happy', 'Happy'),
        ('Sad', 'Sad'),
        ('Neutral', 'Neutral'),
        ('Angry', 'Angry'),
        ('Tired', 'Tired'),
        ('Focused', 'Focused'),
    ]

    emotion_id = models.AutoField(primary_key=True)
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='emotions')
    emotion_type = models.CharField(max_length=20, choices=EMOTION_CHOICES)
    timestamp = models.DateTimeField()

    def __str__(self):
        return f"{self.staff} - {self.emotion_type} @ {self.timestamp}"


# ==============================================
#   6) Productivity Model
# ==============================================    
class Productivity(models.Model):
    productivity_id = models.AutoField(primary_key=True)
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="productivity_records")
    datetime = models.DateTimeField(default=timezone.now)
    keystroke = models.IntegerField(default=0, help_text="Total number of keystrokes")
    mouse_moves = models.IntegerField(default=0, help_text="Total mouse movements or clicks")
    productivity_score = models.DecimalField(default=0.0, max_digits=6, decimal_places=2, help_text="Calculated productivity score")

    def __str__(self):
        return f"Productivity {self.productivity_id} - Staff {self.staff.staff_id}"


# ==============================================
#   7) Feedback Model
# ==============================================  
class Feedback(models.Model):
    feedback_id = models.AutoField(primary_key=True)
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name="feedbacks")
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.staff.name} - {self.message[:20]}"


# ==============================================
#   8) IssueReport Model
# ==============================================  
class IssueReport(models.Model):
    issue_id = models.AutoField(primary_key=True)
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='issues')
    current_problem = models.TextField()
    root_cause = models.TextField(blank=True, null=True)
    proposed_action = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    reviewed = models.BooleanField(default=False)

    def __str__(self):
        return f"Issue: {self.staff} @ {self.created_at}"