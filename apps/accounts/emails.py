from django.core.mail import send_mail
from django.conf import settings


def send_otp_email(user, code):
    send_mail(
        subject='Your Overstrand Adventures verification code',
        message=f'Your verification code is: {code}\n\nThis code expires in 15 minutes.',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
