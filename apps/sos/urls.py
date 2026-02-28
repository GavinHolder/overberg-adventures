from django.urls import path
from . import views

app_name = 'sos'
urlpatterns = [path('', views.sos_screen, name='sos')]
