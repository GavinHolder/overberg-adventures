"""
Admin panel models for Overstrand Adventures.

SiteSettings is a singleton — only one row should ever exist.
Use SiteSettings.get() to retrieve (and auto-create if missing).
"""
from django.db import models


class SiteSettings(models.Model):
    """
    Global site configuration managed by operators/admins via the backend.

    Singleton pattern — enforced by using pk=1 in get().
    All fields are optional so the object can be created empty on first access.

    ASSUMPTIONS:
    - Only one instance exists; pk=1 is always the canonical record.
    - Logo is stored in MEDIA_ROOT/site/ — ensure media serving is configured.

    FAILURE MODES:
    - Concurrent creation: get_or_create with pk=1 is atomic enough for MVP;
      add DB unique constraint or Redis lock for high-concurrency production.
    """

    company_name = models.CharField(max_length=200, blank=True, default='Overstrand Adventures')
    tagline = models.CharField(max_length=300, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    whatsapp_number = models.CharField(
        max_length=30,
        blank=True,
        help_text='Include country code, e.g. +27821234567',
    )
    address = models.TextField(blank=True)

    # Social media
    instagram_url = models.URLField(blank=True)
    facebook_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    website_url = models.URLField(blank=True)

    # Branding
    logo = models.ImageField(upload_to='site/', null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def get(cls):
        """Return the singleton SiteSettings, creating it if it does not exist."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return f'Site Settings — {self.company_name}'

    class Meta:
        verbose_name = 'Site Settings'
        verbose_name_plural = 'Site Settings'
