from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model, login, logout
from django.contrib import messages
from django.http import HttpResponse
from django.conf import settings
from django.utils import timezone
from django.views.decorators.http import require_POST, require_http_methods

from .models import EmailOTP, UserProfile
from .emails import send_otp_email

User = get_user_model()

DEV_ALLOWED_STEPS = range(1, 6)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_htmx(request):
    return request.headers.get('HX-Request') == 'true'


def _get_otp_user(request):
    """Return the User associated with the current OTP session, or None."""
    user_id = request.session.get('otp_user_id')
    if not user_id:
        return None
    try:
        return User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return None


# ---------------------------------------------------------------------------
# Login page
# ---------------------------------------------------------------------------

def login_page(request):
    if request.user.is_authenticated:
        return redirect('/')
    return render(request, 'accounts/login.html', {
        'dev_mode': getattr(settings, 'DEV_MODE', False),
    })


# ---------------------------------------------------------------------------
# Email signup — POST email → create user → send OTP → redirect to verify
# ---------------------------------------------------------------------------

@require_POST
def email_signup(request):
    email = request.POST.get('email', '').strip().lower()
    if not email:
        messages.error(request, 'Please enter your email address.')
        return redirect('accounts:login')

    user, created = User.objects.get_or_create(
        email=email,
        defaults={
            'username': email,
            'is_active': False,
        }
    )

    if not created and user.is_active:
        # Existing active user — re-auth via OTP
        pass
    elif not created and not user.is_active:
        # Incomplete signup — resend OTP
        pass

    otp = EmailOTP.objects.create_for_user(user)
    request.session['otp_user_id'] = user.pk

    dev_mode = getattr(settings, 'DEV_MODE', False)
    if dev_mode:
        # Store OTP code in session for display on verify page
        request.session['dev_otp'] = otp.code
    else:
        try:
            send_otp_email(user, otp.code)
        except Exception:
            messages.error(request, 'Failed to send verification email. Please try again.')
            return redirect('accounts:login')

    return redirect('accounts:verify_otp')


# ---------------------------------------------------------------------------
# Verify OTP
# ---------------------------------------------------------------------------

@require_http_methods(['GET', 'POST'])
def verify_otp(request):
    user = _get_otp_user(request)
    if not user:
        messages.error(request, 'Session expired. Please start again.')
        return redirect('accounts:login')

    dev_mode = getattr(settings, 'DEV_MODE', False)
    dev_otp = request.session.get('dev_otp') if dev_mode else None

    # Mask email for display: j***@example.com
    email = user.email
    at = email.index('@')
    masked_email = email[0] + '***' + email[at:]

    if request.method == 'GET':
        return render(request, 'accounts/verify_otp.html', {
            'masked_email': masked_email,
            'dev_mode': dev_mode,
            'dev_otp': dev_otp,
        })

    # POST
    code = request.POST.get('code', '').strip()

    try:
        otp = EmailOTP.objects.filter(user=user, is_verified=False).latest('created_at')
    except EmailOTP.DoesNotExist:
        messages.error(request, 'No verification code found. Please request a new one.')
        return redirect('accounts:login')

    if otp.is_locked_out:
        messages.error(request, 'Too many incorrect attempts. Please request a new code.')
        return render(request, 'accounts/verify_otp.html', {
            'masked_email': masked_email,
            'dev_mode': dev_mode,
            'dev_otp': dev_otp,
            'error': 'locked',
        })

    if otp.is_expired:
        messages.error(request, 'Your code has expired. Please request a new one.')
        return render(request, 'accounts/verify_otp.html', {
            'masked_email': masked_email,
            'dev_mode': dev_mode,
            'dev_otp': dev_otp,
            'error': 'expired',
        })

    if otp.code != code:
        otp.attempts += 1
        otp.save(update_fields=['attempts'])
        remaining = 3 - otp.attempts
        messages.error(request, f'Incorrect code. {remaining} attempt(s) remaining.')
        return render(request, 'accounts/verify_otp.html', {
            'masked_email': masked_email,
            'dev_mode': dev_mode,
            'dev_otp': dev_otp,
            'error': 'wrong',
        })

    # Success
    otp.is_verified = True
    otp.save(update_fields=['is_verified'])

    user.is_active = True
    user.save(update_fields=['is_active'])

    # Clean up session keys
    request.session.pop('otp_user_id', None)
    request.session.pop('dev_otp', None)

    # Log user in using ModelBackend directly
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')

    return redirect('accounts:profile_setup')


# ---------------------------------------------------------------------------
# Dev login — bypasses OTP entirely (DEV_MODE only)
# ---------------------------------------------------------------------------

@require_POST
def dev_login(request):
    if not getattr(settings, 'DEV_MODE', False):
        return HttpResponse('Not available', status=403)

    email = request.POST.get('email', '').strip().lower()
    if not email:
        messages.error(request, 'Please enter an email address.')
        return redirect('accounts:login')

    user, _ = User.objects.get_or_create(
        email=email,
        defaults={
            'username': email,
            'is_active': True,
        }
    )
    if not user.is_active:
        user.is_active = True
        user.save(update_fields=['is_active'])

    # Ensure profile exists
    UserProfile.objects.get_or_create(user=user)

    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return redirect('/')


# ---------------------------------------------------------------------------
# Profile setup redirect
# ---------------------------------------------------------------------------

def profile_setup(request):
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    profile = request.user.profile
    if profile.setup_complete:
        return redirect('/')

    return redirect('accounts:profile_setup_step', step=1)


# ---------------------------------------------------------------------------
# Profile setup wizard (5 steps)
# ---------------------------------------------------------------------------

STEP_TEMPLATES = {
    1: 'accounts/setup/step1_personal.html',
    2: 'accounts/setup/step2_health.html',
    3: 'accounts/setup/step3_permissions.html',
    4: 'accounts/setup/step4_notes.html',
    5: 'accounts/setup/step5_indemnity.html',
}


def profile_setup_step(request, step):
    if not request.user.is_authenticated:
        return redirect('accounts:login')

    if step not in STEP_TEMPLATES:
        return redirect('accounts:profile_setup_step', step=1)

    profile = request.user.profile

    if request.method == 'POST':
        if step == 1:
            profile.first_name = request.POST.get('first_name', '').strip()
            profile.last_name = request.POST.get('last_name', '').strip()
            profile.phone_whatsapp = request.POST.get('phone_whatsapp', '').strip()
            dob = request.POST.get('date_of_birth', '').strip()
            if dob:
                try:
                    from datetime import date
                    profile.date_of_birth = date.fromisoformat(dob)
                except ValueError:
                    pass
            profile.save()

        elif step == 2:
            try:
                fitness = int(request.POST.get('fitness_level', 3))
                if 1 <= fitness <= 5:
                    profile.fitness_level = fitness
            except (ValueError, TypeError):
                pass
            profile.medical_conditions = request.POST.get('medical_conditions', '').strip()
            profile.dietary_requirements = request.POST.get('dietary_requirements', '').strip()
            profile.save()

        elif step == 3:
            profile.location_enabled = request.POST.get('location_enabled') == 'on'
            profile.notifications_enabled = request.POST.get('notifications_enabled') == 'on'
            profile.save()

        elif step == 4:
            profile.personal_notes = request.POST.get('personal_notes', '').strip()
            profile.save()

        elif step == 5:
            if request.POST.get('indemnity_accepted') == 'on':
                profile.indemnity_accepted = True
                profile.indemnity_accepted_at = timezone.now()
                profile.save()
                return redirect('/')

        # Move to next step
        next_step = step + 1
        if next_step > 5:
            return redirect('/')

        if _is_htmx(request):
            template = STEP_TEMPLATES[next_step]
            ctx = _step_context(request, next_step)
            return render(request, template, ctx)

        return redirect('accounts:profile_setup_step', step=next_step)

    # GET
    template = STEP_TEMPLATES[step]
    ctx = _step_context(request, step)
    return render(request, 'accounts/setup/wizard.html', {**ctx, 'step_template': template})


def _step_context(request, step):
    return {
        'step': step,
        'total_steps': 5,
        'profile': request.user.profile,
        'user': request.user,
        'dev_mode': getattr(settings, 'DEV_MODE', False),
    }


# ---------------------------------------------------------------------------
# Profile settings toggle (HTMX POST)
# ---------------------------------------------------------------------------

@require_POST
def profile_settings_toggle(request):
    if not request.user.is_authenticated:
        return HttpResponse('Unauthorized', status=401)

    profile = request.user.profile
    field = request.POST.get('field')

    if field == 'location_enabled':
        profile.location_enabled = not profile.location_enabled
        profile.save(update_fields=['location_enabled'])
    elif field == 'notifications_enabled':
        profile.notifications_enabled = not profile.notifications_enabled
        profile.save(update_fields=['notifications_enabled'])

    return render(request, 'accounts/partials/settings_toggle.html', {
        'profile': profile,
        'field': field,
    })


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

def logout_view(request):
    logout(request)
    return redirect('accounts:login')
