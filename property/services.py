from django.conf import settings
from django.core.mail import send_mail
from .models import Listing, SavedSearch, SearchMatch, AlertFrequency

def listing_matches(listing: Listing, criteria: dict) -> bool:
    beds_min = criteria.get("beds_min")
    if beds_min is not None and listing.bedrooms is not None and listing.bedrooms < beds_min:
        return False

    baths_min = criteria.get("baths_min")
    if baths_min is not None and listing.bathrooms is not None and listing.bathrooms < baths_min:
        return False

    price_min = criteria.get("price_min")
    if price_min is not None and listing.price is not None and listing.price < price_min:
        return False

    price_max = criteria.get("price_max")
    if price_max is not None and listing.price is not None and listing.price > price_max:
        return False

    keywords = criteria.get("keywords") or []
    hay = " ".join([listing.title or "", listing.address or ""]).lower()
    for kw in keywords:
        if kw and kw.lower() not in hay:
            return False

    return True

def notify_instant_matches(listings: list[Listing]) -> None:
    searches = SavedSearch.objects.select_related("user").all()

    for s in searches:
        if s.alert_frequency != AlertFrequency.INSTANT:
            continue

        for listing in listings:
            if listing.portal != s.portal:
                continue
            if not listing_matches(listing, s.criteria):
                continue

            match, created = SearchMatch.objects.get_or_create(saved_search=s, listing=listing)
            if not created:
                continue

            if not s.user.email:
                continue

            send_mail(
                subject=f"New property match: {s.name}",
                message=f"New listing matched:\n{listing.canonical_url}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[s.user.email],
                fail_silently=True,
            )
