from functools import wraps
from django.shortcuts import render, redirect
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from django.conf import settings

from .decorators import guide_required, staff_required
from apps.tours.models import Tour


def _dev_mode():
    return getattr(settings, 'DEV_MODE', False)


@guide_required
def index(request):
    return redirect('dashboard:tours_list')


@guide_required
def tours_list(request):
    tours = Tour.objects.select_related('guide__profile').order_by('-start_datetime')
    profile = getattr(request.user, 'profile', None)
    if not request.user.is_staff and profile and profile.role == 'GUIDE':
        tours = tours.filter(guide=request.user)
    return render(request, 'admin_panel/tours/list.html', {
        'tours': tours,
        'dev_mode': _dev_mode(),
    })


@guide_required
def activities_list(request):
    return render(request, 'admin_panel/activities/list.html', {'dev_mode': _dev_mode()})


@guide_required
def guests_list(request):
    return render(request, 'admin_panel/guests/list.html', {'dev_mode': _dev_mode()})


@guide_required
def guides_list(request):
    return render(request, 'admin_panel/guides/list.html', {'dev_mode': _dev_mode()})


# Stub views for URL reverse() to work in templates
@guide_required
def tour_create(request):
    return render(request, 'admin_panel/tours/list.html', {'tours': [], 'dev_mode': _dev_mode()})


@guide_required
def tour_detail(request, pk):
    from django.shortcuts import get_object_or_404
    tour = get_object_or_404(Tour, pk=pk)
    return render(request, 'admin_panel/tours/list.html', {'tours': [tour], 'dev_mode': _dev_mode()})


@guide_required
def tour_edit(request, pk):
    from django.shortcuts import get_object_or_404
    tour = get_object_or_404(Tour, pk=pk)
    return render(request, 'admin_panel/tours/list.html', {'tours': [tour], 'dev_mode': _dev_mode()})


@guide_required
def tour_delete(request, pk):
    from django.shortcuts import get_object_or_404
    from django.http import HttpResponse
    tour = get_object_or_404(Tour, pk=pk)
    if request.method in ('POST', 'DELETE'):
        tour.delete()
        return HttpResponse('')
    return HttpResponse(status=405)


@guide_required
def tour_qr(request, pk):
    from django.shortcuts import get_object_or_404
    tour = get_object_or_404(Tour, pk=pk)
    return render(request, 'admin_panel/tours/list.html', {'tours': [tour], 'dev_mode': _dev_mode()})
