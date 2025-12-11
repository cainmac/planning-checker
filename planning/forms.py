from django import forms

BOROUGH_CHOICES = [
    ("ealing", "Ealing"),
    ("croydon", "Croydon"),
    # add more later
]
class AddressSearchForm(forms.Form):
    address = forms.CharField(
        label="Address or postcode",
        max_length=255,
        widget=forms.TextInput(
            attrs={
                "placeholder": "e.g. UB6 8JF or 249 Conway Crescent",
            }
        ),
    )

class PlanningWatchForm(forms.Form):
    address = forms.CharField(
        label="Address or postcode",
        max_length=255,
        widget=forms.TextInput(
            attrs={
                "placeholder": "e.g. UB6 8JF or 249 Conway Crescent",
            }
        ),
    )
    # If later you want per-user alerts, you can add an email field here.