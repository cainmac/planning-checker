from django.conf import settings
from django.db import models
from django.utils import timezone

class Portal(models.TextChoices):
    RIGHTMOVE = "rightmove", "Rightmove"
    ZOOPLA = "zoopla", "Zoopla"

class AlertFrequency(models.TextChoices):
    INSTANT = "instant", "Instant"
    DAILY = "daily", "Daily digest"
    OFF = "off", "Off"

class SavedSearch(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    portal = models.CharField(max_length=20, choices=Portal.choices)
    criteria = models.JSONField(default=dict)  # beds_min, price_max, keywords, etc.
    portal_search_url = models.URLField(blank=True)
    alert_frequency = models.CharField(
        max_length=20, choices=AlertFrequency.choices, default=AlertFrequency.INSTANT
    )
    created_at = models.DateTimeField(auto_now_add=True)

class Listing(models.Model):
    portal = models.CharField(max_length=20, choices=Portal.choices)
    canonical_url = models.URLField(unique=True)

    title = models.CharField(max_length=255, blank=True)
    address = models.CharField(max_length=255, blank=True)
    postcode = models.CharField(max_length=16, blank=True)

    price = models.IntegerField(null=True, blank=True)
    bedrooms = models.IntegerField(null=True, blank=True)
    bathrooms = models.IntegerField(null=True, blank=True)

    first_seen = models.DateTimeField(default=timezone.now)
    last_seen = models.DateTimeField(default=timezone.now)

    raw_source = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

class SearchMatch(models.Model):
    saved_search = models.ForeignKey(SavedSearch, on_delete=models.CASCADE)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE)
    matched_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("saved_search", "listing")

class ShortlistItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    listing = models.ForeignKey(Listing, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("user", "listing")

