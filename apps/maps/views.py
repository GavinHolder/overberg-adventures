from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def map_screen(request):
    return render(request, 'app/map.html', {})
