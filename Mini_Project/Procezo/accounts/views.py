import pytz
from django.utils import timezone
from datetime import date, datetime, timedelta
from decimal import Decimal
import os
import shutil
import base64, io, uuid, json
from tkinter import Image
from PIL import Image
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.core.files.base import ContentFile
from django.contrib.auth.hashers import make_password, check_password
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from django.db.models import Count
from django.core.files.storage import default_storage
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from django.db.models import Q
from datetime import datetime, timedelta, time as dtime
from django.utils.dateparse import parse_date, parse_time
from django.middleware.csrf import get_token
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Max
from .models import Staff, Register, Attendance, GoogleMeet, WorkSchedule, Emotion, Feedback, IssueReport, Productivity
from .forms import StaffRegisterForm
# Import the utility function
from .utils_face import pil_from_base64, count_faces, get_embedding_from_pil, save_base64_to_contentfile, cosine_similarity_vec, compare_two_images
from .utils import detect_emotion_from_base64_image 

# ---------------- Timezone helpers ----------------
INDIA_TZ = pytz.timezone("Asia/Kolkata")

def now_india():
    """Return timezone-aware datetime in Asia/Kolkata."""
    return timezone.now().astimezone(INDIA_TZ)

def today_india():
    """Return date in Asia/Kolkata."""
    return now_india().date()

def time_india():
    """Return time() in Asia/Kolkata."""
    return now_india().time()

# Render main page
def main_page(request):
    return render(request, 'Main Page.html')

# Render login/register page
def login_register(request):
    return render(request, 'Login Registration Form.html')

# Auto-fill staff details by staff_ID
def get_staff_details(request):
    staff_id = request.GET.get('staff_ID') or request.GET.get('staff_id')
    if not staff_id:
        return JsonResponse({"exists": False})
    try:
        staff = Staff.objects.get(staff_id=staff_id)
        return JsonResponse({
            "exists": True,
            "staff_id": staff.staff_id,
            "name": staff.name,
            "email": staff.email,
            "role": staff.role.capitalize(),
            "job_type": staff.job_type,
        })
    except Staff.DoesNotExist:
        return JsonResponse({"exists": False})

# Basic face check API
@csrf_exempt
def api_check_face(request):
    try:
        body = request.body.decode('utf-8') or "{}"
        data = json.loads(body)
        img_b64 = data.get('image')
        if not img_b64:
            return JsonResponse({"error": "No image received", "face_count": 0}, status=400)
        pil = pil_from_base64(img_b64)
        if pil is None:
            return JsonResponse({"error": "Invalid image", "face_count": 0}, status=400)
        fc = count_faces(pil)
        return JsonResponse({"error": None, "face_count": fc})
    except Exception as e:
        return JsonResponse({"error": str(e), "face_count": 0}, status=500)

# Register staff (form POST)
@csrf_exempt
def register_staff(request):
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    # Parse JSON for AJAX
    if is_ajax:
        try:
            data = json.loads(request.body)
        except:
            return JsonResponse({"success": False, "error": "Invalid JSON"})
    else:
        data = request.POST

    if request.method != "POST":
        error_msg = {"success": False, "error": "POST required"}
        return JsonResponse(error_msg) if is_ajax else HttpResponseBadRequest("POST required")

    try:
        # ------------------------------------------------------------
        # EXTRACT FIELDS
        # ------------------------------------------------------------
        name = data.get("name")
        email = data.get("email")
        password = data.get("password")
        role = data.get("role") or "Staff"
        job_type = data.get("job_type")
        gender = data.get("gender")

        face_image_b64 = data.get("image")
        profile_image_b64 = data.get("profile_image")

        if not email:
            return JsonResponse({"success": False, "error": "Email is required"})

        if not password and not is_ajax:
            messages.error(request, "Password is required.")
            return redirect("accounts:login_register")

        staff_obj = Staff.objects.get(email=email)

        # ---------- Face Embedding ----------
        emb = None
        if face_image_b64:
            pil = pil_from_base64(face_image_b64)
            if not pil:
                return JsonResponse({"success": False, "error": "Invalid face image"})

            if count_faces(pil) != 1:
                return JsonResponse({"success": False, "error": "❌ Image must contain exactly 1 face"})

            emb = get_embedding_from_pil(pil)

        # -------- Face Match with Staff Profile --------
        if face_image_b64 and staff_obj.profile_image:
            stored = Image.open(staff_obj.profile_image.path).convert("RGB")

            if not compare_two_images(pil, stored):
                return JsonResponse({"success": False, "error": "❌ Face mismatch! Profile image & captured face do not match."})


        # ---------- Create or Update ----------
        register_obj, created = Register.objects.get_or_create(staff=staff_obj)

        register_obj.email = email
        register_obj.name = name
        register_obj.role = role
        register_obj.gender = gender
        register_obj.job_type = job_type

        # ---------- Password ----------
        if password:
            register_obj.set_password(password)

        # ---------- Save Face Data ----------
        if emb:
            register_obj.face_embedding = emb

            filename = f"{staff_obj.staff_id}_{uuid.uuid4().hex[:8]}.jpg"
            face_file = save_base64_to_contentfile(face_image_b64, filename)
            register_obj.face_capture.save(filename, face_file, save=False)

        # PROFILE IMAGE → COPY FROM STAFF
        if staff_obj.profile_image:
            register_obj.profile_image = staff_obj.profile_image

        register_obj.save()

        # ------------------------------------------------------------
        # SUCCESS
        # ------------------------------------------------------------
        if is_ajax:
            return JsonResponse({"success": True})

        messages.success(request, "Registration successful.")
        return redirect("accounts:login_register")

    except Exception as e:
        if is_ajax:
            return JsonResponse({"success": False, "error": str(e)})
        messages.error(request, f"Error: {e}")
        return redirect("accounts:login_register")


# ---------------- Face login (check-in) ----------------
@csrf_exempt
def api_face_login(request):
    try:
        body = request.body.decode('utf-8') or "{}"
        data = json.loads(body)
        img_b64 = data.get('image')
        email = data.get('email')

        if not img_b64:
            return JsonResponse({"success": False, "error": "No image provided"})

        pil = pil_from_base64(img_b64)
        if pil is None:
            return JsonResponse({"success": False, "error": "Invalid image"})

        faces = count_faces(pil)
        if faces != 1:
            return JsonResponse({"success": False, "error": f"Require exactly 1 face. Found: {faces}"})

        emb = get_embedding_from_pil(pil)
        if emb is None:
            return JsonResponse({"success": False, "error": "Could not compute embedding"})

        threshold = float(getattr(request, 'FACE_SIMILARITY_THRESHOLD', 0.60))
        staff = None

        # Authentication Logic
        if email:
            try:
                register_instance = Register.objects.get(email=email)
                staff = register_instance.staff
            except Register.DoesNotExist:
                return JsonResponse({"success": False, "error": "No account with that email"})

            if not getattr(register_instance, "face_embedding", None):
                return JsonResponse({"success": False, "error": "No face registered for this account"})

            raw_emb = register_instance.face_embedding
            stored = json.loads(raw_emb) if isinstance(raw_emb, str) else raw_emb
            sim = cosine_similarity_vec(emb, stored)
            if sim < threshold:
                return JsonResponse({"success": False, "error": "Face did not match."})

        else:
            candidates = Register.objects.exclude(face_embedding__isnull=True).exclude(face_embedding__exact='')
            best_staff_register = None
            best_sim = -1.0
            for r in candidates:
                raw_emb = r.face_embedding
                try:
                    stored = json.loads(raw_emb) if isinstance(raw_emb, str) else raw_emb
                except Exception:
                    continue
                sim = cosine_similarity_vec(emb, stored)
                if sim > best_sim:
                    best_sim = sim
                    best_staff_register = r

            if best_staff_register and best_sim >= threshold:
                staff = best_staff_register.staff
            else:
                return JsonResponse({"success": False, "error": "No matching user found."})

        # Attendance Logic (Check-In)
        current_time = time_india()         # India-local time
        today = today_india()

        # Determine Late: compare staff.check_in (admin-set schedule) with current_time
        is_late = False
        if staff.check_in:  # admin-set required check_in time
            # give 10 minute grace
            req_dt = datetime.combine(today, staff.check_in).astimezone(INDIA_TZ)
            actual_dt = datetime.combine(today, current_time).astimezone(INDIA_TZ)
            grace_end = req_dt + timedelta(minutes=10)
            if actual_dt > grace_end:
                is_late = True

        # Create rows per the rules:
        # - Late: create a 'Late' row (with check_in), then create 'Active' row (check_out null)
        # - On-time: create only an 'Active' row
        if is_late:
            # Late incident row
            Attendance.objects.create(
                staff=staff,
                date=today,
                check_in=current_time,
                check_out=None,
                status='Late',
                overtime_hours=Decimal('0.00')
            )

            # Active session row
            att = Attendance.objects.create(
                staff=staff,
                date=today,
                check_in=current_time,
                check_out=None,
                status='Active',
                overtime_hours=Decimal('0.00')
            )
            final_status = 'Late/Active'
        else:
            att = Attendance.objects.create(
                staff=staff,
                date=today,
                check_in=current_time,
                check_out=None,
                status='Active',
                overtime_hours=Decimal('0.00')
            )
            final_status = 'Active'

        # store session info for convenience
        request.session['staff_id'] = staff.staff_id
        request.session['staff_role'] = staff.role.lower()
        request.session['is_active'] = True

        redirect_url = reverse('accounts:staff_dashboard') if staff.role.lower() == 'staff' else reverse('accounts:admin_dashboard')

        return JsonResponse({"success": True, "redirect": redirect_url, "name": staff.name, "status": final_status})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


# Password login (POST)
@csrf_exempt
def api_login_with_password(request):
    try:
        # Accept form-encoded or JSON
        if request.content_type and 'application/json' in request.content_type:
            data = json.loads(request.body.decode('utf-8') or "{}")
            email = data.get('email')
            password = data.get('password')
        else:
            email = request.POST.get('email')
            password = request.POST.get('password')

        if not email or not password:
            return JsonResponse({"success": False, "error": "Email and password required."})

        # Hard-coded admin (optional)
        if email == "admin@gmail.com" and password == "admin@123":
            request.session['staff_role'] = 'admin'
            request.session['staff_id'] = 'ADMIN'
            return JsonResponse({"success": True, "redirect": reverse('accounts:admin_dashboard')})

        try:
            staff = Register.objects.get(email=email)
        except Register.DoesNotExist:
            return JsonResponse({"success": False, "error": "Invalid credentials."})

        if staff.check_password(password):
            if staff.role.lower() == 'staff':
                # Password is correct for staff, now require face recognition.
                # The front-end will take the email and call api_face_login.
                return JsonResponse({"success": True, "face_required": True, "email": staff.email})
            else:
                # For any other role (e.g., admin), log in directly without face check.
                request.session['staff_id'] = staff.staff_id
                request.session['staff_role'] = staff.role.lower()
                redirect_url = reverse('accounts:admin_dashboard')
                return JsonResponse({"success": True, "redirect": redirect_url})
        else:
            return JsonResponse({"success": False, "error": "Invalid credentials."})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


# ---------------- Overtime calculation ----------------
# def calculate_overtime(required_checkout_time, actual_checkout_time):
#     """
#     required_checkout_time: python datetime.time or None
#     actual_checkout_time: python datetime.time
#     Returns decimal hours rounded to 2 decimals.
#     """
#     if not required_checkout_time:
#         return Decimal('0.00')

#     # convert to datetimes on the same arbitrary date
#     dt_required = datetime.combine(datetime.today(), required_checkout_time)
#     dt_actual = datetime.combine(datetime.today(), actual_checkout_time)

#     if dt_actual > dt_required:
#         overtime_td = dt_actual - dt_required
#         overtime_hours = Decimal(overtime_td.total_seconds() / 3600).quantize(Decimal('0.01'))
#         return overtime_hours
#     return Decimal('0.00')

@csrf_exempt
def api_face_logout(request):
    try:
        body = request.body.decode('utf-8') or "{}"
        data = json.loads(body)
        email = data.get('email')
        staff = None

        # Identify staff (email or session)
        if email:
            try:
                staff = Register.objects.get(email=email).staff
            except Register.DoesNotExist:
                return JsonResponse({"success": False, "error": "User not found with that email."})
        elif 'staff_id' in request.session:
            staff_id = request.session.get('staff_id')
            staff = Staff.objects.get(staff_id=staff_id)
        else:
            return JsonResponse({"success": False, "error": "Authentication required for check-out (No email or session ID)."})

        today = today_india()
        current_time = time_india()

        # Find the most recent Active session (latest check_in) for today
        active_qs = Attendance.objects.filter(
            staff=staff,
            date=today,
            status='Active',
            check_out__isnull=True
        ).order_by('-check_in')
        active_att = active_qs.first()

        if not active_att:
            return JsonResponse({"success": False, "error": "No active Check-In record found for today. Please Check In first."})

        # -----------------------------
        # ✔ FIXED OVERTIME CALCULATION LOGIC
        # -----------------------------
        overtime_amount = None  # store None by default

        if staff.check_out:  # Staff shift end time is defined
            checkout_dt = datetime.combine(today, current_time)
            required_dt = datetime.combine(today, staff.check_out)

            if checkout_dt > required_dt:
                diff_seconds = (checkout_dt - required_dt).total_seconds()
                overtime_amount = round(Decimal(diff_seconds) / Decimal(3600), 2)  # hours (decimal)

        # 1) Create NEW 'Inactive' row
        new_att = Attendance.objects.create(
            staff=staff,
            date=today,
            check_in=active_att.check_in,
            check_out=current_time,
            status='Inactive',
            overtime_hours=overtime_amount  # store None when no overtime
        )

        # 2) ALSO update the Active row's check_out so both rows show check_out (user wanted that)
        #    (This preserves the original 'Active' row but records its check_out timestamp.)
        active_att.check_out = current_time
        # Optionally you might want to keep Active status (still 'Active') or mark something else.
        # We'll leave its status as 'Active' but now with a check_out for visibility.
        active_att.save(update_fields=['check_out'])

        # Clear session variables
        for key in ('staff_id', 'staff_role', 'is_active'):
            if key in request.session:
                del request.session[key]

        return JsonResponse({
            "success": True,
            "message": f"Checked out at {new_att.check_out}. Overtime: {new_att.overtime_hours} hours.",
            "checkout_time": str(new_att.check_out),
            "status": new_att.status,
            "overtime_hours": float(new_att.overtime_hours)
        })

    except Staff.DoesNotExist:
        return JsonResponse({"success": False, "error": "Staff profile not found."})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})

# ..............................................................
# -------------------- Admin Dashboard URLs --------------------
# ..............................................................

def admin_dashboard(request):
    # ---------------------------------------------
    # DATE HANDLING
    # ---------------------------------------------
    today = today_india()                 # <-- Updated
    tomorrow = today + timedelta(days=1)
    next_week = today + timedelta(days=7)

    # ---------------------------------------------
    # SCHEDULED MEETINGS (store & query naive India-local datetimes because USE_TZ=False)
    # ---------------------------------------------
    start_of_day = datetime.combine(today, datetime.min.time())
    end_of_day = datetime.combine(today, datetime.max.time())
    todays_meetings = GoogleMeet.objects.filter(meet_time__range=(start_of_day, end_of_day)).order_by('meet_time')

    # ---------------------------------------------
    # UPCOMING BIRTHDAYS (next 7 days)
    # ---------------------------------------------
    upcoming_birthdays = Register.objects.filter(
        Q(dob__month=today.month, dob__day__gte=today.day) |
        Q(dob__month=next_week.month, dob__day__lte=next_week.day)
    ).order_by('dob__month', 'dob__day')[:5]

    # BIRTHDAY COUNT THIS WEEK
    birthday_this_week_count = Register.objects.filter(
        Q(dob__month=today.month, dob__day__gte=today.day) |
        Q(dob__month=next_week.month, dob__day__lte=next_week.day)
    ).count()

    # ---------------------------------------------
    # STAFF DETAILS
    # ---------------------------------------------
    recent_staff = Staff.objects.order_by('-created_at')[:5]
    staff_count = Staff.objects.count()

    # ---------------------------------------------
    # ATTENDANCE COUNTS
    # ---------------------------------------------
    active_count = Attendance.objects.filter(date=today, status='Active').count()
    inactive_count = Attendance.objects.filter(date=today, status='Inactive').count()
    late_count = Attendance.objects.filter(date=today, status='Late').count()
    
    register_list = Register.objects.select_related("staff").all()
    # ---------------------------------------------
    # CONTEXT
    # ---------------------------------------------
    context = {
        'recent_staff': recent_staff,
        'staff_count': staff_count,
        'upcoming_birthdays': upcoming_birthdays,
        'birthday_this_week_count': birthday_this_week_count,
        'today': today,
        'tomorrow': tomorrow,
        "stats": {
            "active_today": active_count,
            "inactive_today": inactive_count,
            "late_today": late_count,
        },
        "register_list": register_list,
        "todays_meetings": todays_meetings,
    }
    return render(request, 'admin/Admin Dashboard.html', context)

# Admin staff search view
def admin_staff_search(request):
    query = request.GET.get("q", "")

    results = Staff.objects.filter(
        Q(name__icontains=query) |
        Q(email__icontains=query) |
        Q(staff_id__icontains=query) |
        Q(role__icontains=query) |
        Q(job_type__icontains=query)
    )

    return render(request, "admin/Admin Search Results.html", {
        "results": results,
        "query": query,
    })

@csrf_exempt
def save_meeting(request):
    if request.method != "POST":
        return JsonResponse({"success": False})

    try:
        data = json.loads(request.body.decode('utf-8'))

        job_type = data["job_type"]
        meet_time = data["meet_time"].strip()   # always HH:MM (24-hour)
        title = data["meet_title"]
        desc = data["meet_description"]
        link = data["meet_link"]
        
        # ----------------------------------------------------------
        # 1) Parse ONLY 24-hour format ("HH:MM")
        # ----------------------------------------------------------
        try:
            time_obj = datetime.strptime(meet_time, "%H:%M").time()
        except:
            raise ValueError("Time must be in 24-hour format (e.g., 16:15)")

        # ----------------------------------------------------------
        # 2) Today's India date
        # ----------------------------------------------------------
        ist = pytz.timezone("Asia/Kolkata")
        today_india = datetime.now(ist).date()

        # ----------------------------------------------------------
        # 3) Combine date + time → save as naive datetime
        # ----------------------------------------------------------
        final_datetime = datetime.combine(today_india, time_obj)

        # ----------------------------------------------------------
        # 4) Save to DB
        # ----------------------------------------------------------
        GoogleMeet.objects.create(
            job_type=job_type,
            meet_time=final_datetime,
            meet_title=title,
            meet_description=desc,
            meet_link=link,
        )

        return JsonResponse({"success": True})

    except Exception as e:
        print("ERROR:", e)
        return JsonResponse({"success": False, "error": str(e)})


# Admin staff management view
def admin_staff_management(request):
    query = request.GET.get("q", "")   # read search input

    if query:
        staff_list = Staff.objects.filter(
            Q(staff_id__icontains=query) |
            Q(name__icontains=query) |
            Q(email__icontains=query) |
            Q(role__icontains=query) |
            Q(job_type__icontains=query)
        ).order_by('-created_at')
    else:
        staff_list = Staff.objects.all().order_by('-created_at')

    return render(request, 'admin/Staff Management.html', {
        "staff_list": staff_list,
        "query": query
    })

# ---------------------------------------------------------
# ADD / UPDATE STAFF
# ---------------------------------------------------------
def add_new_staff(request, staff_id=None):
    staff = None

    # UPDATE mode
    if staff_id:
        staff = get_object_or_404(Staff, staff_id=staff_id)

    if request.method == "POST":

        name = request.POST.get("full_name")
        email = request.POST.get("email")
        role = request.POST.get("role")
        gender = request.POST.get("gender")
        job_type = request.POST.get("job_type")
        system_id = request.POST.get("system_id")
        profile_image = request.FILES.get("profile_image")

        # ----------------------------------
        # UPDATE STAFF
        # ----------------------------------
        if staff:
            staff.name = name
            staff.email = email
            staff.role = role
            staff.gender = gender
            staff.job_type = job_type
            staff.system_id = system_id

            if profile_image:
                staff.profile_image = profile_image

            staff.save()

            # ---------- EMAIL FOR UPDATE ----------
            html_content = f"""
            <p>Dear <b>{name}</b>,</p>
            <p>Your staff profile has been <b>updated successfully</b>.</p>
            <p><b>Updated Details:</b></p>
            <ul>
                <li><b>Staff ID:</b> <span style="color:red;">{staff.staff_id}</span></li>
                <li><b>Name:</b> {name}</li>
                <li><b>Role:</b> {role}</li>
                <li><b>Job Type:</b> {job_type}</li>
            </ul>
            <p>If you did not request this change, please contact the admin immediately.</p>
            <p>Regards,<br>Admin Team</p>
            """
            text_content = strip_tags(html_content)

            email_message = EmailMultiAlternatives(
                subject="Your Staff Profile has been Updated",
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email]
            )
            email_message.attach_alternative(html_content, "text/html")
            email_message.send()

            messages.success(request, "Staff Updated Successfully!")
            return redirect("accounts:add_new_staff")

        # ----------------------------------
        # INSERT NEW STAFF
        # ----------------------------------
        staff = Staff.objects.create(
            name=name,
            email=email,
            role=role,
            gender=gender,
            job_type=job_type,
            system_id=system_id,
            profile_image=profile_image,
        )


        # ---------------- EMAIL FOR INSERT ----------------
        html_content = f"""
        <p>Dear <b>{name}</b>,</p>
        <p>Welcome to the team! Your account has been <b>successfully created</b>.</p>
        <p><b>Here are your login details:</b></p>
        <ul>
            <li><b>Staff ID :</b> <span style="color:red;">{staff.staff_id}</span></li>
            <li><b>Name:</b> {name}</li>
            <li><b>Role:</b> {role}</li>
            <li><b>Job Type:</b> {job_type}</li>
        </ul>
        <p>Use these credentials to log in to the system. Update your complete profile details after registering.</p>
        <p>Regards,<br>Admin Team</p>
        """

        text_content = strip_tags(html_content)

        email_message = EmailMultiAlternatives(
            subject="Welcome to the Team! Your Account Details",
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email]
        )
        email_message.attach_alternative(html_content, "text/html")
        email_message.send()

        messages.success(request, f"Staff Created Successfully! Staff ID: {staff.staff_id}")
        return redirect("accounts:add_new_staff")

    # GET request (load form)
    return render(request, "admin/New Staff.html", {
        "staff": staff,
        "is_update": True if staff_id else False
    })


# ---------------------------------------------------------
# UPDATE STAFF
# ---------------------------------------------------------
def update_staff(request, staff_id):
    return add_new_staff(request, staff_id)

# ---------------------------------------------------------
# DELETE STAFF
# ---------------------------------------------------------
def delete_staff(request, staff_id):
    staff = get_object_or_404(Staff, staff_id=staff_id)

    name = staff.name
    email = staff.email
    job_type = staff.job_type
    role = staff.role

    # -------- DELETE PROFILE FOLDER --------
    profile_folder = os.path.join(settings.MEDIA_ROOT, "profiles", staff_id)
    if os.path.exists(profile_folder):
        shutil.rmtree(profile_folder)  # deletes entire folder

    # -------- DELETE FACE FOLDER --------
    face_folder = os.path.join(settings.MEDIA_ROOT, "faces", staff_id)
    if os.path.exists(face_folder):
        shutil.rmtree(face_folder)

    # Delete staff record
    staff.delete()

    # ---------- EMAIL FOR DELETE ----------
    html_content = f"""
    <p>Dear <b>{name}</b>,</p>
    <p>Your staff account has been <b>removed</b> from the system.</p>
    <p><b>Removed Account:</b></p>
    <ul>
        <li><b>Staff ID:</b> <span style="color:red;">{staff_id}</span></li>
        <li><b>Name:</b> {name}</li>
        <li><b>Role:</b> {role}</li>
        <li><b>Job Type:</b> {job_type}</li>
    </ul>
    <p>If you think this is a mistake, please contact the admin immediately.</p>
    <p>Regards,<br>Admin Team</p>
    """

    text_content = strip_tags(html_content)

    email_message = EmailMultiAlternatives(
        subject="Your Staff Account has been Deleted",
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email]
    )
    email_message.attach_alternative(html_content, "text/html")
    email_message.send()

    messages.success(request, "Staff Deleted Successfully!")
    return redirect("accounts:admin_staff_management")

def admin_attendance_management(request):
    # Fetch all staff
    staff_list = Staff.objects.all()
    # Fetch all attendance records
    attendance = Attendance.objects.select_related("staff").order_by('-date', '-attendance_id')

    today = timezone.now().date()
    week_start = today - timedelta(days=7)
    five_months_ago = today - timedelta(days=150)

    # GET values
    status = request.GET.get('status')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    staff_id = request.GET.get('staff_id')
    staff_name = request.GET.get('staff_name')

    attendance_list = Attendance.objects.select_related("staff")

    # ---------------- DATE FILTER ----------------
    # If user selects date range → allow up to 5 months
    if from_date and to_date:
        attendance_list = attendance_list.filter(
            date__range=[from_date, to_date],
            date__gte=five_months_ago
        )
    else:
        # Default → last 7 days
        attendance_list = attendance_list.filter(date__gte=week_start)

    # ---------------- STATUS FILTER ----------------
    # If status is empty (All) → NO filter applied
    if status:
        attendance_list = attendance_list.filter(status=status)

    # ---------------- STAFF FILTERS ----------------
    if staff_id:
        attendance_list = attendance_list.filter(
            staff__staff_id__icontains=staff_id
        )

    if staff_name:
        attendance_list = attendance_list.filter(
            staff__name__icontains=staff_name
        )

    # ---------------- ORDERING ----------------
    attendance_list = attendance_list.order_by('-date', '-attendance_id')

    return render(
        request,
        "admin/Attendance Management.html",
        {
            "staff_list": staff_list,
            "attendance": attendance,
            "attendance_list": attendance_list
        }
    )

@csrf_exempt
def save_attendanceTime_to_staff(request):
    if request.method == "POST":
        if not request.body:
            return JsonResponse({"success": False, "error": "No data provided"})
            
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON format"})

        staff_id = data.get("staffId")
        check_in = data.get("checkIn") # HH:MM format from JS
        check_out = data.get("checkOut") # HH:MM format from JS
            
        if not staff_id:
            return JsonResponse({"success": False, "error": "Staff ID is missing"})

        try:
            staff = Staff.objects.get(staff_id=staff_id)
                
            if check_in is not None:
                staff.check_in = check_in
            if check_out is not None:
                staff.check_out = check_out
                    
            staff.save()

            staff_email = staff.email
            staff_name = staff.name

            html_content = f"""
            <p>Dear <b>{staff_name}</b>,</p>
            <p>Your attendance time has been successfully <b>saved/set</b> in the system.</p>
            <p>This is the required time you should login.</p>
            <p><b>Your Scheduled Times:</b></p>
            <ul>
                <li><b>Staff ID:</b> <span style="color:black;">{staff_id}</span></li>
                <li><b>Check-In Time:</b> <span style="color:green;">{check_in or 'Not Set'}</span></li>
                <li><b>Check-Out Time:</b> <span style="color:green;">{check_out or 'Not Set'}</span></li>
            </ul>
            <p>If you have any queries, please contact the admin team.</p>
            <p>Regards,<br>Admin Team</p>
            """

            text_content = strip_tags(html_content)

            email_message = EmailMultiAlternatives(
                subject="Attendance Time Set Confirmation",
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[staff_email]
            )
            email_message.attach_alternative(html_content, "text/html")
            email_message.send()

            return JsonResponse({"success": True})
        
        except Staff.DoesNotExist:
            return JsonResponse({"success": False, "error": f"Staff with ID {staff_id} not found"})
        except Exception as e:
            return JsonResponse({"success": False, "error": f"Operation error: {str(e)}"})

    return JsonResponse({"success": False, "error": "Invalid request method. Only POST is allowed"})

def has_conflict(staff, start_dt, end_dt, exclude_id=None):
    if not start_dt or not end_dt:
        return False
    
    # Find schedules that overlap with the given time range.
    # An overlap occurs if (s.start_time < end_dt) and (s.end_time > start_dt).
    qs = WorkSchedule.objects.filter(
        staff=staff,
        start_time__lt=end_dt,
        end_time__gt=start_dt
    )
    if exclude_id:
        qs = qs.exclude(schedule_id=exclude_id)
        
    return qs.exists()

# --- PAGE RENDERING VIEW ---
def admin_work_schedule_page(request):
    staff_list = Staff.objects.all().order_by('name')
    schedules = WorkSchedule.objects.select_related('staff').all()
    events = []
    for s in schedules:
        if not s.start_time:
            continue
        events.append({
            'id': s.schedule_id,
            'title': s.title,
            'staff_id': s.staff.staff_id if hasattr(s.staff,'staff_id') else s.staff.pk,
            'staff_name': getattr(s.staff,'name',str(s.staff)),
            'date': s.start_time.strftime('%Y-%m-%d'),
            'start': s.start_time.strftime('%H:%M'),
            'end': s.end_time.strftime('%H:%M') if s.end_time else '',
            'event_type': s.event_type,
            'repeat': getattr(s, 'repeat', 'none'),
            'description': s.description or '',
        })
    context = {
        'staff_list': staff_list,
        'events_json': json.dumps(events),
        'api_urls': {
            'events': '/accounts/admin/work_schedules/api/events/',
            'create': '/accounts/admin/work_schedules/api/create/',
            'update': '/accounts/admin/work_schedules/api/update/{id}/',
            'delete': '/accounts/admin/work_schedules/api/delete/{id}/',
        },
        'csrf_token': get_token(request),
    }
    return render(request, 'admin/Admin Work Schedule.html', context)

# --- API VIEWS ---

# API: Get all schedules (Used for calendar refresh)
def work_schedules_json(request):
    qs = WorkSchedule.objects.select_related('staff').all()
    events = []
    for s in qs:
        # ... (same logic as in admin_work_schedule_page for formatting) ...
        if not s.start_time: continue
        events.append({
            'id': s.schedule_id,
            'title': s.title,
            'staff_id': s.staff.staff_id if hasattr(s.staff,'staff_id') else s.staff.pk,
            'staff_name': getattr(s.staff,'name',str(s.staff)),
            'date': s.start_time.strftime('%Y-%m-%d'),
            'start': s.start_time.strftime('%H:%M'),
            'end': s.end_time.strftime('%H:%M') if s.end_time else '',
            'event_type': s.event_type,
            'description': s.description or '',
        })
    return JsonResponse({'events': events})


# API: Create schedule (The primary fix target)
@require_POST
def work_schedule_create(request):
    try:
        data = json.loads(request.body.decode())
    except json.JSONDecodeError:
        # CRITICAL FIX: Always return JSON on error
        return JsonResponse({'success': False, 'error': 'Invalid request data. Expected JSON.'}, status=400)
    except Exception:
        return JsonResponse({'success': False, 'error': 'Could not read request body.'}, status=400)

    title = data.get('title')
    staff_id = data.get('staff')
    date_s = data.get('date')
    start_s = data.get('start')
    end_s = data.get('end')
    event_type = data.get('event_type','Office')
    description = data.get('description', '')
    repeat = data.get('repeat','none')
    repeat_until = data.get('repeat_until')

    if not (title and staff_id and date_s):
        return JsonResponse({'success': False, 'error': 'Missing required fields (Title, Staff, Date).'}, status=400)

    try:
        staff = Staff.objects.get(staff_id=staff_id)
    except Staff.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Invalid staff member selected.'}, status=400)

    try:
        date_obj = parse_date(date_s)
        start_t = parse_time(start_s) if start_s else dtime.min 
        end_t = parse_time(end_s) if end_s else None
        repeat_until_dt = parse_date(repeat_until) if repeat_until else None

        start_dt = datetime.combine(date_obj, start_t)
        end_dt = datetime.combine(date_obj, end_t) if date_obj and end_t else None
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Invalid Date or Time format. Ensure time is HH:MM.'}, status=400)

    if has_conflict(staff, start_dt, end_dt):
        return JsonResponse({'success': False, 'error': 'Conflict detected: Staff is already scheduled at this time.'}, status=400)

    created = []
    try:
        s = WorkSchedule.objects.create(
            title=title,
            staff=staff,
            start_time=start_dt,
            end_time=end_dt,
            event_type=event_type,
            description=description,
            repeat=repeat,
            repeat_until=repeat_until_dt
        )
        
        # Format the newly created event
        created.append({
            'id': s.schedule_id,
            'title': s.title,
            'staff_id': staff.staff_id,
            'staff_name': staff.name,
            'date': s.start_time.strftime('%Y-%m-%d'),
            'start': s.start_time.strftime('%H:%M'),
            'end': s.end_time.strftime('%H:%M') if s.end_time else '',
            'event_type': s.event_type,
            'description': s.description or '',
        })
        
        # Repeating schedule logic (copied from your previous code)
        if s.repeat != 'none' and s.repeat_until:
            cur = s.start_time.date()
            while True:
                # ... (timedelta logic for daily, weekly, monthly) ...
                if s.repeat == 'daily': cur += timedelta(days=1)
                elif s.repeat == 'weekly': cur += timedelta(weeks=1)
                elif s.repeat == 'monthly': cur += timedelta(days=30) 
                
                if cur > s.repeat_until: break

                new_start_time = datetime.combine(cur, s.start_time.time())
                new_end_time = datetime.combine(cur, s.end_time.time()) if s.end_time else None
                
                ns = WorkSchedule.objects.create(
                    title=s.title, staff=staff, start_time=new_start_time,
                    end_time=new_end_time, event_type=s.event_type, description=s.description, status='Pending'
                )
                created.append({
                    'id': ns.schedule_id, 'title': ns.title, 'staff_id': staff.staff_id, 
                    'staff_name': staff.name, 'date': ns.start_time.strftime('%Y-%m-%d'), 
                    'start': ns.start_time.strftime('%H:%M'),
                    'end': ns.end_time.strftime('%H:%M') if ns.end_time else '',
                    'event_type': ns.event_type, 'description': ns.description or '',
                })

        return JsonResponse({'success': True, 'created': created})

    except Exception as db_e:
        print(f"Database Save Error: {db_e}")
        return JsonResponse({'success': False, 'error': f'A server error occurred while saving: {db_e}'}, status=500)


# API: Update schedule
@require_POST
def work_schedule_update(request, pk):
    try:
        data = json.loads(request.body.decode())
    except:
        return JsonResponse({'success': False, 'error': 'Invalid request data. Expected JSON.'}, status=400)
        
    try:
        s = get_object_or_404(WorkSchedule, schedule_id=pk)
    except:
        return JsonResponse({'success': False, 'error': 'Schedule not found.'}, status=404)
        
    try:
        # Apply updates
        new_date = parse_date(data['date']) if 'date' in data and data.get('date') else s.start_time.date()
        new_start_time_part = parse_time(data['start']) if 'start' in data and data.get('start') else s.start_time.time()
        
        if 'end' in data:
            new_end_time_part = parse_time(data['end']) if data.get('end') else None
        else:
            new_end_time_part = s.end_time.time() if s.end_time else None

        if new_date and new_start_time_part:
            s.start_time = datetime.combine(new_date, new_start_time_part)
        
        if new_date and new_end_time_part:
            s.end_time = datetime.combine(new_date, new_end_time_part)
        else:
            s.end_time = None

        if 'title' in data: s.title = data.get('title')
        if 'event_type' in data: s.event_type = data.get('event_type')
        if 'description' in data: s.description = data.get('description')
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Invalid Date or Time format.'}, status=400)
        
    if has_conflict(s.staff, s.start_time, s.end_time, exclude_id=s.schedule_id):
        return JsonResponse({'success': False, 'error': 'Conflict detected'}, status=400)
    
    try:
        s.save()
        return JsonResponse({'success': True})
    except Exception as db_e:
        return JsonResponse({'success': False, 'error': f'Failed to save update: {db_e}'}, status=500)


# API: Delete schedule
@require_POST
def work_schedule_delete(request, pk):
    try:
        s = get_object_or_404(WorkSchedule, schedule_id=pk)
        s.delete()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Failed to delete schedule: {e}'}, status=500)
        
# --- Placeholder/Helper Views ---
def admin_work_schedule_list(request): return admin_work_schedule_page(request)
  
def staff_work_schedule_list(request):
    """
    Renders the schedule list page for a logged-in staff member.
    """
    # Assuming staff_id is stored in the session upon login
    staff_id = request.session.get("staff_id") 
    
    # Use the appropriate field (e.g., staff_id or pk) to look up the Staff object
    # If your Staff model uses 'staff_id' as the unique identifier:
    try:
        staff = get_object_or_404(Staff, staff_id=staff_id)
    except Exception as e:
        # Handle case where staff_id is missing or invalid in session
        # You might redirect them to login or show an error
        print(f"Error fetching staff: {e}") 
        # For now, let's assume it works or raises the 404
        return render(request, 'staff/Work Schedule List.html', {'schedules': []})

    # Filter schedules only for the current staff member
    schedules = WorkSchedule.objects.filter(staff=staff).order_by('start_time')
    
    return render(request, 'staff/Work Schedule List.html', {'schedules': schedules})


@require_POST
def staff_mark_complete(request, schedule_id):
    """
    Marks a specific WorkSchedule item as complete for staff view.
    It should typically be restricted to POST requests for state changes.
    """
    try:
        # 1. Retrieve the schedule item
        schedule = get_object_or_404(WorkSchedule, schedule_id=schedule_id)

        # OPTIONAL: Add a check to ensure the schedule belongs to the logged-in user
        # staff_id = request.session.get("staff_id")
        # if str(schedule.staff.staff_id) != staff_id:
        #     messages.error(request, "Permission denied.")
        #     return redirect('staff_work_schedule_list') 
        
        # 2. Update the status field (assuming your model has a 'status' field)
        schedule.status = 'Complete'
        schedule.save()
        
        # 3. Provide feedback and redirect
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            # Handle AJAX request
            return JsonResponse({'success': True, 'message': 'Schedule marked as complete.'})
        else:
            # Handle standard form submission/redirect
            messages.success(request, f"Schedule '{schedule.title}' marked as complete.")
            return redirect('staff_work_schedule_list') # Redirect back to the list view

    except WorkSchedule.DoesNotExist:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'Schedule not found.'}, status=404)
        else:
            messages.error(request, "Schedule item not found.")
            return redirect('staff_work_schedule_list')
    
    except Exception as e:
        # Log the error (optional) and return a friendly message
        print(f"Error marking schedule complete: {e}")
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'error': 'An internal error occurred.'}, status=500)
        else:
            messages.error(request, "An unexpected error occurred.")
            return redirect('staff_work_schedule_list')
        

# Note: If your front-end uses GET requests for this action, remove the @require_POST decorator.
# However, POST is strongly recommended for operations that change data (like marking complete).

@require_POST
def staff_reschedule(request, schedule_id):
    """
    Handles a staff request to reschedule an existing WorkSchedule item.
    Expects AJAX POST request with new 'date', 'start', and/or 'end' times.
    """
    try:
        # 1. Attempt to retrieve schedule and parse data
        schedule = get_object_or_404(WorkSchedule, schedule_id=schedule_id)
        
        # Check if the request is JSON (common for modals/AJAX updates)
        if request.content_type == 'application/json':
            data = json.loads(request.body.decode())
        else:
            # Fallback for form data (less common for AJAX PUT/PATCH logic)
            data = request.POST
        
        # Get and parse new data
        new_date_s = data.get('date')
        new_start_s = data.get('start')
        new_end_s = data.get('end')

        # 2. Update schedule object fields if new data is provided
        updated = False
        
        new_date = parse_date(new_date_s) if new_date_s else schedule.start_time.date()
        
        if new_start_s:
            new_start_time_part = parse_time(new_start_s)
            schedule.start_time = datetime.combine(new_date, new_start_time_part)
            updated = True
        elif new_date_s: # date changed but not time
            schedule.start_time = schedule.start_time.replace(year=new_date.year, month=new_date.month, day=new_date.day)
            updated = True

        if new_end_s:
            if schedule.end_time:
                new_end_time_part = parse_time(new_end_s)
                schedule.end_time = datetime.combine(new_date, new_end_time_part)
            updated = True
        elif 'end' in data and not data.get('end'):
            schedule.end_time = None
            updated = True
        elif new_date_s and schedule.end_time: # date changed but not time
            schedule.end_time = schedule.end_time.replace(year=new_date.year, month=new_date.month, day=new_date.day)
            updated = True

        # 3. Validation and Conflict Check
        if not updated:
            return JsonResponse({'success': False, 'error': 'No reschedule data provided.'}, status=400)

        # Assuming has_conflict is available
        if has_conflict(schedule.staff, schedule.start_time, schedule.end_time, exclude_id=schedule.schedule_id):
            return JsonResponse({'success': False, 'error': 'Reschedule failed: Conflict detected with another shift.'}, status=400)
            
        # 4. Save and return success
        schedule.save()
        
        # Return success response for AJAX
        return JsonResponse({'success': True, 'message': 'Schedule successfully updated.'})

    except WorkSchedule.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Schedule item not found.'}, status=404)
        
    except (ValueError, TypeError):
        # Catches errors from parse_date/parse_time if the format is bad
        return JsonResponse({'success': False, 'error': 'Invalid date or time format provided.'}, status=400)
        
    except Exception as e:
        print(f"Reschedule error: {e}")
        return JsonResponse({'success': False, 'error': f'An internal server error occurred: {e}'}, status=500)

 
def work_schedules_page(request):
    schedules = WorkSchedule.objects.all()

    events = []
    for s in schedules:
        if not s.start_time:
            continue
        events.append({
            "id": s.schedule_id,
            "title": s.title,
            "staff": s.staff.staff_id,
            "event_type": s.event_type,
            "start": s.start_time.isoformat(),
            "end": s.end_time.isoformat() if s.end_time else None,
            "date": s.start_time.strftime("%Y-%m-%d"),
            "description": s.description,
        })

    return render(request, "admin/work_schedules.html", {
        "staff_list": Staff.objects.all(),
        "events_json": json.dumps(events, cls=DjangoJSONEncoder),
        "api_urls": json.dumps({
            "create": reverse("accounts:work_schedule_create"),
            "update": "/accounts/admin/work_schedules/api/update/<id>/",
            "delete": "/accounts/admin/work_schedules/api/delete/<id>/",
            "events": reverse("accounts:work_schedules_json")
        })
    })
    
def admin_emotion_management(request):
    today = date.today()

    # ------------------------------------
    # 1) TODAY'S EMOTIONS (FULL QUERYSET)
    # ------------------------------------
    emotions_today = Emotion.objects.filter(timestamp__date=today)

    # ------------------------------------
    # DISTINCT STAFF COUNTS PER EMOTION (CORRECTED)
    # ------------------------------------
    emotion_counts = {
        "Happy": emotions_today.filter(emotion_type="Happy").values('staff').distinct().count(),
        "Sad": emotions_today.filter(emotion_type="Sad").values('staff').distinct().count(),
        "Neutral": emotions_today.filter(emotion_type="Neutral").values('staff').distinct().count(),
        "Angry": emotions_today.filter(emotion_type="Angry").values('staff').distinct().count(),
        "Tired": emotions_today.filter(emotion_type="Tired").values('staff').distinct().count(),
        "Focused": emotions_today.filter(emotion_type="Focused").values('staff').distinct().count(),
    }

    # ------------------------------------
    # 2) INDIVIDUAL STAFF REPORTS
    # ------------------------------------
    all_staff = Staff.objects.all().order_by('staff_id')
    reports = []

    for staff in all_staff:

        # Latest emotion for today, else latest overall
        latest_emotion = (
            Emotion.objects.filter(staff=staff, timestamp__date=today).order_by('-timestamp').first()
            or Emotion.objects.filter(staff=staff).order_by('-timestamp').first()
        )

        # Today's productivity or latest
        productivity_today = Productivity.objects.filter(
            staff=staff, date=today
        ).order_by('-date').first()

        latest_prod = productivity_today or (
            Productivity.objects.filter(staff=staff).order_by('-date').first()
        )

        # Latest feedback
        latest_feedback = Feedback.objects.filter(staff=staff).order_by('-created_at').first()

        # Latest issue
        latest_issue = IssueReport.objects.filter(staff=staff).order_by('-created_at').first()

        # Combine into report list
        reports.append({
            'staff': staff,
            'emotion': latest_emotion,      # can be None
            'productivity': latest_prod,    # can be None
            'feedback': latest_feedback,    # can be None
            'issue': latest_issue,          # can be None
        })

    # ------------------------------------
    # CONTEXT
    # ------------------------------------
    context = {
        'emotion_counts': emotion_counts,
        'reports': reports,
        'today': today,
    }

    return render(request, 'admin/Emotion Management.html', context)


@csrf_exempt
def ajax_submit_feedback(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Invalid request method"})

    try:
        data = json.loads(request.body.decode("utf-8"))

        staff_id = data.get("staff_id")
        message = data.get("message")

        if not staff_id or not message:
            return JsonResponse({"ok": False, "error": "Missing data"})

        staff = Staff.objects.get(pk=staff_id)

        Feedback.objects.create(
            staff=staff,
            message=message
        )

        return JsonResponse({"ok": True})

    except Staff.DoesNotExist:
        return JsonResponse({"ok": False, "error": "Staff not found"})

    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)})

def submit_issue(request):
    if request.method == 'POST':
        data = json.loads(request.body.decode('utf-8'))
        staff_id = data.get('staff_id')
        current_problem = data.get('current_problem', '').strip()
        root_cause = data.get('root_cause', '').strip()
        proposed_action = data.get('proposed_action', '').strip()
        if not current_problem:
            return JsonResponse({'ok': False, 'error': 'Current problem required'}, status=400)
        staff = get_object_or_404(Staff, pk=staff_id)
        issue = IssueReport.objects.create(
            staff=staff,
            current_problem=current_problem,
            root_cause=root_cause,
            proposed_action=proposed_action
        )
        return JsonResponse({'ok': True, 'issue_id': issue.issue_id})
    return JsonResponse({'ok': False}, status=405)

# ..............................................................
# -------------------- Staff Dashboard URLs --------------------
# ..............................................................

# Staff dashboard view
def staff_dashboard(request):
    staff_id = request.session.get('staff_id')
    if not staff_id:
        return redirect('accounts:login_register')
    
    staff = get_object_or_404(Staff, staff_id=staff_id)

    today = today_india()
    next_week = today + timedelta(days=7)

    # ------------ Attendance ------------
    attendance = Attendance.objects.filter(
        staff=staff,
        date=today
    ).first()

    # ------------ Birthday (this week) ------------
    birthday_this_week_count = Register.objects.filter(
        Q(dob__month=today.month, dob__day__gte=today.day) |
        Q(dob__month=next_week.month, dob__day__lte=next_week.day)
    ).count()

    birthday_this_week_list = Register.objects.filter(
        Q(dob__month=today.month, dob__day__gte=today.day) |
        Q(dob__month=next_week.month, dob__day__lte=next_week.day)
    ).order_by('dob__month', 'dob__day')

    # ------------ Upcoming Birthdays ------------
    upcoming_birthdays = Register.objects.filter(
        Q(dob__month=today.month, dob__day__gte=today.day) |
        Q(dob__month=next_week.month, dob__day__lte=next_week.day)
    ).order_by('dob__month', 'dob__day')[:5]

    # ------------ Today's Meetings (by staff.job_type) ------------
    todays_meets = GoogleMeet.objects.filter(
        meet_time__date=today,
        job_type=staff.job_type
    ).order_by('meet_time')

    # ✔ Count meetings for this staff
    todays_meet_count = todays_meets.count()

    return render(
        request,
        'staff/Staff Dashboard.html',
        {
            'staff': staff,
            'attendance': attendance,
            'birthday_this_week_count': birthday_this_week_count,
            'birthday_this_week_list': birthday_this_week_list,
            'upcoming_birthdays': upcoming_birthdays,
            'todays_meets': todays_meets,
            'todays_meet_count': todays_meet_count,  # ✔ Added
        }
    )


# Staff profile view
def staff_profile(request):
    staff_id = request.session.get("staff_id")

    if not staff_id:
        messages.error(request, "Session expired. Please log in again.")
        return redirect("accounts:login_register")

    # Fetch STAFF (master)
    staff = get_object_or_404(Staff, staff_id=staff_id)

    # Fetch REGISTER (login + personal data)
    register = Register.objects.filter(staff=staff).first()

    if request.method == "POST":

        # ------- UPDATE REGISTER FIELDS -------- #
        register.name = request.POST.get("full_name")
        register.email = request.POST.get("email")
        register.gender = request.POST.get("gender")
        register.phone = request.POST.get("phone")
        register.dob = request.POST.get("dob")
        register.country = request.POST.get("country")
        register.state = request.POST.get("state")
        register.city = request.POST.get("city")
        register.place = request.POST.get("place")
        register.pin_code = request.POST.get("pincode")

        # Profile Image update
        if "profile_image" in request.FILES:
            register.profile_image = request.FILES["profile_image"]

        register.save()

        messages.success(request, "Profile updated successfully!")
        return redirect("accounts:staff_profile")   # Refresh page

    # SEND BOTH MODELS
    context = {
        "staff": staff,
        "register": register,
    }
    return render(request, "staff/Staff Profile.html", context)

# Staff attendance view
def staff_attendance(request):
    # Imports like 'from django.shortcuts import render, get_object_or_404'
    # and 'from django.utils import timezone' are assumed
    
    today = date.today()
    first_day_of_month = today.replace(day=1)

    staff = None
    attendance_records = []
    attendance_map = {}
    
    # Initialize counts
    monthly_active_count = 0
    monthly_inactive_count = 0
    monthly_late_count = 0

    staff_id = request.session.get('staff_id')

    if staff_id:
        # Fetch staff object
        staff = get_object_or_404(Staff, staff_id=staff_id)
        
        # Filter attendance for the current month up to today
        monthly_attendance = Attendance.objects.filter(
            staff=staff,
            date__gte=first_day_of_month,
            date__lte=today
        ).order_by('-check_in')
        
        # Calculate counts
        monthly_active_count = monthly_attendance.filter(status='Active').count()
        monthly_inactive_count = monthly_attendance.filter(status='Inactive').count()
        monthly_late_count = monthly_attendance.filter(status='Late').count()
        
        # Set attendance records for the list view
        attendance_records = monthly_attendance
        
        # Build dictionary: { day: "Status" } for calendar view
        for record in monthly_attendance:
            attendance_map[record.date.day] = record.status
            
    # Note: The 'else' block for staff_id not present is handled by the initial
    # values (staff=None and counts=0)
            
    context = {
        'staff': staff,
        'attendance_records': attendance_records,  # List of records (latest first)
        'attendance_map': attendance_map,          # Map {day: status} for calendar
        'monthly_active_count': monthly_active_count,
        'monthly_inactive_count': monthly_inactive_count,
        'monthly_late_count': monthly_late_count,
    }
    
    return render(request, 'staff/Attendance.html', context)

def staff_emotion(request):
    # 1) Logged-in staff
    staff_id = request.session.get('staff_id')
    if not staff_id:
        return render(request, 'staff/Emotion.html')

    staff = get_object_or_404(Staff, staff_id=staff_id)

    # 2) Fetch ALL emotions of this staff (latest first)
    all_emotions = Emotion.objects.filter(staff=staff).order_by('-timestamp')

    # 3) Today's emotion counts
    today = date.today()
    emotions_today = all_emotions.filter(timestamp__date=today)

    emotion_counts = {
        "Happy": emotions_today.filter(emotion_type="Happy").count(),
        "Sad": emotions_today.filter(emotion_type="Sad").count(),
        "Neutral": emotions_today.filter(emotion_type="Neutral").count(),
        "Angry": emotions_today.filter(emotion_type="Angry").count(),
        "Tired": emotions_today.filter(emotion_type="Tired").count(),
        "Focused": emotions_today.filter(emotion_type="Focused").count(),
    }

    # 4) Feedback
    feedback_list = Feedback.objects.filter(staff=staff).order_by('-created_at')
    feedback_count = feedback_list.count()

    # 5) Send data to template
    context = {
        'staff': staff,
        'emotion_counts': emotion_counts,
        'emotions_today': emotions_today,
        'all_emotions': all_emotions,      # 👈 important
        'feedback_count': feedback_count,
        'feedback_list': feedback_list,
    }

    return render(request, 'staff/Emotion.html', context)


@csrf_exempt
def save_admin_reply(request):
    if request.method == "POST":
        data = json.loads(request.body)
        reply_text = data.get("reply_text")
        
        staff_id = request.session.get("staff_id")
        if not staff_id:
            return JsonResponse({"status": "error", "message": "Staff not logged in"})

        staff = Staff.objects.get(staff_id=staff_id)

        # Insert into IssueReport
        IssueReport.objects.create(
            staff=staff,
            current_problem=reply_text,
            created_at=timezone.now()
        )

        return JsonResponse({"status": "success"})

    return JsonResponse({"status": "error", "message": "Invalid request"})

@require_POST
def record_emotion(request):
    """
    Frontend-ൽ നിന്ന് ലഭിക്കുന്ന ക്യാമറ ഫ്രെയിമിൽ Emotion Detection നടത്തി ഡാറ്റാബേസിൽ സേവ് ചെയ്യുന്നു.
    ഇവിടെ 'Neutral' വികാരവും സേവ് ചെയ്യപ്പെടുന്നു.
    """
    staff_id = request.session.get('staff_id')
    
    try:
        if request.content_type != 'application/json':
            return JsonResponse({'status': 'error', 'message': 'Invalid Content-Type'}, status=400)

        data = json.loads(request.body)
        
        # Fallback staff_id logic (if session is missing, check payload)
        if not staff_id:
            staff_id = data.get('staff_id') or data.get('staffId')

        full_image_data = data.get('image', '')
        base64_image = full_image_data.split(',')[1] if ',' in full_image_data else full_image_data

    except (json.JSONDecodeError, IndexError, AttributeError) as e:
        return JsonResponse({'status': 'error', 'message': f'Invalid image data: {e}'}, status=400)

    # 1. Detect emotion
    detected_emotion = detect_emotion_from_base64_image(base64_image)

    print(f"record_emotion called: staff_id={staff_id} detected_emotion={detected_emotion}")

    # *** പ്രധാന മാറ്റം: None അല്ലെങ്കിൽ സേവ് ചെയ്യുക (Neutral ഉൾപ്പെടെ) ***
    if detected_emotion: 
        try:
            if not staff_id:
                return JsonResponse({'status': 'error', 'message': 'Staff not identified'}, status=401)

            staff = get_object_or_404(Staff, staff_id=staff_id) # Use get_object_or_404 for cleaner code
            
            # Timestamp calculation (assuming now_india and INDIA_TZ are defined elsewhere)
            # Use timezone.now() if you rely on Django's USE_TZ=True settings
            store_ts = timezone.now()
            
            print(f"Attempting to save emotion: staff={staff_id}, emotion={detected_emotion}, ts={store_ts}")

            obj = Emotion.objects.create(
                staff=staff,
                emotion_type=detected_emotion,
                timestamp=store_ts
            )

            print(f"Saved emotion record: id={obj.emotion_id}, emotion={obj.emotion_type}")

            return JsonResponse({'status': 'success', 'emotion': detected_emotion, 'id': obj.emotion_id, 'timestamp': str(obj.timestamp)})

        except Staff.DoesNotExist:
            print(f"record_emotion error: Staff not found for staff_id={staff_id}")
            return JsonResponse({'status': 'error', 'message': 'Staff not found'}, status=404)
        except Exception as e:
            print(f"Database save error: {e}")
            return JsonResponse({'status': 'error', 'message': 'Could not save emotion', 'error': str(e)}, status=500)
    else:
        # Returns info if detection failed (returned None)
        msg = 'Emotion detection failed on frame (returned None).'
        return JsonResponse({'status': 'info', 'message': msg, 'detected_emotion': detected_emotion}, status=200)