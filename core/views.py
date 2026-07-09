from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Member, JobCategory, Event
from .forms import MemberForm, EventForm


def home_page(request):
    """صفحه اصلی سایت - عمومی"""
    # واکشی ۶ رویداد آخر برای نمایش در صفحه اصلی (فرض بر این است که رویدادها بر اساس زمان مرتب می‌شوند)
    latest_events = Event.objects.all().order_by('-id')[:6]
    return render(request, 'core/home.html', {'events': latest_events})


@login_required(login_url='/admin/login/')
def assistant_dashboard(request):
    """پنل اصلی دستیار"""
    # محاسبه تعداد کل برای نمایش در داشبورد
    context = {
        'events_count': Event.objects.count(),
        'members_count': Member.objects.count(),
    }
    return render(request, 'core/dashboard.html', context)


@login_required(login_url='/admin/login/')
def add_member(request):
    """
    ثبت عضو جدید با مدیریت پویای حوزه فعالیت
    اگر شغل وارد شده وجود نداشته باشد، به طور خودکار ساخته می‌شود.
    """
    if request.method == 'POST':
        form = MemberForm(request.POST)
        if form.is_valid():
            # استخراج اطلاعات بدون ذخیره فوری در دیتابیس
            new_member = form.save(commit=False)
            job_name = form.cleaned_data.get('job_name').strip()

            # بررسی وجود شغل یا ایجاد آن (Core Logic)
            job_category, created = JobCategory.objects.get_or_create(name=job_name)

            # انتساب شغل به عضو و ذخیره نهایی
            new_member.job_category = job_category
            new_member.save()

            messages.success(request, f"عضو جدید ({new_member.first_name} {new_member.last_name}) با موفقیت ثبت شد.")
            return redirect('add_member')
        else:
            messages.error(request, "خطایی در فرم وجود دارد. لطفاً اطلاعات را بررسی کنید.")
    else:
        form = MemberForm()

    return render(request, 'core/add_member.html', {'form': form})


@login_required(login_url='login')
def member_list(request):
    # 'job' به 'job_category' تغییر یافت
    members = Member.objects.select_related('job_category').all().order_by('-created_at')

    context = {
        'members': members,
    }
    return render(request, 'core/member_list.html', context)


@login_required(login_url='login')
def event_list(request):
    # دریافت لیست رویدادها به ترتیب تاریخ برگزاری (نزولی)
    events = Event.objects.all().order_by('-date')  # اگر فیلد تاریخ شما نام دیگری دارد، اصلاح کنید

    context = {
        'events': events,
    }
    return render(request, 'core/event_list.html', context)


@login_required(login_url='login')
def add_event(request):
    if request.method == 'POST':
        form = EventForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'رویداد جدید با موفقیت ثبت شد.', extra_tags='success')
            return redirect('event_list')
    else:
        form = EventForm()

    context = {
        'form': form,
    }
    return render(request, 'core/add_event.html', context)


from django.shortcuts import render
from django.views.generic import ListView
from .models import Member, JobCategory
from .forms import MemberForm


# ====================== لیست اعضا ======================
class MemberListView(ListView):
    model = Member
    template_name = 'core/member_list.html'
    context_object_name = 'members'
    paginate_by = 20  # هر صفحه ۲۰ نفر

    def get_queryset(self):
        queryset = Member.objects.select_related('job_category').order_by('-created_at')

        # فیلتر بر اساس حوزه فعالیت
        category_id = self.request.GET.get('category')
        if category_id:
            queryset = queryset.filter(job_category_id=category_id)

        # جستجو بر اساس نام یا شماره تماس
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                first_name__icontains=search
            ) | queryset.filter(
                last_name__icontains=search
            ) | queryset.filter(
                phone_number__icontains=search
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = JobCategory.objects.all()
        context['current_category'] = self.request.GET.get('category', '')
        context['search_query'] = self.request.GET.get('search', '')
        return context




