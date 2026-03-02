import random
from datetime import timedelta
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()


class EmailOTPManager(models.Manager):
    def create_for_user(self, user):
        """Delete any existing unverified OTPs, create fresh 6-digit code."""
        self.filter(user=user, is_verified=False).delete()
        code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        return self.create(user=user, code=code)


class EmailOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otps')
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    attempts = models.PositiveSmallIntegerField(default=0)

    objects = EmailOTPManager()

    @property
    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=15)

    @property
    def is_locked_out(self):
        return self.attempts >= 3

    class Meta:
        ordering = ['-created_at']


class UserProfile(models.Model):
    class Role(models.TextChoices):
        GUEST = 'GUEST', 'Guest Traveller'
        GUIDE = 'GUIDE', 'Tour Guide'
        OPERATOR = 'OPERATOR', 'Operator'
        ADMIN = 'ADMIN', 'Admin'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.GUEST)
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    phone_whatsapp = models.CharField(max_length=20, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    avatar_url = models.URLField(
        max_length=500,
        blank=True,
        help_text='Profile picture URL from social login (Google, Facebook, etc.).',
    )
    social_provider = models.CharField(
        max_length=50,
        blank=True,
        help_text='Which social provider was used to create this account (e.g. "google").',
    )
    # Step 2: Health
    fitness_level = models.PositiveSmallIntegerField(default=3)  # 1-5
    medical_conditions = models.TextField(blank=True)
    dietary_requirements = models.TextField(blank=True)
    # Step 4: Notes
    personal_notes = models.TextField(blank=True)
    # Step 5: Indemnity
    indemnity_accepted = models.BooleanField(default=False)
    indemnity_accepted_at = models.DateTimeField(null=True, blank=True)
    # App permissions
    location_enabled = models.BooleanField(default=False)
    notifications_enabled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def setup_complete(self):
        return bool(self.first_name and self.indemnity_accepted)

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip() or self.user.email

    @property
    def display_avatar(self):
        """
        Return the URL to display as the user's avatar.

        Priority order:
        1. Uploaded avatar image (user explicitly set this — highest priority).
        2. Social provider avatar URL (from Google profile picture, etc.).
        3. None → template should render initials circle fallback.
        """
        if self.avatar:
            return self.avatar.url
        if self.avatar_url:
            return self.avatar_url
        return None

    @property
    def initials(self):
        """Return 1-2 letter initials for avatar fallback display."""
        if self.first_name and self.last_name:
            return (self.first_name[0] + self.last_name[0]).upper()
        if self.first_name:
            return self.first_name[0].upper()
        return self.user.email[0].upper()

    def __str__(self):
        return self.full_name


class SocialAuthProvider(models.Model):
    """
    Tracks which social OAuth providers are enabled and stores their credentials.

    This model is the single source of truth for social authentication config.
    Backend admins can toggle providers on/off and update credentials without
    touching environment variables.

    A post_save signal syncs credentials to allauth's SocialApp model so allauth
    can perform the OAuth flow using the stored client_id/secret.

    ASSUMPTIONS:
    1. SITE_ID=1 is always valid (django.contrib.sites is installed).
    2. client_id and client_secret are stored in plaintext — acceptable for MVP,
       encrypt at rest in production via Django encrypted fields or vault.
    3. Only providers listed in Provider.choices are supported by allauth.

    FAILURE MODES:
    - Missing Site(pk=1): SocialApp sync will fail silently (logged, not raised).
    - Empty client_id/secret with enabled=True: is_active returns False, login
      button will not be shown, but allauth SocialApp still exists (harmless).
    """

    class Provider(models.TextChoices):
        GOOGLE = 'google', 'Google'
        # Future providers — add here and install corresponding allauth provider app:
        # FACEBOOK = 'facebook', 'Facebook'
        # APPLE = 'apple', 'Apple'
        # MICROSOFT = 'microsoft', 'Microsoft'

    provider = models.CharField(
        max_length=50,
        choices=Provider.choices,
        unique=True,
        help_text='The allauth provider key (e.g. "google").',
    )
    display_name = models.CharField(max_length=100, help_text='Shown on the login button.')
    enabled = models.BooleanField(
        default=False,
        help_text='When disabled, the login button is hidden regardless of credentials.',
    )
    client_id = models.CharField(max_length=500, blank=True)
    client_secret = models.CharField(max_length=500, blank=True)
    extra_config = models.JSONField(
        default=dict,
        blank=True,
        help_text='Optional provider-specific JSON config passed to allauth.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_configured(self):
        """True only when both client_id and client_secret have been entered."""
        return bool(self.client_id and self.client_secret)

    @property
    def is_active(self):
        """True only when enabled AND credentials are present. Used by login template."""
        return self.enabled and self.is_configured

    def __str__(self):
        status = 'active' if self.is_active else ('enabled/unconfigured' if self.enabled else 'disabled')
        return f'{self.display_name} ({status})'

    class Meta:
        verbose_name = 'Social Auth Provider'
        verbose_name_plural = 'Social Auth Providers'
        ordering = ['display_name']


from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=SocialAuthProvider)
def sync_social_app(sender, instance, **kwargs):
    """
    Sync SocialAuthProvider credentials to allauth's SocialApp model.

    allauth reads OAuth client_id/secret from SocialApp (DB) in preference to
    settings. This signal keeps SocialApp in sync whenever an admin updates the
    provider credentials or toggles enabled status.

    ASSUMPTIONS:
    1. Site with pk=SITE_ID exists (created by Django sites framework migrations).
    2. This signal fires after every save — including partial updates. Safe because
       allauth reads SocialApp at request time, not cached in memory.

    FAILURE MODES:
    - Site.DoesNotExist: Logged as warning; SocialApp not created/updated.
      Admin must run: python manage.py migrate && python manage.py createinitialrevisions
      or create Site(pk=1) manually.
    - allauth not installed: ImportError caught; signal exits silently.
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        from allauth.socialaccount.models import SocialApp
        from django.contrib.sites.models import Site
    except ImportError:
        return

    try:
        site = Site.objects.get(pk=1)
    except Site.DoesNotExist:
        logger.warning(
            'SocialAuthProvider sync: Site pk=1 not found. '
            'Run migrations and ensure django.contrib.sites is set up.'
        )
        return

    if instance.is_configured:
        social_app, created = SocialApp.objects.get_or_create(
            provider=instance.provider,
            defaults={
                'name': instance.display_name,
                'client_id': instance.client_id,
                'secret': instance.client_secret,
            },
        )
        if not created:
            social_app.name = instance.display_name
            social_app.client_id = instance.client_id
            social_app.secret = instance.client_secret
            social_app.save(update_fields=['name', 'client_id', 'secret'])

        # Ensure site is linked
        if site not in social_app.sites.all():
            social_app.sites.add(site)
