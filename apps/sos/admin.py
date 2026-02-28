from django.contrib import admin
from .models import SosConfig, EmergencyContact


@admin.register(SosConfig)
class SosConfigAdmin(admin.ModelAdmin):
    list_display = [
        'show_whatsapp_sos', 'show_sa_emergency_numbers',
        'show_gps_share', 'show_first_aid', 'show_emergency_contacts',
    ]


@admin.register(EmergencyContact)
class EmergencyContactAdmin(admin.ModelAdmin):
    list_display = ['name', 'role', 'phone', 'is_active', 'order']
    list_editable = ['is_active', 'order']
    ordering = ['order', 'name']
