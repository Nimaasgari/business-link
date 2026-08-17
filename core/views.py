from collections import defaultdict
from datetime import datetime, timedelta

import jdatetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q, Case, When, Value, IntegerField
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView, UpdateView, View

from .forms import EventForm, EventGalleryUploadForm, MemberForm, SmsSettingsForm
from .models import Event, EventGallery, EventGuest, JobCategory, Member, SmsSettings
from .sms_service import build_public_url, send_sms


@login_required(login_url="/admin/login/")
def assistant_dashboard(request):
    today = timezone.localdate()

    latest_completed_event = Event.objects.filter(
        Q(status=Event.STATUS_COMPLETED) | Q(event_date__lt=today)
    ).order_by("-event_date", "-event_time").first()

    latest_event_gallery = EventGallery.objects.none()
    if latest_completed_event:
        latest_event_gallery = EventGallery.objects.filter(
            city=latest_completed_event.city,
            event_date=latest_completed_event.event_date,
            is_active=True,
        ).order_by("-created_at")

    context = {
        "members_count": Member.objects.count(),
        "events_count": Event.objects.count(),
        "latest_completed_event": latest_completed_event,
        "latest_event_gallery": latest_event_gallery[:12],
        "gallery_form": EventGalleryUploadForm(),
    }
    return render(request, "core/dashboard.html", context)


class MemberListView(LoginRequiredMixin, ListView):
    login_url = "/admin/login/"
    model = Member
    template_name = "core/member_list.html"
    context_object_name = "members"
    paginate_by = 20

    def get_queryset(self):
        queryset = (
            Member.objects
            .select_related("job_category")
            .all()
        )

        search_query = self.request.GET.get("search", "").strip()
        category_id = self.request.GET.get("category", "").strip()
        city = self.request.GET.get("city", "").strip()

        if search_query:
            queryset = queryset.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(phone_number__icontains=search_query) |
                Q(city__icontains=search_query) |
                Q(job_category__name__icontains=search_query)
            )

        if city:
            queryset = queryset.filter(city__icontains=city)

        if category_id:
            queryset = queryset.filter(job_category_id=category_id)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["categories"] = JobCategory.objects.all()
        context["search_query"] = self.request.GET.get("search", "").strip()
        context["current_city"] = self.request.GET.get("city", "").strip()
        context["current_category_id"] = self.request.GET.get("category", "").strip()

        return context


class MemberCreateView(LoginRequiredMixin, CreateView):
    login_url = "/admin/login/"
    model = Member
    form_class = MemberForm
    template_name = "core/add_member.html"
    success_url = reverse_lazy("member_list")

    def form_valid(self, form):
        job_name = (form.cleaned_data.get("job_name") or "").strip()
        if job_name:
            job_category, _ = JobCategory.objects.get_or_create(name=job_name)
            form.instance.job_category = job_category

        messages.success(self.request, "عضو جدید با موفقیت ثبت شد.")
        return super().form_valid(form)


class MemberDetailView(LoginRequiredMixin, DetailView):
    login_url = "/admin/login/"
    model = Member
    template_name = "core/member_detail.html"
    context_object_name = "member"


class MemberUpdateView(LoginRequiredMixin, UpdateView):
    login_url = "/admin/login/"
    model = Member
    form_class = MemberForm
    template_name = "core/member_edit.html"

    def get_success_url(self):
        return reverse_lazy("member_detail", kwargs={"pk": self.object.pk})

    def get_initial(self):
        initial = super().get_initial()
        initial["job_name"] = ""
        return initial

    def form_valid(self, form):
        job_name = (form.cleaned_data.get("job_name") or "").strip()
        if job_name:
            job_category, _ = JobCategory.objects.get_or_create(name=job_name)
            form.instance.job_category = job_category

        messages.success(self.request, "اطلاعات عضو با موفقیت بروزرسانی شد.")
        return super().form_valid(form)


class EventListView(LoginRequiredMixin, ListView):
    login_url = "/admin/login/"
    model = Event
    template_name = "core/event_list.html"
    context_object_name = "events"
    paginate_by = 12

    def get_queryset(self):
        return (
            Event.objects
            .filter(
                Q(status=Event.STATUS_PENDING) |
                Q(status=Event.STATUS_ACTIVE)
            )
            .prefetch_related("guests")
            .annotate(guests_total=Count("guests", distinct=True))
            .order_by(
                Case(
                    When(status=Event.STATUS_ACTIVE, then=Value(0)),
                    When(status=Event.STATUS_PENDING, then=Value(1)),
                    default=Value(2),
                    output_field=IntegerField(),
                ),
                "-event_date",
                "-event_time",
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()

        for event in context.get("events", []):
            event.upcoming_hint = ""

            if event.status != Event.STATUS_PENDING:
                continue

            event_start_at = get_event_start_at(event)
            if not event_start_at:
                continue

            delta = event_start_at - now
            if delta.total_seconds() <= 0:
                continue

            if delta <= timedelta(hours=24):
                event.upcoming_hint = "این مراسم کمتر از 24 ساعت دیگر برگزار می‌شود."
            elif delta <= timedelta(hours=48):
                hours_left = int(delta.total_seconds() // 3600)
                event.upcoming_hint = f"این مراسم حدود {hours_left} ساعت دیگر برگزار می‌شود."

        completed_events = (
            Event.objects
            .filter(status=Event.STATUS_COMPLETED)
            .prefetch_related("guests")
            .annotate(guests_total=Count("guests", distinct=True))
            .order_by("city", "-event_date", "-event_time")
        )

        city_groups = defaultdict(list)
        for event in completed_events:
            city_name = event.city or "بدون شهر"
            city_groups[city_name].append(event)

        context["completed_events_by_city"] = dict(city_groups)
        return context


class EventCreateView(LoginRequiredMixin, CreateView):
    login_url = "/admin/login/"
    model = Event
    form_class = EventForm
    template_name = "core/event_form.html"
    success_url = reverse_lazy("event_list")

    def form_valid(self, form):
        form.instance.status = Event.STATUS_PENDING
        response = super().form_valid(form)
        invited_members = form.cleaned_data.get("invited_members")
        sync_event_guests(self.object, invited_members)
        messages.success(self.request, "مهمانی با موفقیت ثبت شد.")
        return response

class EventUpdateView(LoginRequiredMixin, UpdateView):
    login_url = "/admin/login/"
    model = Event
    form_class = EventForm
    template_name = "core/event_form.html"

    def get_success_url(self):
        return reverse_lazy("event_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        response = super().form_valid(form)
        invited_members = form.cleaned_data.get("invited_members")
        sync_event_guests(self.object, invited_members)
        messages.success(self.request, "اطلاعات مهمانی با موفقیت بروزرسانی شد.")
        return response


class EventDetailView(LoginRequiredMixin, DetailView):
    login_url = "/admin/login/"
    model = Event
    template_name = "core/event_detail.html"
    context_object_name = "event"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["guests"] = self.object.guests.select_related(
            "member",
            "member__job_category",
        ).order_by("member__first_name", "member__last_name")
        context["elapsed_seconds"] = get_elapsed_seconds(self.object)
        return context


@login_required(login_url="/admin/login/")
def upload_latest_event_gallery(request):
    if request.method != "POST":
        return redirect("dashboard")

    today = timezone.localdate()

    latest_completed_event = Event.objects.filter(
        Q(status=Event.STATUS_COMPLETED) | Q(event_date__lt=today)
    ).order_by("-event_date", "-event_time").first()

    if not latest_completed_event:
        messages.error(request, "هیچ رویداد برگزارشده‌ای برای بارگذاری عکس پیدا نشد.")
        return redirect("dashboard")

    form = EventGalleryUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, "بارگذاری عکس انجام نشد. فایل‌ها را دوباره بررسی کن.")
        return redirect("dashboard")

    images = form.cleaned_data["images"]
    created_count = 0

    for image in images:
        EventGallery.objects.create(
            title=latest_completed_event.name,
            image=image,
            city=latest_completed_event.city,
            event_date=latest_completed_event.event_date,
            is_active=True,
        )
        created_count += 1

    messages.success(request, f"{created_count} عکس با موفقیت برای آخرین رویداد ثبت شد.")
    return redirect("dashboard")


def sync_event_guests(event, invited_members):
    invited_members = invited_members or Member.objects.none()
    selected_member_ids = set(invited_members.values_list("id", flat=True))
    existing_guests = {guest.member_id: guest for guest in event.guests.all()}

    for member in invited_members:
        if member.id not in existing_guests:
            EventGuest.objects.create(
                event=event,
                member=member,
                status=EventGuest.Status.DRAFT,
            )

    removable_ids = set(existing_guests.keys()) - selected_member_ids
    if removable_ids:
        event.guests.filter(member_id__in=removable_ids).delete()


class EventGuestStatusUpdateView(View):
    allowed_statuses = {
        EventGuest.Status.DRAFT,
        EventGuest.Status.INVITED,
        EventGuest.Status.ATTENDED,
        EventGuest.Status.ABSENT,
    }

    def post(self, request, pk):
        guest = get_object_or_404(EventGuest, pk=pk)
        status = request.POST.get("status")

        if status not in self.allowed_statuses:
            messages.error(request, "وضعیت انتخاب‌شده معتبر نیست.")
            return redirect("event_detail", pk=guest.event_id)

        guest.status = status

        if status == EventGuest.Status.ATTENDED:
            guest.is_present = True
            if not guest.check_in_time:
                guest.check_in_time = timezone.now()
        elif status == EventGuest.Status.ABSENT:
            guest.is_present = False
        elif status in {EventGuest.Status.DRAFT, EventGuest.Status.INVITED}:
            guest.is_present = False
            guest.check_in_time = None

        guest.save()
        messages.success(request, "وضعیت مهمان بروزرسانی شد.")
        return redirect("event_detail", pk=guest.event_id)


class EventSendInvitesView(LoginRequiredMixin, View):
    login_url = "/admin/login/"

    def post(self, request, pk):
        event = get_object_or_404(Event, pk=pk)

        if event.status != Event.STATUS_PENDING:
            messages.error(request, "فقط مهمانی‌های در انتظار را می‌توان دعوت کرد.")
            return redirect("event_detail", pk=event.pk)

        guests = event.guests.select_related("member")
        if not guests.exists():
            messages.error(request, "برای این مهمانی هنوز مهمانی انتخاب نشده است.")
            return redirect("event_detail", pk=event.pk)

        sms_settings = SmsSettings.get_solo()
        invitation_text = (event.invitation_text or "").strip()
        if not invitation_text:
            invitation_text = sms_settings.invitation_template
            event.invitation_text = invitation_text
            event.save(update_fields=["invitation_text"])

        sent_count = 0
        failed_count = 0
        debug_failures = []
        debug_mode = None
        now = timezone.now()
        for guest in guests:
            sms_text = render_sms_text(invitation_text, event, guest, request=request)
            ok, details = send_sms(guest.member.phone_number, sms_text)
            if debug_mode is None:
                debug_mode = (details or {}).get("mode")
            guest.status = EventGuest.Status.INVITED
            guest.invite_sent_at = now
            guest.save(update_fields=["status", "invite_sent_at", "updated_at"])
            if ok:
                sent_count += 1
            else:
                failed_count += 1
                reason = (details or {}).get("reason") or (details or {}).get("response") or (details or {}).get("error")
                debug_failures.append(f"{guest.member.phone_number}: {reason}")

        if failed_count:
            messages.warning(request, f"دعوت‌نامه برای {sent_count} نفر ارسال شد و {failed_count} ارسال ناموفق بود.")
            if debug_failures:
                messages.warning(request, "دیباگ ارسال: " + " | ".join(debug_failures[:3]))
        else:
            messages.success(request, f"دعوت‌نامه برای {sent_count} نفر با موفقیت ارسال شد.")
        if debug_mode == "mock":
            messages.info(request, "ارسال در حالت تست (mock) انجام شده است؛ برای ارسال واقعی `SMS_PROVIDER=smsir` را تنظیم کنید.")
        return redirect("event_detail", pk=event.pk)


class EventStartView(LoginRequiredMixin, View):
    login_url = "/admin/login/"

    def post(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        if event.status == Event.STATUS_COMPLETED:
            messages.error(request, "این مهمانی قبلاً پایان یافته است.")
            return redirect("event_detail", pk=event.pk)
        event.mark_as_active()
        messages.success(request, "مهمانی شروع شد. حالا می‌توانید حضور مهمان‌ها را ثبت کنید.")
        return redirect("event_detail", pk=event.pk)


class EventCheckInView(LoginRequiredMixin, View):
    login_url = "/admin/login/"

    def post(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        if event.status != Event.STATUS_ACTIVE:
            messages.error(request, "برای ثبت حضور، مهمانی باید در حال برگزاری باشد.")
            return redirect("event_detail", pk=event.pk)

        query = (request.POST.get("guest_query") or "").strip()
        if not query:
            messages.error(request, "نام یا شماره تماس مهمان را وارد کنید.")
            return redirect("event_detail", pk=event.pk)

        guest = event.guests.select_related("member").filter(
            Q(member__phone_number__icontains=query)
            | Q(member__first_name__icontains=query)
            | Q(member__last_name__icontains=query)
        ).first()

        if not guest:
            messages.error(request, "مهمان پیدا نشد یا در این مهمانی ثبت نشده است.")
            return redirect("event_detail", pk=event.pk)

        guest.mark_present()
        messages.success(request, f"حضور {guest.member.full_name} ثبت شد.")
        return redirect("event_detail", pk=event.pk)


class EventGuestLookupView(LoginRequiredMixin, View):
    login_url = "/admin/login/"

    def get(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        if event.status != Event.STATUS_ACTIVE:
            return JsonResponse({"results": []})

        query = (request.GET.get("q") or "").strip()
        if len(query) < 2:
            return JsonResponse({"results": []})

        guests = (
            event.guests.select_related("member", "member__job_category")
            .filter(
                Q(member__phone_number__icontains=query)
                | Q(member__first_name__icontains=query)
                | Q(member__last_name__icontains=query)
            )
            .order_by("member__first_name", "member__last_name")[:6]
        )

        data = [
            {
                "id": guest.id,
                "full_name": guest.member.full_name,
                "phone_number": guest.member.phone_number,
                "job": guest.member.job_category.name if guest.member.job_category else "سایر",
                "is_present": guest.is_present,
            }
            for guest in guests
        ]
        return JsonResponse({"results": data})


class EventCompleteView(LoginRequiredMixin, View):
    login_url = "/admin/login/"

    def post(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        if event.status == Event.STATUS_COMPLETED:
            messages.info(request, "این مهمانی قبلاً پایان یافته است.")
            return redirect("event_detail", pk=event.pk)

        guests = event.guests.select_related("member")

        now = timezone.now()
        sms_settings = SmsSettings.get_solo()
        thank_you_text = (event.thank_you_text or "").strip() or sms_settings.thank_you_template
        missed_you_text = (event.missed_you_text or "").strip() or sms_settings.missed_you_template
        event.thank_you_text = thank_you_text
        event.missed_you_text = missed_you_text
        event.save(update_fields=["thank_you_text", "missed_you_text"])

        attended = 0
        absent = 0
        failed_count = 0
        for guest in guests:
            if guest.is_present or guest.status == EventGuest.Status.ATTENDED:
                guest.status = EventGuest.Status.ATTENDED
                guest.thank_you_sent_at = now
                guest.save(update_fields=["status", "thank_you_sent_at", "updated_at"])
                sms_text = render_sms_text(thank_you_text, event, guest, request=request)
                ok, _ = send_sms(guest.member.phone_number, sms_text)
                if not ok:
                    failed_count += 1
                attended += 1
            else:
                guest.mark_absent()
                guest.missed_you_sent_at = now
                guest.save(update_fields=["missed_you_sent_at", "updated_at"])
                sms_text = render_sms_text(missed_you_text, event, guest, request=request)
                ok, _ = send_sms(guest.member.phone_number, sms_text)
                if not ok:
                    failed_count += 1
                absent += 1

        event.mark_as_completed()
        messages.success(
            request,
            f"مهمانی پایان یافت. پیام تشکر برای {attended} نفر و پیام عدم حضور برای {absent} نفر همین حالا ارسال شد.",
        )
        if failed_count:
            messages.warning(request, f"در ارسال پیامک {failed_count} مورد خطا رخ داد؛ تنظیمات پنل پیامک را بررسی کنید.")
        return redirect("event_list")


class SmsSettingsView(LoginRequiredMixin, UpdateView):
    login_url = "/admin/login/"
    form_class = SmsSettingsForm
    template_name = "core/sms_settings.html"
    success_url = reverse_lazy("sms_settings")

    def get_object(self, queryset=None):
        return SmsSettings.get_solo()

    def form_valid(self, form):
        messages.success(self.request, "تنظیمات پنل پیامک با موفقیت ذخیره شد.")
        return super().form_valid(form)


class EventPosterView(DetailView):
    model = EventGuest
    template_name = "core/event_poster.html"
    context_object_name = "guest"
    slug_field = "unique_link"
    slug_url_kwarg = "uuid"


def get_elapsed_seconds(event):
    if event.status != Event.STATUS_ACTIVE or not event.started_at:
        return 0
    delta = timezone.now() - event.started_at
    return max(int(delta.total_seconds()), 0)


def get_event_start_at(event):
    if not event.event_date or not event.event_time:
        return None
    naive_start = datetime.combine(event.event_date, event.event_time)
    return timezone.make_aware(naive_start, timezone.get_current_timezone())


def render_sms_text(template, event, guest, request=None):
    member = guest.member
    poster_relative_url = guest.get_poster_url()
    poster_url = request.build_absolute_uri(poster_relative_url) if request else build_public_url(poster_relative_url)
    event_date_jalali = ""
    if event.event_date:
        event_date_jalali = jdatetime.date.fromgregorian(date=event.event_date).strftime("%Y/%m/%d")

    event_time_text = ""
    if event.event_time:
        event_time_text = event.event_time.strftime("%H:%M")

    values = {
        "full_name": member.full_name,
        "first_name": member.first_name,
        "last_name": member.last_name,
        "event_name": event.name,
        "city": event.city,
        "venue_name": event.venue_name,
        "event_date": event_date_jalali,
        "event_time": event_time_text,
        "poster_url": poster_url,
        "phone_number": member.phone_number,
    }
    try:
        return template.format(**values)
    except (KeyError, ValueError):
        return template
