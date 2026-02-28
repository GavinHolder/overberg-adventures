from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.conf import settings
from apps.bookings.models import Booking


@login_required
def map_screen(request):
    booking = (
        Booking.objects.filter(user=request.user)
        .exclude(status=Booking.Status.CANCELLED)
        .select_related('tour')
        .order_by('-tour__start_datetime')
        .first()
    )
    return render(request, 'app/map.html', {
        'booking': booking,
        'tour': booking.tour if booking else None,
        'google_maps_api_key': getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
    })
