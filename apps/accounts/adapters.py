"""
Custom django-allauth adapters for Overstrand Adventures.

We use allauth ONLY for social OAuth (Google, etc.) — not for email/password auth,
which we handle via our own OTP flow. These adapters bridge the social login
result into our UserProfile system.
"""
import logging
from datetime import date

import requests as http_requests
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
from django.urls import reverse

from .models import UserProfile

logger = logging.getLogger(__name__)
User = get_user_model()

GOOGLE_PEOPLE_API = 'https://people.googleapis.com/v1/people/me'


def _fetch_google_birthday(access_token):
    """
    Call Google People API to retrieve the user's date of birth.

    Returns a date object if Google returns a complete birthday (year + month + day),
    otherwise returns None. This is a best-effort call — failure is non-fatal.

    ASSUMPTIONS:
    1. access_token is a valid Google OAuth2 token with user.birthday.read scope.
    2. Google only returns a birthday if the user has set one AND it's not private.
       Expect None for ~70% of users.
    3. Google may return multiple birthday entries (account + contact sources).
       We use the first entry that has a complete date (year + month + day).

    FAILURE MODES:
    - API unreachable / timeout: returns None, logged as warning.
    - Scope not granted: 403 response, returns None.
    - Birthday set without year (common): returns None — incomplete for our use.
    - Unexpected response shape: returns None, logged as warning.
    """
    try:
        resp = http_requests.get(
            GOOGLE_PEOPLE_API,
            params={'personFields': 'birthdays'},
            headers={'Authorization': f'Bearer {access_token}'},
            timeout=5,
        )
        if resp.status_code != 200:
            logger.warning('Google People API returned %s for birthday fetch', resp.status_code)
            return None

        for entry in resp.json().get('birthdays', []):
            d = entry.get('date', {})
            year, month, day = d.get('year'), d.get('month'), d.get('day')
            if year and month and day:
                return date(year, month, day)

        return None

    except Exception as exc:
        logger.warning('Google birthday fetch failed: %s', exc)
        return None


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

        For new users: links the social account to an existing user by email if
        one exists (prevents duplicate accounts for users who signed up via OTP first).

        For returning users: opportunistically backfills date_of_birth from the
        People API if it was not set during their original sign-up (e.g. they
        logged in before birthday fetching was implemented).

        ASSUMPTIONS:
        - sociallogin.is_existing: True if this social account is already linked.
        - Email uniqueness enforced on User model (Django default).
        - Birthday backfill is best-effort; failure is silently ignored.
        """
        if sociallogin.is_existing:
            # Returning user — backfill birthday if not yet set
            try:
                profile = sociallogin.user.profile
                token = getattr(sociallogin, 'token', None)
                if not profile.date_of_birth and token:
                    birthday = _fetch_google_birthday(token.token)
                    if birthday:
                        profile.date_of_birth = birthday
                        profile.save(update_fields=['date_of_birth'])
            except Exception as exc:
                logger.warning('Birthday backfill for returning user failed: %s', exc)
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

        Populates UserProfile with data from the social provider:
        - first_name / last_name from Google's id_token claims
        - avatar_url from Google's 'picture' field
        - social_provider label for template badges
        - date_of_birth from Google People API (best-effort, requires birthday scope)

        ASSUMPTIONS:
        1. sociallogin.token is available and contains a valid access_token string.
        2. UserProfile is auto-created by post_save signal before this runs.
        3. Birthday fetch is non-fatal — profile is saved with or without it.
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
            profile.avatar_url = avatar_url

        # Record which provider was used
        profile.social_provider = sociallogin.account.provider

        # Fetch birthday from Google People API (requires user.birthday.read scope)
        token = getattr(sociallogin, 'token', None)
        if token and not profile.date_of_birth:
            profile.date_of_birth = _fetch_google_birthday(token.token)

        profile.save(update_fields=[
            'first_name', 'last_name', 'avatar_url', 'social_provider', 'date_of_birth',
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
