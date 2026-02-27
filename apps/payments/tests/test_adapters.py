import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from apps.tours.models import Tour, TourCodeWord
from apps.bookings.models import Booking

User = get_user_model()


@pytest.fixture
def tour(db):
    return Tour.objects.create(
        name='Test Tour',
        start_datetime=timezone.now() + timedelta(days=7),
        location_name='Kleinmond',
        location_lat='-34.3',
        location_lng='19.1',
        capacity=20,
    )


@pytest.fixture
def user(db):
    return User.objects.create_user(username='paytester', password='pass')


@pytest.fixture
def booking(tour, user):
    return Booking.objects.create(user=user, tour=tour, status=Booking.Status.RSVP_PENDING)


@pytest.fixture
def seeded_words(db):
    TourCodeWord.objects.create(word='fynbos', is_used=False)
    TourCodeWord.objects.create(word='pelican', is_used=False)


def test_get_adapter_returns_manual_by_default(settings):
    settings.PAYMENT_GATEWAY = 'manual'
    settings.DEV_MODE = False
    from apps.payments.adapters import get_payment_adapter
    from apps.payments.adapters.manual import ManualPaymentAdapter
    adapter = get_payment_adapter()
    assert isinstance(adapter, ManualPaymentAdapter)


def test_get_adapter_returns_dev_when_dev_gateway(settings):
    settings.PAYMENT_GATEWAY = 'dev'
    settings.DEV_MODE = True
    from apps.payments.adapters import get_payment_adapter
    from apps.payments.adapters.dev import DevSimulateAdapter
    adapter = get_payment_adapter()
    assert isinstance(adapter, DevSimulateAdapter)


def test_get_adapter_returns_dev_when_manual_and_dev_mode(settings):
    settings.PAYMENT_GATEWAY = 'manual'
    settings.DEV_MODE = True
    from apps.payments.adapters import get_payment_adapter
    from apps.payments.adapters.dev import DevSimulateAdapter
    adapter = get_payment_adapter()
    assert isinstance(adapter, DevSimulateAdapter)


@pytest.mark.django_db
def test_dev_simulate_confirms_booking(booking, seeded_words):
    from apps.payments.adapters.dev import DevSimulateAdapter
    adapter = DevSimulateAdapter()
    result = adapter.simulate_payment(booking)
    assert result.success
    booking.refresh_from_db()
    assert booking.status == 'CONFIRMED'
    assert booking.tour_code != ''
    assert booking.confirmed_at is not None


@pytest.mark.django_db
def test_manual_adapter_process_confirmation(booking, seeded_words):
    from apps.payments.adapters.manual import ManualPaymentAdapter
    from apps.payments.adapters.base import PaymentResult
    adapter = ManualPaymentAdapter()
    result = PaymentResult(success=True, reference='MANUAL-001')
    adapter.process_confirmation(booking, result)
    booking.refresh_from_db()
    assert booking.status == 'CONFIRMED'
    assert booking.tour_code != ''


@pytest.mark.django_db
def test_manual_adapter_webhook_raises(booking):
    from apps.payments.adapters.manual import ManualPaymentAdapter
    adapter = ManualPaymentAdapter()
    with pytest.raises(NotImplementedError):
        adapter.verify_webhook(None)


def test_payment_result_defaults():
    from apps.payments.adapters.base import PaymentResult
    result = PaymentResult(success=True)
    assert result.reference == ''
    assert result.error == ''
