from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class PaymentResult:
    success: bool
    reference: str = ''
    error: str = ''


class PaymentGatewayAdapter(ABC):
    """
    Abstract base for all payment gateway adapters.
    Implement all three methods for a complete gateway integration.
    """

    @abstractmethod
    def create_payment_session(self, booking, amount_zar: int) -> dict:
        """Return redirect URL or form fields for payment page."""

    @abstractmethod
    def verify_webhook(self, request) -> PaymentResult:
        """Verify incoming webhook and return result."""

    @abstractmethod
    def process_confirmation(self, booking, result: PaymentResult) -> None:
        """Called after successful payment — assign tour code, send email, confirm booking."""
