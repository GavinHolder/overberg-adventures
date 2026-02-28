from django.urls import path
from . import views

app_name = 'accounts'
urlpatterns = [
    path('login/', views.login_page, name='login'),
    path('signup/email/', views.email_signup, name='email_signup'),
    path('verify/', views.verify_otp, name='verify_otp'),
    path('setup/', views.profile_setup, name='profile_setup'),
    path('setup/<int:step>/', views.profile_setup_step, name='profile_setup_step'),
    path('dev-login/', views.dev_login, name='dev_login'),
    path('settings/toggle/', views.profile_settings_toggle, name='settings_toggle'),
    path('profile/', views.profile_view, name='profile'),
    path('logout/', views.logout_view, name='logout'),
]
