import pytz
from django.utils import timezone
from datetime import date, timedelta
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.utils.html import strip_tags
from django.db.models import Q
from datetime import timedelta
from .models import Staff, Register, Attendance, GoogleMeet, WorkSchedule, Emotion, Feedback, IssueReport, Productivity
# Import the utility function
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
    attendance = Attendance.objects.filter(staff=staff, date=today).first()

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
    todays_meets = GoogleMeet.objects.filter(meet_time__date=today, job_type=staff.job_type).order_by('meet_time')

    # ✔ Count meetings for this staff
    todays_meet_count = todays_meets.count()

    tasks = WorkSchedule.objects.filter(staff=staff).order_by('-start_time')

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
            'todays_meet_count': todays_meet_count,
            'tasks': tasks,
            'stats': {
                "tasks_completed": tasks.filter(staff_response="Complete").count(),
                "tasks_pending": tasks.filter(staff_response="Pending").count(),
            }            
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
    # 1. Basic Date Setup
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    first_day_of_month = today.replace(day=1)
    five_months_ago = today - timedelta(days=150)

    # 2. Identify the Staff
    staff_id = request.session.get('staff_id')
    if not staff_id:
        # Redirect to login if session is missing
        return redirect('login') 
    
    staff = get_object_or_404(Staff, staff_id=staff_id)

    # 3. Monthly Stats (For the Dashboard/Cards)
    # This remains consistent regardless of the table filters
    monthly_data = Attendance.objects.filter(
        staff=staff,
        date__gte=first_day_of_month,
        date__lte=today
    )
    
    monthly_active_count = monthly_data.filter(status='Active').count()
    monthly_inactive_count = monthly_data.filter(status='Inactive').count()
    monthly_late_count = monthly_data.filter(status='Late').count()
    
    all_attendance_data = Attendance.objects.filter(
        staff=staff,
        date__year__gte=2020,
        date__year__lte=2030
    )

    attendance_map = {
        record.date.strftime('%Y-%m-%d'): record.status 
        for record in all_attendance_data
    }

    # 4. Filtering Logic for the Table
    status_filter = request.GET.get('status')
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')

    # Start with all records for this specific staff
    attendance_records = Attendance.objects.filter(staff=staff)

    # Apply Date Range Filter
    if from_date and to_date:
        attendance_records = attendance_records.filter(
            date__range=[from_date, to_date],
            date__gte=five_months_ago  # Security limit
        )
    else:
        # Default: Show current week's records
        attendance_records = attendance_records.filter(
            date__gte=start_of_week,
            date__lte=today
        )

    # Apply Status Filter (only if 'All' is not selected)
    if status_filter:
        attendance_records = attendance_records.filter(status=status_filter)

    # Final ordering (Newest first)
    attendance_records = attendance_records.order_by('-date')

    context = {
        'staff': staff,
        'attendance_records': attendance_records,
        'attendance_map': attendance_map,
        'monthly_active_count': monthly_active_count,
        'monthly_inactive_count': monthly_inactive_count,
        'monthly_late_count': monthly_late_count,
        'start_of_week': start_of_week,
    }
    
    return render(request, 'staff/Attendance.html', context)




# Staff work schedule view
def staff_WorkSchedule(request):
    staff_id = request.session.get('staff_id')
    if not staff_id:
        return redirect('accounts:login_register')

    staff = get_object_or_404(Staff, staff_id=staff_id)

    today = today_india()
    next_week = today + timedelta(days=7)

    todays_meets = GoogleMeet.objects.filter(meet_time__date=today, job_type=staff.job_type).order_by('meet_time')

    tasks = WorkSchedule.objects.filter(staff=staff).order_by('-start_time')

    context = {
        'staff': staff,
        'todays_meets': todays_meets,
        'todays_meet_count': todays_meets.count(),
        'tasks': tasks,
        'stats': {
            "meeting_today": todays_meets.count(),
            "total_hours": 0,
            "tasks_completed": tasks.filter(staff_response="Complete").count()
        }
    }

    return render(request, 'staff/Staff Work Schedule.html', context)


@require_POST
def update_staff_response(request):
    schedule_id = request.POST.get("schedule_id")
    response = request.POST.get("response")
    staff_id = request.session.get('staff_id')

    if not staff_id:
        return JsonResponse({"success": False, "error": "Session expired. Please login again."}, status=401)

    try:
        task = WorkSchedule.objects.get(schedule_id=schedule_id)

        # Security Check
        if str(task.staff.staff_id) != str(staff_id):
            return JsonResponse({"success": False, "error": "Permission denied"}, status=403)

        task.staff_response = response
        task.save(update_fields=["staff_response"])

        return JsonResponse({"success": True})

    except WorkSchedule.DoesNotExist:
        return JsonResponse({"success": False, "error": "Task not found"}, status=404)
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)




# Staff emotion view
def staff_emotion(request):
    # 1) Logged-in staff id session-il ninnu edukunu
    staff_id = request.session.get('staff_id')
    if not staff_id:
        return render(request, 'staff/Emotion.html')

    staff = get_object_or_404(Staff, staff_id=staff_id)
    today = date.today()

    # 2) Stat cards-il kaanikkan vendi TODAY'S counts mathram edukunu
    emotions_today_query = Emotion.objects.filter(staff=staff, timestamp__date=today)
    
    emotion_counts = {
        "Happy": emotions_today_query.filter(emotion_type="Happy").count(),
        "Sad": emotions_today_query.filter(emotion_type="Sad").count(),
        "Neutral": emotions_today_query.filter(emotion_type="Neutral").count(),
        "Angry": emotions_today_query.filter(emotion_type="Angry").count(),
        "Tired": emotions_today_query.filter(emotion_type="Tired").count(),
        "Focused": emotions_today_query.filter(emotion_type="Focused").count(),
    }

    # 3) Table-ile data (Filtering logic ivide aanu)
    # Default aayi ee staff-inte ella data-yum edukkunnu
    all_emotions = Emotion.objects.filter(staff=staff).order_by('-timestamp')

    # URL-il ninnu filter parameters edukkunu
    status_q = request.GET.get('status', '').strip()
    date_q = request.GET.get('date', '').strip()

    # Status filter apply cheyyunnu
    if status_q:
        all_emotions = all_emotions.filter(emotion_type=status_q)

    # Date filter apply cheyyunnu
    if date_q:
        all_emotions = all_emotions.filter(timestamp__date=date_q)

    # 4) Feedback details
    feedback_list = Feedback.objects.filter(staff=staff).order_by('-created_at')

    context = {
        'staff': staff,
        'emotion_counts': emotion_counts,
        'all_emotions': all_emotions,
        'feedback_count': feedback_list.count(),
        'feedback_list': feedback_list,
        'selected_status': status_q,
        'selected_date': date_q,
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