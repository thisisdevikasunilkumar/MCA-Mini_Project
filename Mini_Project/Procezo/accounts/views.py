import pytz
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import uuid, json
from tkinter import Image
from PIL import Image
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponseBadRequest
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.urls import reverse
from datetime import datetime, timedelta
from .models import Staff, Register, Attendance
# Import the utility function
from .utils_face import pil_from_base64, count_faces, get_embedding_from_pil, save_base64_to_contentfile, cosine_similarity_vec, compare_two_images

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