from django import forms
from jalali_date.fields import JalaliDateField
from jalali_date.widgets import AdminJalaliDateWidget

from .models import Event, Member, SmsSettings


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_file_clean(file, initial) for file in data]
        if data:
            return [single_file_clean(data, initial)]
        return []


class MemberForm(forms.ModelForm):
    job_name = forms.CharField(
        required=False,
        label="حوزه فعالیت جدید",
        widget=forms.TextInput(attrs={"class": "form-control"})
    )

    class Meta:
        model = Member
        fields = ["first_name", "last_name", "phone_number", "job_category","city"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "phone_number": forms.TextInput(attrs={"class": "form-control", "dir": "ltr"}),
            "job_category": forms.Select(attrs={"class": "form-select"}),
            "city": forms.TextInput(attrs={"class":"form-control","placeholder":"نام شهر "}),
        }


class EventForm(forms.ModelForm):
    invited_members = forms.ModelMultipleChoiceField(
        queryset=Member.objects.select_related("job_category").order_by("first_name", "last_name"),
        required=False,
        label="افراد دعوت‌شده",
        widget=forms.SelectMultiple(
            attrs={
                "class": "form-select d-none",
                "size": 12,
                "id": "id_invited_members_native",
            }
        ),
    )

    event_date = JalaliDateField(
        label="تاریخ برگزاری",
        widget=AdminJalaliDateWidget(
            attrs={
                "class": "form-control",
                "placeholder": "مثال: 1405/05/01",
                "autocomplete": "off",
            }
        ),
    )

    event_time = forms.TimeField(
        label="ساعت شروع",
        input_formats=["%H:%M", "%H:%M:%S"],
        widget=forms.TimeInput(
            attrs={
                "class": "form-control",
                "type": "time",
                "step": 300,
            },
            format="%H:%M",
        ),
    )

    class Meta:
        model = Event
        fields = [
            "name",
            "city",
            "venue_name",
            "event_date",
            "event_time",
            "status",
            "invitation_text",
            "thank_you_text",
            "missed_you_text",
            "invited_members",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "venue_name": forms.TextInput(attrs={"class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "invitation_text": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "thank_you_text": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "missed_you_text": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        if args and hasattr(args[0], "copy"):
            mutable_data = args[0].copy()
            event_time_key = self.add_prefix("event_time") if hasattr(self, "prefix") and self.prefix else "event_time"
            event_time_value = mutable_data.get(event_time_key)
            if event_time_value is not None:
                mutable_data[event_time_key] = self._normalize_digits(event_time_value)
            args = (mutable_data, *args[1:])

        super().__init__(*args, **kwargs)

        grouped_choices = []
        categories = list(Member.objects.select_related("job_category").order_by("job_category__name", "first_name", "last_name"))
        by_job = {}
        for member in categories:
            job_name = member.job_category.name if member.job_category else "سایر"
            by_job.setdefault(job_name, []).append((member.pk, f"{member.full_name} - {member.phone_number}"))
        for job_name, members in by_job.items():
            grouped_choices.append((job_name, members))
        self.fields["invited_members"].choices = grouped_choices

        self.fields["status"].required = False
        self.fields["status"].widget = forms.HiddenInput()
        if not self.initial.get("status"):
            self.initial["status"] = Event.STATUS_PENDING

        if self.instance and self.instance.pk:
            self.fields["invited_members"].initial = self.instance.guests.values_list("member_id", flat=True)

        if self.instance and self.instance.pk and self.instance.event_time:
            self.initial["event_time"] = self.instance.event_time.strftime("%H:%M")

    @staticmethod
    def _normalize_digits(value):
        if not isinstance(value, str):
            return value
        translation = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
        return value.translate(translation)

class EventGalleryUploadForm(forms.Form):
    images = MultipleFileField(
        label="تصاویر گالری",
        required=True,
        widget=MultipleFileInput(
            attrs={
                "class": "form-control",
                "accept": "image/*",
                "multiple": True,
            }
        ),
    )


class SmsSettingsForm(forms.ModelForm):
    class Meta:
        model = SmsSettings
        fields = ["sender_name", "invitation_template", "thank_you_template", "missed_you_template"]
        widgets = {
            "sender_name": forms.TextInput(attrs={"class": "form-control"}),
            "invitation_template": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
            "thank_you_template": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "missed_you_template": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }
