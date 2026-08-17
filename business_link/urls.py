from django.contrib import admin
from django.urls import path, include
# ۱. ایمپورت RedirectView
from django.views.generic import RedirectView

urlpatterns = [
    # هدایت مسیر ریشه به صفحه لاگین
    path('', RedirectView.as_view(pattern_name='login', permanent=False)),

    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),  # ایجاد مسیرهای ورود و خروج

    # سایر مسیرهای پروژه یا core/urls.py
    path('', include('core.urls')),
]
