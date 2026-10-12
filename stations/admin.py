from django.contrib import admin

from .models import FuelStop


@admin.register(FuelStop)
class FuelStopAdmin(admin.ModelAdmin):
    list_display = ("opis_id", "name", "city", "state", "retail_price", "lat", "lng")
    list_filter = ("state",)
    search_fields = ("name", "city", "address")
