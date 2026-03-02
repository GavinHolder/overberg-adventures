"""
Custom django-allauth adapters for Overstrand Adventures.

We use allauth ONLY for social OAuth (Google, etc.) — not for email/password auth,
which we handle via our own OTP flow. These adapters bridge the social login
result into our UserProfile system.
"""
import logging

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
from django.urls import reverse

from .models import UserProfile

logger = logging.getLogger(__name__)
User = get_user_model()


class OurSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom adapter that integrates allauth social login with our auth system.

    Responsibilities:
    1. Link social login to existing users by email (prevents duplicate accounts).
    2. Sync avatar URL from Google profile picture into UserProfile.avatar_url.
    3. Pre-populate UserProfile.first_name / last_name from social data.
    4. Mark social_provider on the profile so templates can display the right badge.
    5. Redirect new social users to our profile setup wizard if setup is incomplete.

    ASSUMPTIONS:
    1. Social provider always supplies an email address (Google enforces this).
    2. UserProfile is auto-created by post_save signal when User is created.
    3. Google profile picture URLs are stable for the lifetime of the access token.
       We store the URL, not download the image — acceptable for MVP.

    FAILURE MODES:
    - No email from provider: pre_social_login skips email linking; new user created.
    - UserProfile missing: get_or_create used defensively in save_user.
    - Avatar URL unavailable: avatar_url left blank; template shows initials.
    """

    def pre_social_login(self, request, sociallogin):
        """
        Called after OAuth callback but before the user is logged in.

        If the social account's email matches an existing user, link the social
        account to that user instead of creating a duplicate. This handles the
        case where someone signed up via email/OTP first and later uses Google.

        ASSUMPTIONS:
        - sociallogin.is_existing: True if this social account is already linked.
        - Email uniqueness enforced on User model (Django default).
        """
        if sociallogin.is_existing:
            # Already linked — nothing to do
            return

        email = sociallogin.account.extra_data.get('email', '').strip().lower()
        if not email:
            return

        try:
            existing_user = User.objects.get(email=email)
            # Link the social account to the existing user
            sociallogin.connect(request, existing_user)
        except User.DoesNotExist:
            # New user — allauth will create one
            pass

    def save_user(self, request, sociallogin, form=None):
        """
        Called when a new social user is created (first login ever).

        Populates UserProfile with data from the social provider.
        """
        user = super().save_user(request, sociallogin, form)
        user.is_active = True
        user.save(update_fields=['is_active'])

        profile, _ = UserProfile.objects.get_or_create(user=user)
        extra = sociallogin.account.extra_data

        # Sync name fields if not already set by user
        if not profile.first_name:
            profile.first_name = extra.get('given_name', '') or extra.get('first_name', '')
        if not profile.last_name:
            profile.last_name = extra.get('family_name', '') or extra.get('last_name', '')

        # Sync avatar URL — Google provides 'picture', Facebook provides 'picture.data.url'
        avatar_url = extra.get('picture', '')
        if avatar_url and not profile.avatar:
            # Only set avatar_url if user hasn't uploaded their own avatar
            profile.avatar_url = avatar_url

        # Record which provider was used
        profile.social_provider = sociallogin.account.provider

        profile.save(update_fields=[
            'first_name', 'last_name', 'avatar_url', 'social_provider',
        ])

        return user

    def get_connect_redirect_url(self, request, socialaccount):
        """Redirect after successfully connecting a social account."""
        return reverse('accounts:profile')

    def get_login_redirect_url(self, request):
        """
        After social login completes, redirect to profile setup if incomplete,
        otherwise to the app home.

        FAILURE MODES:
        - User with no profile (edge case): redirect to profile setup safely.
        """
        try:
            profile = request.user.profile
            if not profile.setup_complete:
                return reverse('accounts:profile_setup')
        except Exception:
            return reverse('accounts:profile_setup')
        return '/'
