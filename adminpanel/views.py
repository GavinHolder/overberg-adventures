"""
Admin backend views for Overstrand Adventures.

This backend (/backend/) is for operators and admins managing global site settings.
Guides use /guide/ for tour management.

Access: OPERATOR role, ADMIN role, and Django staff.
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponseNotAllowed, HttpResponseNotFound
from django.shortcuts import render, redirect, get_object_or_404

from .decorators import backend_required

User = get_user_model()


def _dev_mode():
    """Return True when DEV_MODE is active."""
    return getattr(settings, 'DEV_MODE', False)


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------

@backend_required
def overview(request):
    """
    Admin backend home — key stats dashboard.

    Shows counts for: tours, active bookings, users by role, social auth status.
    """
    from apps.tours.models import Tour
    from apps.bookings.models import Booking
    from apps.accounts.models import UserProfile, SocialAuthProvider

    stats = {
        'total_tours': Tour.objects.count(),
        'active_tours': Tour.objects.filter(status='ACTIVE').count(),
        'total_bookings': Booking.objects.count(),
        'total_users': User.objects.count(),
        'guides': UserProfile.objects.filter(role='GUIDE').count(),
        'operators': UserProfile.objects.filter(role='OPERATOR').count(),
        'guests': UserProfile.objects.filter(role='GUEST').count(),
        'social_providers_active': SocialAuthProvider.objects.filter(enabled=True).count(),
    }
    return render(request, 'backend/overview.html', {
        'stats': stats,
        'dev_mode': _dev_mode(),
    })


# ---------------------------------------------------------------------------
# Site Settings
# ---------------------------------------------------------------------------

@backend_required
def site_settings(request):
    """
    Manage global site settings: company name, logo, contacts, social media.
    """
    from adminpanel.models import SiteSettings
    settings_obj = SiteSettings.get()

    if request.method == 'POST':
        settings_obj.company_name = request.POST.get('company_name', '').strip()
        settings_obj.tagline = request.POST.get('tagline', '').strip()
        settings_obj.contact_email = request.POST.get('contact_email', '').strip()
        settings_obj.contact_phone = request.POST.get('contact_phone', '').strip()
        settings_obj.whatsapp_number = request.POST.get('whatsapp_number', '').strip()
        settings_obj.address = request.POST.get('address', '').strip()
        settings_obj.instagram_url = request.POST.get('instagram_url', '').strip()
        settings_obj.facebook_url = request.POST.get('facebook_url', '').strip()
        settings_obj.twitter_url = request.POST.get('twitter_url', '').strip()
        settings_obj.website_url = request.POST.get('website_url', '').strip()

        # Handle logo upload
        if 'logo' in request.FILES:
            settings_obj.logo = request.FILES['logo']

        settings_obj.save()
        from django.contrib import messages
        messages.success(request, 'Site settings saved.')
        return redirect('backend:site_settings')

    return render(request, 'backend/site_settings.html', {
        'settings': settings_obj,
        'dev_mode': _dev_mode(),
    })


# ---------------------------------------------------------------------------
# User Management
# ---------------------------------------------------------------------------

@backend_required
def users_list(request):
    """
    List all users with their roles, active status, and last login.

    Supports filtering by role via ?role= query parameter.
    """
    from apps.accounts.models import UserProfile

    role_filter = request.GET.get('role', '')
    users_qs = User.objects.select_related('profile').order_by('-date_joined')

    if role_filter:
        users_qs = users_qs.filter(profile__role=role_filter)

    return render(request, 'backend/users_list.html', {
        'users': users_qs,
        'role_filter': role_filter,
        'role_choices': UserProfile.Role.choices,
        'dev_mode': _dev_mode(),
    })


@backend_required
def user_edit(request, pk):
    """
    Edit a user's role and staff status.

    Only superusers can promote users to staff (is_staff).
    """
    from apps.accounts.models import UserProfile

    target_user = get_object_or_404(User, pk=pk)
    profile, _ = UserProfile.objects.get_or_create(user=target_user)

    if request.method == 'POST':
        role = request.POST.get('role', profile.role)
        if role in [r[0] for r in UserProfile.Role.choices]:
            profile.role = role
            profile.save(update_fields=['role'])

        # Only superusers can toggle is_staff
        if request.user.is_superuser:
            target_user.is_staff = request.POST.get('is_staff') == 'on'
            target_user.save(update_fields=['is_staff'])

        from django.contrib import messages
        messages.success(request, f'Updated {profile.full_name or target_user.email}.')
        return redirect('backend:users_list')

    return render(request, 'backend/user_edit.html', {
        'target_user': target_user,
        'profile': profile,
        'role_choices': UserProfile.Role.choices,
        'dev_mode': _dev_mode(),
    })


@backend_required
def user_toggle_active(request, pk):
    """HTMX POST — toggle user active status."""
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    target_user = get_object_or_404(User, pk=pk)

    # Prevent locking yourself out
    if target_user == request.user:
        return HttpResponseNotFound()

    target_user.is_active = not target_user.is_active
    target_user.save(update_fields=['is_active'])

    from apps.accounts.models import UserProfile
    profile, _ = UserProfile.objects.get_or_create(user=target_user)

    return render(request, 'backend/partials/user_row.html', {
        'u': target_user,
        'profile': profile,
    })


# ---------------------------------------------------------------------------
# Social Auth Settings (moved from guide dashboard)
# ---------------------------------------------------------------------------

@backend_required
def social_auth_settings(request):
    """Manage social OAuth providers."""
    from apps.accounts.models import SocialAuthProvider
    providers = SocialAuthProvider.objects.all().order_by('display_name')
    return render(request, 'backend/social_auth.html', {
        'providers': providers,
        'dev_mode': _dev_mode(),
    })


@backend_required
def social_auth_toggle(request, pk):
    """HTMX POST — toggle a provider enabled/disabled."""
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    from apps.accounts.models import SocialAuthProvider
    provider = get_object_or_404(SocialAuthProvider, pk=pk)
    provider.enabled = not provider.enabled
    provider.save(update_fields=['enabled'])
    return render(request, 'backend/partials/provider_card.html', {'provider': provider})


@backend_required
def social_auth_save(request, pk):
    """HTMX POST — save credentials for a provider."""
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    from apps.accounts.models import SocialAuthProvider
    provider = get_object_or_404(SocialAuthProvider, pk=pk)
    provider.client_id = request.POST.get('client_id', '').strip()
    provider.client_secret = request.POST.get('client_secret', '').strip()
    provider.save(update_fields=['client_id', 'client_secret'])
    return render(request, 'backend/partials/provider_card.html', {
        'provider': provider,
        'saved': True,
    })
