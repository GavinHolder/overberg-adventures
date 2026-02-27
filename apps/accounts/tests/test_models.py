import pytest
from django.contrib.auth import get_user_model
from apps.accounts.models import EmailOTP, UserProfile

User = get_user_model()


@pytest.mark.django_db
def test_otp_created_with_6_digit_code():
    user = User.objects.create_user(username='t1@test.com', email='t1@test.com', password='x')
    otp = EmailOTP.objects.create_for_user(user)
    assert len(otp.code) == 6
    assert otp.code.isdigit()
    assert not otp.is_verified
    assert not otp.is_expired


@pytest.mark.django_db
def test_otp_replaces_existing():
    user = User.objects.create_user(username='t2@test.com', email='t2@test.com', password='x')
    otp1 = EmailOTP.objects.create_for_user(user)
    otp2 = EmailOTP.objects.create_for_user(user)
    assert EmailOTP.objects.filter(user=user, is_verified=False).count() == 1
    assert otp1.pk != otp2.pk


@pytest.mark.django_db
def test_otp_expires_after_15_minutes():
    from django.utils import timezone
    from datetime import timedelta
    user = User.objects.create_user(username='t3@test.com', email='t3@test.com', password='x')
    otp = EmailOTP.objects.create_for_user(user)
    otp.created_at = timezone.now() - timedelta(minutes=16)
    otp.save()
    assert otp.is_expired


@pytest.mark.django_db
def test_otp_locked_out_after_3_attempts():
    user = User.objects.create_user(username='t4@test.com', email='t4@test.com', password='x')
    otp = EmailOTP.objects.create_for_user(user)
    otp.attempts = 3
    assert otp.is_locked_out


@pytest.mark.django_db
def test_profile_autocreated_on_user_create():
    user = User.objects.create_user(username='t5@test.com', email='t5@test.com', password='x')
    assert hasattr(user, 'profile')
    assert user.profile.fitness_level == 3


@pytest.mark.django_db
def test_profile_setup_complete_requires_name_and_indemnity():
    user = User.objects.create_user(username='t6@test.com', email='t6@test.com', password='x')
    assert not user.profile.setup_complete
    user.profile.first_name = 'Test'
    user.profile.indemnity_accepted = True
    user.profile.save()
    assert user.profile.setup_complete
