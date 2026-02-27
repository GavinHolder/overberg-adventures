from django.conf import settings


def get_payment_adapter():
    """
    Return the configured payment gateway adapter.

    ASSUMPTIONS:
    1. settings.PAYMENT_GATEWAY is one of: 'manual', 'payfast', 'peach', 'dev'
    2. DEV_MODE is True only in non-production environments
    3. PayFast/Peach adapters will be created in future phases
    """
    gateway = getattr(settings, 'PAYMENT_GATEWAY', 'manual')
    if gateway == 'payfast':
        from .payfast import PayFastAdapter
        return PayFastAdapter()
    if gateway == 'peach':
        from .peach import PeachPaymentsAdapter
        return PeachPaymentsAdapter()
    if gateway == 'dev' or (gateway == 'manual' and getattr(settings, 'DEV_MODE', False)):
        from .dev import DevSimulateAdapter
        return DevSimulateAdapter()
    from .manual import ManualPaymentAdapter
    return ManualPaymentAdapter()
