from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from apps.tours.models import Tour
from .models import Booking


@login_required
def itinerary_home(request):
    booking = (
        Booking.objects.filter(user=request.user)
        .exclude(status=Booking.Status.CANCELLED)
        .select_related('tour').order_by('-tour__start_datetime').first()
    )
    if booking:
        return redirect('bookings:itinerary_detail', booking_id=booking.id)
    return render(request, 'app/itinerary_empty.html', {})


@login_required
def itinerary_detail(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_related('tour', 'tour__guide', 'tour__guide__profile'),
        pk=booking_id, user=request.user,
    )
    items_by_day = {}
    for item in booking.tour.itinerary_items.select_related('category').all():
        items_by_day.setdefault(item.day, []).append(item)
    return render(request, 'app/itinerary.html', {
        'booking': booking,
        'tour': booking.tour,
        'items_by_day': items_by_day,
    })


@login_required
@require_http_methods(['POST'])
def rsvp_action(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id, user=request.user)
    if booking.status == Booking.Status.INVITED:
        booking.status = Booking.Status.RSVP_PENDING
        booking.save(update_fields=['status'])
    return redirect('bookings:itinerary_detail', booking_id=booking_id)


@login_required
@require_http_methods(['POST'])
def join_lookup(request):
    code = request.POST.get('tour_code', '').strip().lower()
    try:
        tour = Tour.objects.get(tour_code=code, status=Tour.Status.ACTIVE)
    except Tour.DoesNotExist:
        messages.error(request, f'Tour code "{code.upper()}" not found.')
        return redirect('landing:home')
    existing = Booking.objects.filter(user=request.user, tour=tour).first()
    if existing:
        return redirect('bookings:itinerary_detail', booking_id=existing.id)
    return redirect('bookings:join_confirm', tour_code=code)


@login_required
@require_http_methods(['GET', 'POST'])
def join_confirm(request, tour_code):
    tour = get_object_or_404(Tour, tour_code=tour_code, status=Tour.Status.ACTIVE)
    existing = Booking.objects.filter(user=request.user, tour=tour).first()
    if existing:
        return redirect('bookings:itinerary_detail', booking_id=existing.id)
    if request.method == 'POST':
        try:
            booking = Booking.objects.create_from_rsvp(request.user, tour)
        except ValueError:
            messages.error(request, 'Sorry, this tour is now full.')
            return redirect('landing:home')
        return redirect('bookings:itinerary_detail', booking_id=booking.id)
    return render(request, 'app/join_confirm.html', {
        'tour': tour, 'profile': request.user.profile,
    })
