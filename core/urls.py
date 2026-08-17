from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.assistant_dashboard, name='dashboard'),

    # members
    path('members/', views.MemberListView.as_view(), name='member_list'),
    path('members/add/', views.MemberCreateView.as_view(), name='add_member'),
    path('members/<int:pk>/', views.MemberDetailView.as_view(), name='member_detail'),
    path('members/<int:pk>/edit/', views.MemberUpdateView.as_view(), name='edit_member'),

    # events
    path('events/', views.EventListView.as_view(), name='event_list'),
    path('events/add/', views.EventCreateView.as_view(), name='add_event'),
    path('events/<int:pk>/', views.EventDetailView.as_view(), name='event_detail'),
    path('events/<int:pk>/edit/', views.EventUpdateView.as_view(), name='edit_event'),
    path('events/<int:pk>/start/', views.EventStartView.as_view(), name='start_event'),
    path('events/<int:pk>/complete/', views.EventCompleteView.as_view(), name='complete_event'),
    path('events/<int:pk>/checkin/', views.EventCheckInView.as_view(), name='event_checkin'),
    path('events/<int:pk>/guest-lookup/', views.EventGuestLookupView.as_view(), name='guest_lookup'),
    path('guests/<int:pk>/status/', views.EventGuestStatusUpdateView.as_view(), name='update_guest_status'),
    path('events/<int:pk>/send-invites/', views.EventSendInvitesView.as_view(), name='send_invites'),

    # gallery
    path('gallery/upload/', views.upload_latest_event_gallery, name='upload_latest_gallery'),

    # sms
    path('settings/sms/', views.SmsSettingsView.as_view(), name='sms_settings'),

    # poster
    path('poster/<uuid:uuid>/', views.EventPosterView.as_view(), name='event_poster'),
]
