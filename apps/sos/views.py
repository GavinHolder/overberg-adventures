from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from apps.bookings.models import Booking
from .models import SosConfig, EmergencyContact


@login_required
def sos_screen(request):
    config = SosConfig.objects.first() or SosConfig()
    contacts = EmergencyContact.objects.filter(is_active=True) if config.show_emergency_contacts else []
    # Fetch most recent active booking to get guide's WhatsApp for SOS
    active_booking = (
        Booking.objects.filter(user=request.user)
        .exclude(status=Booking.Status.CANCELLED)
        .select_related('tour__guide__profile')
        .order_by('-tour__start_datetime')
        .first()
    )
    guide_whatsapp = None
    if active_booking and active_booking.tour.guide:
        guide_whatsapp = getattr(active_booking.tour.guide.profile, 'phone_whatsapp', None)
    return render(request, 'app/sos.html', {
        'config': config,
        'contacts': contacts,
        'active_booking': active_booking,
        'guide_whatsapp': guide_whatsapp,
    })
