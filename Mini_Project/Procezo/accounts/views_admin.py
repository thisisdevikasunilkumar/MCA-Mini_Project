import pytz
from django.utils import timezone
from datetime import date, datetime, timedelta
import os
import shutil
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.utils import timezone
from django.urls import reverse
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from django.db.models import Q
from datetime import datetime, timedelta, time as dtime
from django.utils.dateparse import parse_date, parse_time
from django.middleware.csrf import get_token
from django.core.serializers.json import DjangoJSONEncoder
from .models import Staff, Register, Attendance, GoogleMeet, WorkSchedule, Emotion, Feedback, IssueReport, Productivity
from .models import EVENT_TYPE_CHOICES


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

# ..............................................................
# -------------------- Admin Dashboard URLs --------------------
# ..............................................................


# Admin dashboard view
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



# Save meeting (AJAX POST)
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



# Admin attendance management view
def admin_attendance_management(request):
    # Fetch all staff
    staff_list = Staff.objects.all()
    # Fetch all attendance records
    attendance = Attendance.objects.select_related("staff").order_by('-date', '-attendance_id')

    today = today_india()
    week_start = today - timedelta(days=7)
    five_months_ago = today - timedelta(days=150)

    # ATTENDANCE COUNTS FOR TODAY
    active_count = Attendance.objects.filter(date=today, status='Active').count()
    inactive_count = Attendance.objects.filter(date=today, status='Inactive').count()
    late_count = Attendance.objects.filter(date=today, status='Late').count()

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

    context = {
            "staff_list": staff_list,
            "attendance": attendance,
            "attendance_list": attendance_list,
            "stats": {
                "active_today": active_count,
                "inactive_today": inactive_count,
                "late_today": late_count,
            },
    }

    return render(
        request,
        "admin/Attendance Management.html",
        context
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



# ---------------- Work Schedule Management ----------------
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
@csrf_exempt
@require_POST
def work_schedule_create(request):
    try:
        data = json.loads(request.body.decode())
    except json.JSONDecodeError:
        # CRITICAL FIX: Always return JSON on error
        return JsonResponse({'success': False, 'error': 'Invalid request data. Expected JSON.'}, status=400)
    except Exception as e:
        print(f"Request decode error: {e}")
        return JsonResponse({'success': False, 'error': 'Could not read request body.'}, status=400)

    print(f"DEBUG: Received data = {data}")
    
    title = data.get('title')
    staff_id = data.get('staff')
    date_s = data.get('date')
    event_type = data.get('event_type','Office')
    description = data.get('description', '')
    repeat = data.get('repeat','none')
    repeat_until = data.get('repeat_until')

    if not (title and staff_id and date_s):
        return JsonResponse({'success': False, 'error': 'Missing required fields (Title, Staff, Date).'}, status=400)

    print(f"DEBUG: title={title}, staff_id={staff_id}, date_s={date_s}, event_type={event_type}")

    try:
        staff = Staff.objects.get(staff_id=staff_id)
    except Staff.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Invalid staff member selected.'}, status=400)

    try:
        # Parse date - handle both YYYY-MM-DD and DD-MM-YYYY formats
        date_obj = parse_date(date_s)
        if not date_obj:
            # Try alternative format DD-MM-YYYY
            try:
                date_obj = datetime.strptime(date_s, '%d-%m-%Y').date()
            except:
                raise ValueError(f"Invalid date format: {date_s}")
        
        repeat_until_dt = parse_date(repeat_until) if repeat_until else None

        # Create datetime objects - full day schedule (00:00:00 to 23:59:59)
        start_dt = datetime.combine(date_obj, dtime.min)
        end_dt = datetime.combine(date_obj, dtime.max)
        
        print(f"DEBUG: Parsed dates - start_dt={start_dt}, end_dt={end_dt}")
    except ValueError as ve:
        print(f"DEBUG: Date parse error: {ve}")
        return JsonResponse({'success': False, 'error': f'Invalid Date or Time format. {str(ve)}'}, status=400)

    if has_conflict(staff, start_dt, end_dt):
        return JsonResponse({'success': False, 'error': 'Conflict detected: Staff is already scheduled at this time.'}, status=400)

    created = []
    try:
        print(f"DEBUG: Creating schedule with event_type={event_type}")
        
        # Validate event_type
        valid_event_types = [choice[0] for choice in EVENT_TYPE_CHOICES]
        if event_type not in valid_event_types:
            print(f"DEBUG: Invalid event_type. Valid options: {valid_event_types}")
            event_type = 'Office'  # Default to Office if invalid
        
        s = WorkSchedule.objects.create(
            title=title,
            staff=staff,
            start_time=start_dt,
            end_time=end_dt,
            event_type=event_type,
            description=description,
            repeat=repeat,
            repeat_until=repeat_until_dt,
            status='Pending'
        )
        print(f"DEBUG: Schedule created successfully with ID {s.schedule_id}")
        
        # Format the newly created event
        created.append({
            'id': s.schedule_id,
            'title': s.title,
            'staff_id': staff.staff_id,
            'staff_name': staff.name,
            'date': s.start_time.strftime('%Y-%m-%d'),
            'start': '',
            'end': '',
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

                new_start_time = datetime.combine(cur, dtime.min)
                new_end_time = datetime.combine(cur, dtime.max)
                
                ns = WorkSchedule.objects.create(
                    title=s.title, staff=staff, start_time=new_start_time,
                    end_time=new_end_time, event_type=s.event_type, description=s.description, status='Pending'
                )
                created.append({
                    'id': ns.schedule_id, 'title': ns.title, 'staff_id': staff.staff_id, 
                    'staff_name': staff.name, 'date': ns.start_time.strftime('%Y-%m-%d'), 
                    'start': '',
                    'end': '',
                    'event_type': ns.event_type, 'description': ns.description or '',
                })

        return JsonResponse({'success': True, 'created': created})

    except Exception as db_e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Database Save Error: {db_e}")
        print(f"Traceback: {error_trace}")
        return JsonResponse({
            'success': False, 
            'error': f'Server error: {str(db_e)}'
        }, status=500)


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



# Admin key logs management view
def admin_KeyLogs_management(request):
    return render(request, 'admin/Key Logs Management.html')



# Admin emotion management view
def admin_emotion_management(request):
    today = date.today()
    last_week_day = today - timedelta(days=7)

    # -----------------------------
    # GET FILTER VALUES
    # -----------------------------
    status = request.GET.get('status', '').strip()
    staff_id_q = request.GET.get('staff_id', '').strip()
    staff_name_q = request.GET.get('staff_name', '').strip()

    filters_applied = any([status, staff_id_q, staff_name_q])

    # -----------------------------
    # STAFF QUERYSET
    # -----------------------------
    staff_qs = Staff.objects.all()

    if staff_id_q:
        staff_qs = staff_qs.filter(staff_id__icontains=staff_id_q)

    if staff_name_q:
        staff_qs = staff_qs.filter(name__icontains=staff_name_q)

    staff_qs = staff_qs.order_by('staff_id')

    # -----------------------------
    # TODAY EMOTION COUNTS (LATEST PER STAFF)
    # -----------------------------
    emotion_counts = {
        'Happy': 0,
        'Sad': 0,
        'Neutral': 0,
        'Angry': 0,
        'Tired': 0,
        'Focused': 0,
    }

    today_emotions = (
        Emotion.objects
        .filter(timestamp__date=today)
        .order_by('staff', '-timestamp')
    )

    seen_staff = set()

    for emo in today_emotions:
        if emo.staff_id not in seen_staff:
            seen_staff.add(emo.staff_id)
            if emo.emotion_type in emotion_counts:
                emotion_counts[emo.emotion_type] += 1

    total_today_responses = sum(emotion_counts.values())

    # -----------------------------
    # POSITIVE TODAY %
    # -----------------------------
    positive_today_percent = 0
    if total_today_responses > 0:
        positive_today_percent = round(
            ((emotion_counts['Happy'] + emotion_counts['Focused']) / total_today_responses) * 100
        )

    # -----------------------------
    # LAST WEEK POSITIVE %
    # -----------------------------
    last_week_emotions = (
        Emotion.objects
        .filter(timestamp__date=last_week_day)
        .order_by('staff', '-timestamp')
    )

    last_week_seen = set()
    last_week_positive = 0

    for emo in last_week_emotions:
        if emo.staff_id not in last_week_seen:
            last_week_seen.add(emo.staff_id)
            if emo.emotion_type in ['Happy', 'Focused']:
                last_week_positive += 1

    last_week_total = len(last_week_seen)

    last_week_positive_percent = 0
    if last_week_total > 0:
        last_week_positive_percent = round(
            (last_week_positive / last_week_total) * 100
        )

    # -----------------------------
    # POSITIVE CHANGE %
    # -----------------------------
    positive_change = positive_today_percent - last_week_positive_percent

    # -----------------------------
    # INDIVIDUAL REPORTS
    # -----------------------------
    reports = []

    for staff in staff_qs:

        if filters_applied:
            emotion_qs = Emotion.objects.filter(staff=staff)

            if status:
                emotion_qs = emotion_qs.filter(emotion_type=status)
                if not emotion_qs.exists():
                    continue

            latest_emotion = emotion_qs.order_by('-timestamp').first()
        else:
            latest_emotion = Emotion.objects.filter(
                staff=staff,
                timestamp__date=today
            ).order_by('-timestamp').first()

        latest_productivity = (
            Productivity.objects.filter(staff=staff)
            .order_by('-date')
            .first()
            if filters_applied else
            Productivity.objects.filter(staff=staff, date=today).first()
        )

        latest_feedback = (
            Feedback.objects.filter(staff=staff)
            .order_by('-created_at')
            .first()
            if filters_applied else
            Feedback.objects.filter(staff=staff, created_at__date=today)
            .order_by('-created_at')
            .first()
        )

        latest_issue = (
            IssueReport.objects.filter(staff=staff)
            .order_by('-created_at')
            .first()
            if filters_applied else
            IssueReport.objects.filter(staff=staff, created_at__date=today)
            .order_by('-created_at')
            .first()
        )

        reports.append({
            'staff': staff,
            'emotion': latest_emotion,
            'productivity': latest_productivity,
            'feedback': latest_feedback,
            'issue': latest_issue,
        })

    # -----------------------------
    # CONTEXT
    # -----------------------------
    context = {
        'reports': reports,
        'today': today,
        'filters_applied': filters_applied,
        'emotion_counts': emotion_counts,
        'positive_today_percent': positive_today_percent,
        'positive_change': positive_change,
        'responses_today': total_today_responses,
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