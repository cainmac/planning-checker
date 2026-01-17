from django import forms
from .models import SavedSearch, Portal, AlertFrequency

class SavedSearchForm(forms.ModelForm):
    beds_min = forms.IntegerField(required=False, min_value=0)
    baths_min = forms.IntegerField(required=False, min_value=0)
    price_min = forms.IntegerField(required=False, min_value=0)
    price_max = forms.IntegerField(required=False, min_value=0)
    postcode = forms.CharField(required=False)
    radius_miles = forms.FloatField(required=False, min_value=0)
    keywords = forms.CharField(required=False, help_text="Comma-separated keywords")

    class Meta:
        model = SavedSearch
        fields = ["name", "portal", "portal_search_url", "alert_frequency"]

    def clean_keywords(self):
        s = self.cleaned_data.get("keywords", "")
        if not s:
            return []
        return [k.strip().lower() for k in s.split(",") if k.strip()]

    def save(self, commit=True, user=None):
        obj = super().save(commit=False)
        obj.criteria = {
            "beds_min": self.cleaned_data.get("beds_min"),
            "baths_min": self.cleaned_data.get("baths_min"),
            "price_min": self.cleaned_data.get("price_min"),
            "price_max": self.cleaned_data.get("price_max"),
            "postcode": (self.cleaned_data.get("postcode") or "").strip(),
            "radius_miles": self.cleaned_data.get("radius_miles"),
            "keywords": self.cleaned_data.get("keywords"),
            "status": "on_market",
        }
        obj.criteria = {k: v for k, v in obj.criteria.items() if v not in (None, "", [])}
        if user is not None:
            obj.user = user
        if commit:
            obj.save()
        return obj
