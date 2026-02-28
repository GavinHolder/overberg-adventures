from django.db import models


class SosConfig(models.Model):
    """
    Singleton config for SOS feature.
    Admin toggles what options are shown to guests.
    """
    show_whatsapp_sos = models.BooleanField(default=True)
    show_sa_emergency_numbers = models.BooleanField(default=True)
    show_gps_share = models.BooleanField(default=True)
    show_first_aid = models.BooleanField(default=True)
    show_emergency_contacts = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'SOS Configuration'

    def __str__(self):
        return 'SOS Configuration'


class EmergencyContact(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    role = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name
