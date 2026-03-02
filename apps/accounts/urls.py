from django.urls import path, include
from . import views

app_name = 'accounts'
urlpatterns = [
    # Our custom auth views
    path('login/', views.login_page, name='login'),
    path('signup/email/', views.email_signup, name='email_signup'),
    path('verify/', views.verify_otp, name='verify_otp'),
    path('setup/', views.profile_setup, name='profile_setup'),
    path('setup/<int:step>/', views.profile_setup_step, name='profile_setup_step'),
    path('dev-login/', views.dev_login, name='dev_login'),
    path('settings/toggle/', views.profile_settings_toggle, name='settings_toggle'),
    path('profile/', views.profile_view, name='profile'),
    path('logout/', views.logout_view, name='logout'),
    # allauth social OAuth URLs — shared views (cancelled, error, signup, connections)
    path('', include('allauth.socialaccount.urls')),
    # Google OAuth2 URLs — /accounts/google/login/ and /accounts/google/login/callback/
    # Provider URLs are separate from allauth.socialaccount.urls and must be included explicitly.
    path('', include('allauth.socialaccount.providers.google.urls')),
]
