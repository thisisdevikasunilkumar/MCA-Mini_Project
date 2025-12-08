from django.urls import path
from . import views

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

    path('adminDashboard/', views.admin_dashboard, name='admin_dashboard'),  
    path('staff/search/', views.admin_staff_search, name='admin_staff_search'),
    path("save-meeting/", views.save_meeting, name="save_meeting"),

    path('adminstaffManagement/', views.admin_staff_management, name='admin_staff_management'),

    path('AddNewstaff/', views.add_new_staff, name='add_new_staff'), 
    path("staff/update/<str:staff_id>/", views.update_staff, name="update_staff"),
    path("staff/delete/<str:staff_id>/", views.delete_staff, name="delete_staff"),

    path('adminAttendanceManagement/', views.admin_attendance_management, name='admin_attendance_management'),
    path('save-attendanceTime/', views.save_attendanceTime_to_staff, name='save_attendanceTime'),
    
    path('adminEmotionManagement/', views.admin_emotion_management, name='admin_emotion_management'),


path('admin/work_schedules/', views.admin_work_schedule_list, name='admin_work_schedule_list'),
    
    # --- API ENDPOINTS ---
    
    # GET: Get all events (for calendar refresh)
    path('admin/work_schedules/api/events/', views.work_schedules_json, name='work_schedules_json'),
    
    # POST: Create a new schedule
    path('admin/work_schedules/api/create/', views.work_schedule_create, name='work_schedule_create'),
    
    # POST: Update an existing schedule (pk is the schedule_id)
    path('admin/work_schedules/api/update/<int:pk>/', views.work_schedule_update, name='work_schedule_update'),
    
    # POST: Delete a schedule (pk is the schedule_id)
    path('admin/work_schedules/api/delete/<int:pk>/', views.work_schedule_delete, name='work_schedule_delete'),
    
    # ..............................................................
    # -------------------- Staff Dashboard URLs --------------------
    # ..............................................................

    path('staffDashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('staffProfile/', views.staff_profile, name='staff_profile'),
    path('staffAttendance/', views.staff_attendance, name='staff_attendance'),

    path('staffEmotion/', views.staff_emotion, name='staff_emotion'),
]