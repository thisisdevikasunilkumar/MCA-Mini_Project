from django import forms
from .models import Staff, Register, Attendance


class StaffRegisterForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = Staff
        fields = ['name', 'email', 'password', 'role', 'job_type', 'profile_image']


class StaffProfileForm(forms.ModelForm):
    class Meta:
        model = Register
        fields = [
            'name', 'email', 'dob', 'gender', 'country',
            'state', 'city', 'pin_code', 'profile_image'
        ]
        widgets = {
            'dob': forms.DateInput(attrs={'type': 'date'}),
            'gender': forms.RadioSelect(choices=[('male', 'Male'), ('female', 'Female')]),
        }