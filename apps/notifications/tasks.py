from overberg_adventures.celery import app


@app.task
def send_tour_code_email(booking_pk: int) -> None:
    """
    Send tour code confirmation email to guest.
    Placeholder — full implementation in Phase 8 (Push Notifications).
    """
    # TODO: Phase 8 — load Booking, render email template, send via SendGrid
    pass
