from django.db import models
from django.utils import timezone


class PlanningWatch(models.Model):
    email = models.EmailField()
    query = models.CharField(max_length=255)          # address or postcode
    borough_code = models.CharField(max_length=50)    # e.g. "ealing"
    active = models.BooleanField(default=True)

    last_seen_urls = models.JSONField(default=list, blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.query} ({self.borough_code}) → {self.email}"
