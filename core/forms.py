from django import forms
from .models import Member, Event, JobCategory, EventGuest


class MemberForm(forms.ModelForm):
    job_name = forms.CharField(
        required=False,
        label="حوزه فعالیت جدید",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'اگر حوزه در لیست نیست، اینجا وارد کنید'
        })
    )

    class Meta:
        model = Member
        fields = ['first_name', 'last_name', 'phone_number', 'job_category', 'job_name']
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

    def clean(self):
        cleaned_data = super().clean()
        job_category = cleaned_data.get('job_category')
        job_name = (cleaned_data.get('job_name') or '').strip()

        if not job_category and not job_name:
            raise forms.ValidationError("یا حوزه فعالیت را از لیست انتخاب کنید یا حوزه جدید وارد کنید.")

        return cleaned_data


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




from django import forms
from .models import Member, Event


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        single_file_clean = super().clean

        if not data:
            return []

        if isinstance(data, (list, tuple)):
            return [single_file_clean(item, initial) for item in data]

        return [single_file_clean(data, initial)]


class EventGalleryUploadForm(forms.Form):
    images = MultipleFileField(
        label="عکس‌های رویداد",
        widget=MultipleFileInput(attrs={"accept": "image/*", "multiple": True}),
    )


