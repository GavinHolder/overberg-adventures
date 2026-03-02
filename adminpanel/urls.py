from django.urls import path
from . import views

app_name = 'backend'

urlpatterns = [
    path('', views.overview, name='overview'),
    path('site-settings/', views.site_settings, name='site_settings'),
    path('users/', views.users_list, name='users_list'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/toggle-active/', views.user_toggle_active, name='user_toggle_active'),
    path('social-auth/', views.social_auth_settings, name='social_auth'),
    path('social-auth/<int:pk>/toggle/', views.social_auth_toggle, name='social_auth_toggle'),
    path('social-auth/<int:pk>/save/', views.social_auth_save, name='social_auth_save'),
]
