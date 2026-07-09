from django import forms
from .models import Member, Event, JobCategory, EventGuest


class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        fields = ['first_name', 'last_name', 'phone_number', 'job_category']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'نام خانوادگی'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '09123456789'}),
            'job_category': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'first_name': 'نام',
            'last_name': 'نام خانوادگی',
            'phone_number': 'شماره تماس',
            'job_category': 'حوزه فعالیت',
        }


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['name', 'city', 'venue_name', 'event_date', 'event_time']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام مهمانی'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'تهران'
            }),
            'venue_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'نام مکان برگزاری'
            }),
            'event_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'event_time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
        }
        labels = {
            'name': 'نام مهمانی',
            'city': 'شهر',
            'venue_name': 'نام مکان برگزاری',
            'event_date': 'تاریخ برگزاری',
            'event_time': 'ساعت شروع',
        }
