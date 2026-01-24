from django.urls import path
from . import views
from . import views_admin
from . import views_staff

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_register, name='login_register'),
    path('get_staff_details/', views.get_staff_details, name='get_staff_details'),
    path('register/', views.register_staff, name='register_staff'),

    # APIs
    path('api/check-face/', views.api_check_face, name='api_check_face'),
    path('api/face-login/', views.api_face_login, name='api_face_login'),
    path('api_login_with_password/', views.api_login_with_password, name='api_login_with_password'),

    path('api/face_logout/', views.api_face_logout, name='api_face_logout'),

    # ..............................................................
    # -------------------- Admin Dashboard URLs --------------------
    # ..............................................................

    path('adminDashboard/', views_admin.admin_dashboard, name='admin_dashboard'),  
    path('staff/search/', views_admin.admin_staff_search, name='admin_staff_search'),
    path("save-meeting/", views_admin.save_meeting, name="save_meeting"),

    path('adminstaffManagement/', views_admin.admin_staff_management, name='admin_staff_management'),

    path('AddNewstaff/', views_admin.add_new_staff, name='add_new_staff'), 
    path("staff/update/<str:staff_id>/", views_admin.update_staff, name="update_staff"),
    path("staff/delete/<str:staff_id>/", views_admin.delete_staff, name="delete_staff"),

    path('adminAttendanceManagement/', views_admin.admin_attendance_management, name='admin_attendance_management'),
    path('save-attendanceTime/', views_admin.save_attendanceTime_to_staff, name='save_attendanceTime'),
    
    path('adminEmotionManagement/', views_admin.admin_emotion_management, name='admin_emotion_management'),
    path('ajax/submit-feedback/', views_admin.ajax_submit_feedback, name='ajax_submit_feedback'),
    path('ajax/submit-issue/', views_admin.submit_issue, name='submit_issue'),

    path('admin/work_schedules/', views_admin.admin_work_schedule_list, name='admin_work_schedule_list'),
    
    # --- API ENDPOINTS --
    # GET: Get all events (for calendar refresh)
    path('admin/work_schedules/api/events/', views_admin.work_schedules_json, name='work_schedules_json'), 
    # POST: Create a new schedule
    path('admin/work_schedules/api/create/', views_admin.work_schedule_create, name='work_schedule_create'),  
    # POST: Update an existing schedule (pk is the schedule_id)
    path('admin/work_schedules/api/update/<int:pk>/', views_admin.work_schedule_update, name='work_schedule_update'),    
    # POST: Delete a schedule (pk is the schedule_id)
    path('admin/work_schedules/api/delete/<int:pk>/', views_admin.work_schedule_delete, name='work_schedule_delete'),
    
    # ..............................................................
    # -------------------- Staff Dashboard URLs --------------------
    # ..............................................................

    path('staffDashboard/', views_staff.staff_dashboard, name='staff_dashboard'),
    path('staffProfile/', views_staff.staff_profile, name='staff_profile'),
    path('staffAttendance/', views_staff.staff_attendance, name='staff_attendance'),
    path('staffWorkSchedule/', views_staff.staff_WorkSchedule, name='staff_work_schedule'),
    path('update-staff-response/', views_staff.update_staff_response, name='update_staff_response'),
    path('staffEmotion/', views_staff.staff_emotion, name='staff_emotion'),
    path('save-reply/', views_staff.save_admin_reply, name='save_admin_reply'),
    path('staff/record-emotion/', views_staff.record_emotion, name='record_emotion'),
    # Backwards-compatible alias: accept POSTs sent to /accounts/record-emotion/
    path('record-emotion/', views_staff.record_emotion, name='record_emotion_alias'),
]