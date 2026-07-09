import uuid
from django.db import models
from django.core.validators import RegexValidator
from django.urls import reverse


class JobCategory(models.Model):
    """
    مدل دسته‌بندی مشاغل: به صورت پویا اضافه می‌شود و افراد را گروه بندی می‌کند.
    """
    name = models.CharField(max_length=100, unique=True, verbose_name="حوزه فعالیت")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "حوزه کاری"
        verbose_name_plural = "حوزه‌های کاری"

    def __str__(self):
        return self.name


class Member(models.Model):
    """
    مدل اعضای بیزنس لینک
    """
    first_name = models.CharField(max_length=50, verbose_name="نام")
    last_name = models.CharField(max_length=50, verbose_name="نام خانوادگی")

    # اعتبارسنجی شماره تماس (فرمت ایران)
    phone_regex = RegexValidator(regex=r'^09\d{9}$', message="شماره تماس باید با 09 شروع شود و 11 رقم باشد.")
    phone_number = models.CharField(validators=[phone_regex], max_length=11, unique=True, verbose_name="شماره تماس")

    job_category = models.ForeignKey(JobCategory, on_delete=models.SET_NULL, null=True, related_name='members',
                                     verbose_name="حوزه فعالیت")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "عضو"
        verbose_name_plural = "اعضا"

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.job_category}"


class Event(models.Model):
    """
    مدل مهمانی / رویداد
    """
    STATUS_CHOICES = [
        ('pending', 'در انتظار برگزاری'),
        ('active', 'در حال برگزاری'),
        ('completed', 'پایان یافته'),
    ]

    name = models.CharField(max_length=200, verbose_name="نام مهمانی")
    city = models.CharField(max_length=100, verbose_name="شهر")
    venue_name = models.CharField(max_length=200, verbose_name="نام مکان برگزاری")
    event_date = models.DateField(verbose_name="تاریخ برگزاری")
    event_time = models.TimeField(verbose_name="ساعت شروع")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="وضعیت مهمانی")

    # متن پیام‌های سفارشی برای این رویداد
    invitation_text = models.TextField(verbose_name="متن پیام دعوت",
                                       help_text="از {name} برای قرار دادن نام شخص و از {link} برای لینک دعوت استفاده کنید.")
    thank_you_text = models.TextField(blank=True, null=True, verbose_name="متن تشکر از حضور")
    missed_you_text = models.TextField(blank=True, null=True, verbose_name="متن عدم حضور")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "مهمانی"
        verbose_name_plural = "مهمانی‌ها"
        ordering = ['-event_date', '-event_time']

    def __str__(self):
        return f"{self.name} ({self.city})"


class EventGuest(models.Model):
    """
    مدل مهمانان دعوت شده به یک رویداد خاص
    این مدل مشخص می‌کند چه کسی دعوت شده، آیا آمده است یا خیر و لینک اختصاصی او چیست.
    """
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='guests', verbose_name="مهمانی")
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='invitations',
                               verbose_name="عضو دعوت شده")

    # لینک اختصاصی و غیرقابل حدس (UUID) برای پوستر هر فرد
    unique_link = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    # وضعیت حضور
    is_present = models.BooleanField(default=False, verbose_name="حاضر بود؟")
    check_in_time = models.DateTimeField(blank=True, null=True, verbose_name="زمان ثبت حضور")

    class Meta:
        verbose_name = "مهمان"
        verbose_name_plural = "مهمانان"
        unique_together = ('event', 'member')  # یک نفر نمی‌تواند دو بار به یک مهمانی دعوت شود

    def __str__(self):
        return f"{self.member.first_name} {self.member.last_name} -> {self.event.name}"

    def get_poster_url(self):
        # این متد آدرس صفحه پوستر اختصاصی فرد را برمی‌گرداند
        return reverse('event_poster', kwargs={'uuid': self.unique_link})
