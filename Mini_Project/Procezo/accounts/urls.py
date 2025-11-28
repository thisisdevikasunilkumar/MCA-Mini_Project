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

]