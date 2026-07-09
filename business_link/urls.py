from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # متصل کردن مسیرهای اپلیکیشن core به روت پروژه
    path('', include('core.urls')),
]
