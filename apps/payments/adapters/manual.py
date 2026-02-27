from django.utils import timezone
from .base import PaymentGatewayAdapter, PaymentResult


class ManualPaymentAdapter(PaymentGatewayAdapter):
    """
    Admin manually captures payment — no automated webhook flow.
    Used in production when no gateway is configured.
    """

    def create_payment_session(self, booking, amount_zar: int) -> dict:
        return {
            'manual': True,
            'instruction': 'Admin will capture payment manually.',
        }

    def verify_webhook(self, request) -> PaymentResult:
        raise NotImplementedError('Manual payments do not use webhooks.')

    def process_confirmation(self, booking, result: PaymentResult) -> None:
        from apps.tours.models import TourCodeWord
        from apps.notifications.tasks import send_tour_code_email
        booking.status = 'CONFIRMED'
        booking.tour_code = TourCodeWord.generate()
        booking.confirmed_at = timezone.now()
        booking.save()
        send_tour_code_email.delay(booking.pk)
