from django.urls import path
from . import views

app_name = 'bookings'
urlpatterns = [
    path('itinerary/', views.itinerary_home, name='itinerary_home'),
    path('itinerary/<int:booking_id>/', views.itinerary_detail, name='itinerary_detail'),
    path('itinerary/<int:booking_id>/rsvp/', views.rsvp_action, name='rsvp_action'),
    path('join/', views.join_lookup, name='join_lookup'),
    path('join/<str:tour_code>/', views.join_confirm, name='join_confirm'),
]
