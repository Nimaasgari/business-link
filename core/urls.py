from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .views import upload_latest_event_gallery

urlpatterns = [
    # ==================== صفحه اصلی ====================
    path('', views.home_page, name='home'),

    # ==================== احراز هویت ====================
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html', next_page='dashboard'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),

    # ==================== پنل دستیار ====================
    path('dashboard/', views.assistant_dashboard, name='dashboard'),

    # ==================== مدیریت اعضا ====================
    path('members/', views.MemberListView.as_view(), name='member_list'),
    path('members/add/', views.MemberCreateView.as_view(), name='add_member'),

    # ==================== مدیریت مهمانی‌ها ====================
    path('events/', views.EventListView.as_view(), name='event_list'),
    path('events/add/', views.EventCreateView.as_view(), name='add_event'),

    path('members/', views.MemberListView.as_view(), name='member_list'),
    path('members/add/', views.MemberCreateView.as_view(), name='add_member'),
    path('members/<int:pk>/', views.MemberDetailView.as_view(), name='member_detail'),
    path('members/<int:pk>/edit/', views.MemberUpdateView.as_view(), name='member_edit'),

    path('dashboard/event-gallery/upload/', upload_latest_event_gallery, name='upload_latest_event_gallery'),
    path('dashboard/event-gallery/upload/', upload_latest_event_gallery, name='upload_latest_event_gallery')

]
