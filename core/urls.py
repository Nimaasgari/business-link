from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # صفحه اصلی عمومی
    path('', views.home_page, name='home'),

    # احراز هویت
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html', next_page='dashboard'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),

    # پنل دستیار
    path('dashboard/', views.assistant_dashboard, name='dashboard'),
    path('members/add/', views.add_member, name='add_member'),
    path('members/', views.member_list, name='member_list'),

    path('events/', views.event_list, name='event_list'),
    path('events/add/', views.add_event, name='add_event'),

    path('members/', views.MemberListView.as_view(), name='member_list'),
# urls.py

    # path('events/', views.events_list, name='events_list'),
    # path('events/<slug:slug>/', views.event_detail, name='event_detail'),
    # path('events/<slug:slug>/register/', views.event_register, name='event_register'),


]
