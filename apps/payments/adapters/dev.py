from django.utils import timezone
from .base import PaymentGatewayAdapter, PaymentResult


class DevSimulateAdapter(PaymentGatewayAdapter):
    """
    DEV_MODE only — instantly confirms any booking without real payment.
    Never active when DEV_MODE=False (enforced in get_payment_adapter).
    """

    def create_payment_session(self, booking, amount_zar: int) -> dict:
        return {'dev_simulate': True, 'booking_id': booking.pk}

    def verify_webhook(self, request) -> PaymentResult:
        return PaymentResult(success=True, reference='DEV-SIM')

    def simulate_payment(self, booking) -> PaymentResult:
        result = PaymentResult(success=True, reference='DEV-SIM')
        self.process_confirmation(booking, result)
        return result

    def process_confirmation(self, booking, result: PaymentResult) -> None:
        from apps.tours.models import TourCodeWord
        from apps.notifications.tasks import send_tour_code_email
        booking.status = 'CONFIRMED'
        booking.tour_code = TourCodeWord.generate()
        booking.confirmed_at = timezone.now()
        booking.save()
        send_tour_code_email.delay(booking.pk)
