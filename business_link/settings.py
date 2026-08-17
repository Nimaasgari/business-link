import os
from pathlib import Path

# مسیر ریشه پروژه
BASE_DIR = Path(__file__).resolve().parent.parent

# تنظیمات امنیتی پایه
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-insecure-key")
DEBUG = True

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",")

# برنامه‌های نصب شده
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # برنامه اصلی پروژه (مدیریت اعضا، رویدادها و داشبورد)
    'core.apps.CoreConfig',

    # ابزارهای جانبی مورد نیاز پروژه
    'jalali_date',
]

# میدل‌ورها (میدل‌ور CORS حذف شد)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'business_link.urls'

# تنظیمات موتور تمپلیت جنگو
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # مسیر سراسری قالب‌ها در ریشه پروژه
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',  # اضافه شد برای دیباگ راحت‌تر در تمپلیت‌ها
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'business_link.wsgi.application'

# دیتابیس (SQLite برای توسعه محلی)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# تنظیمات زبان و منطقه زمانی ایران
LANGUAGE_CODE = 'fa-ir'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_TZ = True

# تنظیمات فایل‌های استاتیک (CSS, JS, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',  # اطمینان حاصل کن که پوشه static در ریشه پروژه ساخته شده است
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

# تنظیمات رسانه (فایل‌های آپلودی کاربران)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# تنظیمات احراز هویت و ریدایرکت‌ها
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

# تنظیمات سامانه پیامک و متغیرهای سراسری
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://127.0.0.1:8000")
SMS_PROVIDER = os.getenv("SMS_PROVIDER", "smsir")
SMSIR_API_KEY = os.getenv("SMSIR_API_KEY", "Y3H2lEclwslHuJuGcxy5OeZoUL6pkSA3qk9DMbQYuJLP94yF")
SMSIR_LINE_NUMBER = os.getenv("SMSIR_LINE_NUMBER", "30002108028154")
SMSIR_SEND_ENDPOINT = os.getenv("SMSIR_SEND_ENDPOINT", "https://api.sms.ir/v1/send/bulk")
