from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.views.generic import ListView, CreateView
from django.urls import reverse_lazy

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Member, JobCategory, Event, EventGallery
from .forms import MemberForm, EventForm, EventGalleryUploadForm

from django.contrib import messages
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from .models import Member, JobCategory
from .forms import MemberForm

# ====================== صفحه اصلی (عمومی) ======================
# ====================== صفحه اصلی (عمومی) ======================
def home_page(request):
    today = timezone.localdate()

    recent_events = Event.objects.all().order_by("-created_at")[:6]
    upcoming_events = Event.objects.filter(
        event_date__gte=today
    ).order_by("event_date", "event_time")[:6]

    past_events = Event.objects.filter(
        event_date__lt=today
    ).order_by("-event_date", "-event_time")[:6]

    latest_completed_event = Event.objects.filter(
        Q(status=Event.STATUS_COMPLETED) | Q(event_date__lt=today)
    ).order_by("-event_date", "-event_time").first()

    gallery_items = EventGallery.objects.filter(is_active=True)
    if latest_completed_event:
        gallery_items = gallery_items.filter(
            city=latest_completed_event.city,
            event_date=latest_completed_event.event_date,
        ).order_by("-created_at")
    else:
        gallery_items = gallery_items.none()

    context = {
        "recent_events": recent_events,
        "upcoming_events": upcoming_events,
        "past_events": past_events,
        "latest_completed_event": latest_completed_event,
        "gallery_items": gallery_items[:12],
    }
    return render(request, "core/home.html", context)

# ====================== داشبورد دستیار ======================
# ====================== داشبورد دستیار ======================
@login_required(login_url='/admin/login/')
def assistant_dashboard(request):
    today = timezone.localdate()

    latest_completed_event = Event.objects.filter(
        Q(status=Event.STATUS_COMPLETED) | Q(event_date__lt=today)
    ).order_by("-event_date", "-event_time").first()

    latest_event_gallery = EventGallery.objects.none()
    if latest_completed_event:
        latest_event_gallery = EventGallery.objects.filter(
            city=latest_completed_event.city,
            event_date=latest_completed_event.event_date
        ).order_by("-created_at")

    context = {
        'events_count': Event.objects.count(),
        'members_count': Member.objects.count(),
        'latest_completed_event': latest_completed_event,
        'latest_event_gallery': latest_event_gallery[:8],
        'gallery_form': EventGalleryUploadForm(),
    }
    return render(request, 'core/dashboard.html', context)


# ====================== لیست اعضا ======================


class MemberListView(ListView):
    model = Member
    template_name = 'core/member_list.html'
    context_object_name = 'members'
    paginate_by = 12  # برای موبایل/تبلت بهتر

    def get_queryset(self):
        queryset = Member.objects.select_related('job_category').order_by('-created_at')

        category_id = self.request.GET.get('category')
        if category_id:
            queryset = queryset.filter(job_category_id=category_id)

        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(phone_number__icontains=search)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category = self.request.GET.get('category', '')
        context['categories'] = JobCategory.objects.all()
        context['current_category'] = category
        context['search_query'] = self.request.GET.get('search', '')
        context['current_category_id'] = int(category) if str(category).isdigit() else None
        return context


class MemberCreateView(CreateView):
    model = Member
    form_class = MemberForm
    template_name = 'core/add_member.html'
    success_url = reverse_lazy('member_list')

    def form_valid(self, form):
        job_name = (form.cleaned_data.get('job_name') or '').strip()
        if job_name:
            job_category, _ = JobCategory.objects.get_or_create(name=job_name)
            form.instance.job_category = job_category

        messages.success(self.request, "عضو جدید با موفقیت ثبت شد.")
        return super().form_valid(form)


class MemberDetailView(DetailView):
    model = Member
    template_name = 'core/member_detail.html'
    context_object_name = 'member'


class MemberUpdateView(UpdateView):
    model = Member
    form_class = MemberForm
    template_name = 'core/member_edit.html'

    def get_success_url(self):
        return reverse_lazy('member_detail', kwargs={'pk': self.object.pk})

    def get_initial(self):
        initial = super().get_initial()
        # در حالت ویرایش job_name خالی باشد تا بی‌دلیل overwrite نکند
        initial['job_name'] = ''
        return initial

    def form_valid(self, form):
        job_name = (form.cleaned_data.get('job_name') or '').strip()
        if job_name:
            job_category, _ = JobCategory.objects.get_or_create(name=job_name)
            form.instance.job_category = job_category

        messages.success(self.request, "اطلاعات عضو با موفقیت بروزرسانی شد.")
        return super().form_valid(form)


# ====================== لیست مهمانی‌ها ======================
class EventListView(ListView):
    model = Event
    template_name = 'core/event_list.html'
    context_object_name = 'events'
    paginate_by = 12
    ordering = ['-event_date', '-event_time']


# ====================== ایجاد مهمانی جدید ======================
class EventCreateView(CreateView):
    model = Event
    form_class = EventForm
    template_name = 'core/event_form.html'
    success_url = reverse_lazy('event_list')

    def form_valid(self, form):
        if hasattr(form.instance, 'created_by'):
            form.instance.created_by = self.request.user
        messages.success(self.request, "مهمانی با موفقیت ثبت شد.")
        return super().form_valid(form)


# ====================== آپلود عکس‌های آخرین رویداد برگزارشده ======================
@login_required(login_url='/admin/login/')
def upload_latest_event_gallery(request):
    today = timezone.localdate()

    latest_completed_event = Event.objects.filter(
        Q(status=Event.STATUS_COMPLETED) | Q(event_date__lt=today)
    ).order_by("-event_date", "-event_time").first()

    if not latest_completed_event:
        messages.error(request, "هیچ رویداد برگزارشده‌ای برای بارگذاری عکس پیدا نشد.")
        return redirect("dashboard")

    if request.method != "POST":
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

    messages.success(request, f"{created_count} عکس برای آخرین رویداد با موفقیت بارگذاری شد.")
    return redirect("dashboard")
