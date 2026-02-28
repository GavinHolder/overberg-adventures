from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.index, name='index'),
    path('tours/', views.tours_list, name='tours_list'),
    path('tours/create/', views.tour_create, name='tour_create'),
    path('tours/<int:pk>/', views.tour_detail, name='tour_detail'),
    path('tours/<int:pk>/edit/', views.tour_edit, name='tour_edit'),
    path('tours/<int:pk>/delete/', views.tour_delete, name='tour_delete'),
    path('tours/<int:pk>/qr/', views.tour_qr, name='tour_qr'),
    path('activities/', views.activities_list, name='activities_list'),
    path('guests/', views.guests_list, name='guests_list'),
    path('guides/', views.guides_list, name='guides_list'),
]
