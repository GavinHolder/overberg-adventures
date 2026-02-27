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
    def initials(self):
        if self.first_name:
            return self.first_name[0].lower()
        return self.user.email[0].lower()

    def __str__(self):
        return self.full_name


from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)
