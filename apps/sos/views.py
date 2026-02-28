from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def sos_screen(request):
    return render(request, 'app/sos.html', {})
