from .base import PaymentGatewayAdapter, PaymentResult


class PayFastAdapter(PaymentGatewayAdapter):
    """Stub — PayFast integration not yet implemented. Will be added in Phase 10."""

    def __init__(self):
        raise NotImplementedError('PayFast adapter not yet implemented.')

    def create_payment_session(self, booking, amount_zar: int) -> dict: ...

    def verify_webhook(self, request) -> PaymentResult: ...

    def process_confirmation(self, booking, result: PaymentResult) -> None: ...
