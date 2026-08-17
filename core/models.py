import uuid
from django.db import models
from django.core.validators import RegexValidator
from django.urls import reverse
from django.utils import timezone


class JobCategory(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="حوزه فعالیت")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "حوزه کاری"
        verbose_name_plural = "حوزه‌های کاری"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Member(models.Model):
    first_name = models.CharField(max_length=50, verbose_name="نام")
    last_name = models.CharField(max_length=50, verbose_name="نام خانوادگی")
    city = models.CharField(max_length=50,verbose_name="شهر",null=True,blank=True)
    phone_regex = RegexValidator(
        regex=r"^09\d{9}$",
        message="شماره تماس باید با 09 شروع شود و 11 رقم باشد."
    )
    phone_number = models.CharField(
        max_length=11,
        unique=True,
        validators=[phone_regex],
        verbose_name="شماره تماس"
    )

    job_category = models.ForeignKey(
        JobCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
        verbose_name="حوزه فعالیت"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "عضو"
        verbose_name_plural = "اعضا"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Event(models.Model):
    STATUS_PENDING = "pending"
    STATUS_ACTIVE = "active"
    STATUS_COMPLETED = "completed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "در انتظار برگزاری"),
        (STATUS_ACTIVE, "در حال برگزاری"),
        (STATUS_COMPLETED, "پایان یافته"),
    ]

    name = models.CharField(max_length=200, verbose_name="نام مهمانی")
    city = models.CharField(max_length=100, db_index=True, verbose_name="شهر")
    venue_name = models.CharField(max_length=200, verbose_name="نام مکان برگزاری")
    event_date = models.DateField(db_index=True, verbose_name="تاریخ برگزاری")
    event_time = models.TimeField(verbose_name="ساعت شروع")

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
        verbose_name="وضعیت مهمانی"
    )

    invitation_text = models.TextField(
        blank=True,
        default="",
        verbose_name="متن پیام دعوت"
    )
    thank_you_text = models.TextField(
        blank=True,
        default="",
        verbose_name="متن تشکر از حضور"
    )
    missed_you_text = models.TextField(
        blank=True,
        default="",
        verbose_name="متن عدم حضور"
    )

    started_at = models.DateTimeField(blank=True, null=True, verbose_name="زمان شروع واقعی")
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name="زمان پایان")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "مهمانی"
        verbose_name_plural = "مهمانی‌ها"
        ordering = ["-event_date", "-event_time"]

    def __str__(self):
        return f"{self.name} ({self.city})"

    @property
    def guest_count(self):
        return self.guests.count()

    @property
    def present_count(self):
        return self.guests.filter(status=EventGuest.Status.ATTENDED).count()

    @property
    def absent_count(self):
        return self.guests.filter(status=EventGuest.Status.ABSENT).count()

    def mark_as_active(self):
        self.status = self.STATUS_ACTIVE
        if not self.started_at:
            self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at"])

    def mark_as_completed(self):
        self.status = self.STATUS_COMPLETED
        if not self.completed_at:
            self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at"])

    @property
    def invited_count(self):
        return self.guests.filter(status=EventGuest.Status.INVITED).count()


class EventGuest(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "پیش‌نویس"
        INVITED = "invited", "دعوت شد"
        ATTENDED = "attended", "حضور داشت"
        ABSENT = "absent", "غایب بود"

    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE,
        related_name="guests",
        verbose_name="مهمانی"
    )
    member = models.ForeignKey(
        Member,
        on_delete=models.CASCADE,
        related_name="event_guests",
        verbose_name="عضو دعوت‌شده"
    )

    unique_link = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
        verbose_name="وضعیت دعوت"
    )

    is_present = models.BooleanField(default=False, db_index=True, verbose_name="حاضر بود؟")
    check_in_time = models.DateTimeField(blank=True, null=True, verbose_name="زمان ثبت حضور")

    invite_sent_at = models.DateTimeField(blank=True, null=True, verbose_name="زمان ارسال دعوت")
    thank_you_sent_at = models.DateTimeField(blank=True, null=True, verbose_name="زمان ارسال پیام تشکر")
    missed_you_sent_at = models.DateTimeField(blank=True, null=True, verbose_name="زمان ارسال پیام عدم حضور")

    note = models.TextField(blank=True, verbose_name="یادداشت داخلی")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "مهمان"
        verbose_name_plural = "مهمانان"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["event", "member"], name="unique_event_member")
        ]

    def __str__(self):
        return f"{self.member} → {self.event.name}"

    def get_poster_url(self):
        return reverse("event_poster", kwargs={"uuid": self.unique_link})

    def mark_present(self):
        updates = []

        if not self.is_present:
            self.is_present = True
            updates.append("is_present")

        if not self.check_in_time:
            self.check_in_time = timezone.now()
            updates.append("check_in_time")

        if self.status != self.Status.ATTENDED:
            self.status = self.Status.ATTENDED
            updates.append("status")

        if updates:
            self.save(update_fields=updates)

    def mark_absent(self):
        updates = []

        if self.is_present:
            self.is_present = False
            updates.append("is_present")

        if self.status != self.Status.ABSENT:
            self.status = self.Status.ABSENT
            updates.append("status")

        if updates:
            self.save(update_fields=updates)


class SmsSettings(models.Model):
    sender_name = models.CharField(max_length=100, default="BusinessLink", verbose_name="نام فرستنده")
    invitation_template = models.TextField(
        default=(
            "{full_name} عزیز، شما به مهمانی {event_name} دعوت شده‌اید.\n"
            "شهر: {city}\nمکان: {venue_name}\nتاریخ: {event_date}\nساعت: {event_time}\n"
            "لینک جزئیات: {poster_url}"
        ),
        verbose_name="قالب پیام دعوت",
    )
    thank_you_template = models.TextField(
        default="{full_name} عزیز، از حضور شما در {event_name} سپاسگزاریم.",
        verbose_name="قالب پیام تشکر",
    )
    missed_you_template = models.TextField(
        default="{full_name} عزیز، جای شما در {event_name} خالی بود. امیدواریم برنامه بعدی همراه ما باشید.",
        verbose_name="قالب پیام عدم حضور",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "تنظیمات پیامک"
        verbose_name_plural = "تنظیمات پیامک"

    def __str__(self):
        return "تنظیمات پیامک"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class EventGallery(models.Model):
    title = models.CharField(max_length=150, verbose_name="عنوان عکس/رویداد")
    image = models.ImageField(upload_to="event_gallery/", verbose_name="عکس")
    city = models.CharField(max_length=100, blank=True, verbose_name="شهر")
    event_date = models.DateField(blank=True, null=True, verbose_name="تاریخ رویداد")
    is_active = models.BooleanField(default=True, verbose_name="نمایش در صفحه اصلی")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "عکس گالری مهمانی"
        verbose_name_plural = "گالری مهمانی‌ها"
        ordering = ["-event_date", "-created_at"]

    def __str__(self):
        return self.title
