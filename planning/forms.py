from django import forms

BOROUGH_CHOICES = [
    ("ealing", "Ealing"),
    ("croydon", "Croydon"),
    # add more later
]

class AddressSearchForm(forms.Form):
    address = forms.CharField(
        max_length=255,
        label="Address or postcode",
        widget=forms.TextInput(attrs={
            "placeholder": "e.g. UB6 8JF or 249 Conway Crescent",
        }),
    )

class WatchForm(forms.Form):
    email = forms.EmailField()
    query = forms.CharField(
        max_length=255,
        label="Address or postcode",
        widget=forms.TextInput(attrs={
            "placeholder": "e.g. UB6 8JF",
        }),
    )