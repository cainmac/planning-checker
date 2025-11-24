from django.db import models


class PlanningWatch(models.Model):
    email = models.EmailField()
    query = models.CharField(max_length=255, help_text="Address or postcode")
    borough_code = models.CharField(max_length=32)  # e.g. 'ealing'
    created_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    # store URLs of apps we've already seen, so we only alert on new ones
    seen_urls = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"{self.query} ({self.borough_code}) → {self.email}"
