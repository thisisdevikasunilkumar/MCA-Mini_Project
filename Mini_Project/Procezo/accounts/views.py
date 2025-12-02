from datetime import date, timedelta
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
from django.core.files.storage import default_storage
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from django.db.models import Q
from .models import Staff, Register, Attendance
from .forms import StaffRegisterForm
from .utils_face import pil_from_base64, count_faces, get_embedding_from_pil, save_base64_to_contentfile, cosine_similarity_vec, compare_two_images

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


# Face login API (POST)    
@csrf_exempt
def api_face_login(request):
    try:
        body = request.body.decode('utf-8') or "{}"
        data = json.loads(body)
        img_b64 = data.get('image')
        email = data.get('email')  # optional

        if not img_b64:
            return JsonResponse({"success": False, "error": "No image provided"})

        pil = pil_from_base64(img_b64)
        if pil is None:
            return JsonResponse({"success": False, "error": "Invalid image"})

        if count_faces(pil) != 1:
            return JsonResponse({"success": False, "error": f"Require exactly 1 face. Found: {count_faces(pil)}"})

        emb = get_embedding_from_pil(pil)
        if emb is None:
            return JsonResponse({"success": False, "error": "Could not compute embedding"})

        threshold = float(getattr(settings, 'FACE_SIMILARITY_THRESHOLD', 0.60))

        # If email provided -> check only that user
        if email:
            try:
                staff = Register.objects.get(email=email)
            except Register.DoesNotExist:
                return JsonResponse({"success": False, "error": "No account with that email"})

            if not staff.face_embedding:
                return JsonResponse({"success": False, "error": "No face registered for this account"})

            raw_emb = staff.face_embedding
            stored = json.loads(raw_emb) if isinstance(raw_emb, str) else raw_emb
            sim = cosine_similarity_vec(emb, stored)
            if sim >= threshold:
                # login success: set session, attendance, redirect
                request.session['staff_id'] = staff.staff.staff_id
                request.session['staff_role'] = staff.role.lower()
                today = timezone.localdate()
                att, _ = Attendance.objects.get_or_create(staff=staff.staff, date=today)
                if not att.check_in:
                    att.check_in = timezone.localtime().time()
                    att.save()
                redirect_url = reverse('accounts:staff_dashboard') if staff.role.lower() == 'staff' else reverse('accounts:admin_dashboard')
                return JsonResponse({"success": True, "redirect": redirect_url, "name": staff.name})
            else:
                return JsonResponse({"success": False, "error": "Face did not match."})

        # No email provided: search all candidates
        candidates = Register.objects.exclude(face_embedding__isnull=True).exclude(face_embedding__exact='')
        best_staff = None
        best_sim = -1.0
        for s in candidates:
            raw_emb = s.face_embedding
            try:
                stored = json.loads(raw_emb) if isinstance(raw_emb, str) else raw_emb
            except Exception:
                continue
            sim = cosine_similarity_vec(emb, stored)
            if sim > best_sim:
                best_sim = sim
                best_staff = s

        if best_staff and best_sim >= threshold:
            staff = best_staff
            request.session['staff_id'] = staff.staff_id
            request.session['staff_role'] = staff.role.lower()
            today = timezone.localdate()
            att, _ = Attendance.objects.get_or_create(staff=staff, date=today)
            if not att.check_in:
                att.check_in = timezone.localtime().time()
                att.save()
            redirect_url = reverse('accounts:staff_dashboard') if staff.role.lower() == 'staff' else reverse('accounts:admin_dashboard')
            return JsonResponse({"success": True, "redirect": redirect_url, "name": staff.name})

        return JsonResponse({"success": False, "error": "No matching user found."})
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
    
# ..............................................................
# -------------------- Admin Dashboard URLs --------------------
# ..............................................................

def admin_dashboard(request):
    today = date.today()
    tomorrow = today + timedelta(days=1)
    next_week = today + timedelta(days=7)

    # Upcoming birthdays (next 7 days)
    upcoming_birthdays = Register.objects.filter(
        Q(dob__month=today.month, dob__day__gte=today.day) |
        Q(dob__month=next_week.month, dob__day__lte=next_week.day)
    ).order_by('dob__month', 'dob__day')[:5]

    # Birthdays this week (count only)
    birthday_this_week_count = Register.objects.filter(
        Q(dob__month=today.month, dob__day__gte=today.day) |
        Q(dob__month=next_week.month, dob__day__lte=next_week.day)
    ).count()

    # Staff details
    recent_staff = Staff.objects.order_by('-created_at')[:5] # <-- last 5 created accounts
    staff_count = Staff.objects.count() # <-- total staff count

    return render(request, 'admin/Admin Dashboard.html', {
        'recent_staff': recent_staff,
        'staff_count': staff_count,
        'upcoming_birthdays': upcoming_birthdays,
        'birthday_this_week_count': birthday_this_week_count,
        'today': today,
        'tomorrow': tomorrow
    })

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
    return render(request, "admin/Attendance Management.html")

def admin_emotion_management(request):
    return render(request, "admin/Emotion Management.html")

# ..............................................................
# -------------------- Staff Dashboard URLs --------------------
# ..............................................................

# Staff dashboard view
def staff_dashboard(request):
    staff_id = request.session.get('staff_id')
    if not staff_id:
        return redirect('accounts:login_register')
    
    staff = get_object_or_404(Staff, staff_id=staff_id)

    today = timezone.localdate()
    next_week = today + timedelta(days=7)

    # Today's attendance
    attendance = Attendance.objects.filter(
        staff=staff,
        date=today
    ).first()

    # Birthdays this week (count)
    birthday_this_week_count = Register.objects.filter(
        Q(dob__month=today.month, dob__day__gte=today.day) |
        Q(dob__month=next_week.month, dob__day__lte=next_week.day)
    ).count()

    # Or if you want the actual list (optional)
    birthday_this_week_list = Register.objects.filter(
        Q(dob__month=today.month, dob__day__gte=today.day) |
        Q(dob__month=next_week.month, dob__day__lte=next_week.day)
    ).order_by('dob__month', 'dob__day')

    return render(
        request,
        'staff/Staff Dashboard.html',
        {
            'staff': staff,
            'attendance': attendance,
            'birthday_this_week_count': birthday_this_week_count,
            'birthday_this_week_list': birthday_this_week_list
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
    staff = None
    staff_id = request.session.get('staff_id')
    if staff_id:
        staff = get_object_or_404(Staff, staff_id=staff_id)
    context = {
        'staff': staff
    }
    return render(request, 'staff/Attendance.html',context) 

def staff_emotion(request):
    staff = None
    staff_id = request.session.get('staff_id')
    if staff_id:
        staff = get_object_or_404(Staff, staff_id=staff_id)
    context = {
        'staff': staff
    }    
    return render(request, 'staff/Emotion.html',context)