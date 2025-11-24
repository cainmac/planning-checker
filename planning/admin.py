from django.contrib import admin
from .models import PlanningWatch

@admin.register(PlanningWatch)
class PlanningWatchAdmin(admin.ModelAdmin):
    list_display = ("email", "query", "borough_code", "active", "created_at")
    list_filter = ("borough_code", "active", "created_at")
    search_fields = ("email", "query")
