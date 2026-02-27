import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
def test_login_page_renders(client):
    response = client.get(reverse('accounts:login'))
    assert response.status_code == 200


@pytest.mark.django_db
def test_email_signup_creates_user_and_sends_otp(client, mailoutbox, settings):
    settings.DEV_MODE = False
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    response = client.post(reverse('accounts:email_signup'), {'email': 'new@test.com'})
    assert response.status_code == 302
    assert User.objects.filter(email='new@test.com').exists()
    assert len(mailoutbox) == 1


@pytest.mark.django_db
def test_email_signup_dev_mode_stores_otp_in_session(client, settings):
    # DEV_MODE = True but DEBUG stays False to avoid debug toolbar URL conflicts in tests.
    # The view only checks settings.DEV_MODE, not DEBUG, for the session path.
    settings.DEV_MODE = True
    settings.DEBUG = False
    response = client.post(reverse('accounts:email_signup'), {'email': 'dev@test.com'})
    assert response.status_code == 302
    assert 'dev_otp' in client.session


@pytest.mark.django_db
def test_verify_otp_correct_code_logs_in(client):
    from apps.accounts.models import EmailOTP
    user = User.objects.create_user(
        username='v@test.com', email='v@test.com', password='x', is_active=False
    )
    otp = EmailOTP.objects.create_for_user(user)
    session = client.session
    session['otp_user_id'] = user.pk
    session.save()
    response = client.post(reverse('accounts:verify_otp'), {'code': otp.code})
    assert response.status_code == 302
    user.refresh_from_db()
    assert user.is_active


@pytest.mark.django_db
def test_verify_otp_wrong_code_increments_attempts(client):
    from apps.accounts.models import EmailOTP
    user = User.objects.create_user(
        username='w@test.com', email='w@test.com', password='x', is_active=False
    )
    otp = EmailOTP.objects.create_for_user(user)
    session = client.session
    session['otp_user_id'] = user.pk
    session.save()
    client.post(reverse('accounts:verify_otp'), {'code': '000000'})
    otp.refresh_from_db()
    assert otp.attempts == 1


@pytest.mark.django_db
def test_profile_setup_step1_saves_name(client):
    user = User.objects.create_user(username='s@test.com', email='s@test.com', password='x')
    client.force_login(user)
    response = client.post(reverse('accounts:profile_setup_step', args=[1]), {
        'first_name': 'John',
        'last_name': 'Doe',
        'phone_whatsapp': '+27821234567',
    })
    assert response.status_code in [200, 302]
    user.profile.refresh_from_db()
    assert user.profile.first_name == 'John'


@pytest.mark.django_db
def test_verify_otp_get_renders_form(client):
    user = User.objects.create_user(
        username='g@test.com', email='g@test.com', password='x', is_active=False
    )
    session = client.session
    session['otp_user_id'] = user.pk
    session.save()
    response = client.get(reverse('accounts:verify_otp'))
    assert response.status_code == 200


@pytest.mark.django_db
def test_verify_otp_no_session_redirects(client):
    response = client.get(reverse('accounts:verify_otp'))
    assert response.status_code == 302


@pytest.mark.django_db
def test_profile_setup_requires_login(client):
    response = client.get(reverse('accounts:profile_setup'))
    assert response.status_code == 302
    assert '/login/' in response.url or '/accounts/' in response.url


@pytest.mark.django_db
def test_profile_setup_step2_saves_health(client):
    user = User.objects.create_user(username='h@test.com', email='h@test.com', password='x')
    client.force_login(user)
    response = client.post(reverse('accounts:profile_setup_step', args=[2]), {
        'fitness_level': '4',
        'medical_conditions': 'None',
        'dietary_requirements': 'Vegetarian',
    })
    assert response.status_code in [200, 302]
    user.profile.refresh_from_db()
    assert user.profile.fitness_level == 4
    assert user.profile.dietary_requirements == 'Vegetarian'


@pytest.mark.django_db
def test_logout_redirects_to_login(client):
    user = User.objects.create_user(username='lo@test.com', email='lo@test.com', password='x')
    client.force_login(user)
    response = client.get(reverse('accounts:logout'))
    assert response.status_code == 302
