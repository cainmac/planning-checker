import re
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .forms import SavedSearchForm
from .models import Listing, Portal, SavedSearch, ShortlistItem
from .services import notify_instant_matches

RIGHTMOVE_RE = re.compile(r"https?://www\.rightmove\.co\.uk/properties/\d+")
ZOOPLA_RE = re.compile(r"https?://www\.zoopla\.co\.uk/for-sale/details/\d+")

@login_required
def dashboard(request):
    return render(request, "property/dashboard.html")

@login_required
def search_list(request):
    searches = SavedSearch.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "property/search_list.html", {"searches": searches})

@login_required
def search_create(request):
    if request.method == "POST":
        form = SavedSearchForm(request.POST)
        if form.is_valid():
            form.save(user=request.user)
            return redirect("property:search_list")
    else:
        form = SavedSearchForm()
    return render(request, "property/search_form.html", {"form": form, "mode": "create"})

@login_required
def search_edit(request, pk):
    s = get_object_or_404(SavedSearch, pk=pk, user=request.user)
    if request.method == "POST":
        form = SavedSearchForm(request.POST, instance=s)
        if form.is_valid():
            form.save(user=request.user)
            return redirect("property:search_list")
    else:
        # For v1: just edit the model fields; criteria fields will appear blank unless you map them back.
        form = SavedSearchForm(instance=s)
    return render(request, "property/search_form.html", {"form": form, "mode": "edit"})

@login_required
def search_delete(request, pk):
    s = get_object_or_404(SavedSearch, pk=pk, user=request.user)
    if request.method == "POST":
        s.delete()
        return redirect("property:search_list")
    return render(request, "property/search_delete.html", {"search": s})

@login_required
def listings_inbox(request):
    qs = Listing.objects.all().order_by("-first_seen")

    portal = request.GET.get("portal")
    if portal:
        qs = qs.filter(portal=portal)

    beds_min = request.GET.get("beds_min")
    if beds_min:
        qs = qs.filter(bedrooms__gte=int(beds_min))

    baths_min = request.GET.get("baths_min")
    if baths_min:
        qs = qs.filter(bathrooms__gte=int(baths_min))

    price_max = request.GET.get("price_max")
    if price_max:
        qs = qs.filter(price__lte=int(price_max))

    shortlist_ids = set(
        ShortlistItem.objects.filter(user=request.user).values_list("listing_id", flat=True)
    )

    return render(request, "property/listings_inbox.html", {"listings": qs[:200], "shortlist_ids": shortlist_ids})

@login_required
def shortlist(request):
    items = ShortlistItem.objects.filter(user=request.user).select_related("listing").order_by("-created_at")
    return render(request, "property/shortlist.html", {"items": items})

@login_required
def shortlist_add(request, listing_id):
    listing = get_object_or_404(Listing, pk=listing_id)
    ShortlistItem.objects.get_or_create(user=request.user, listing=listing)
    return redirect("property:listings_inbox")

@login_required
def shortlist_remove(request, listing_id):
    ShortlistItem.objects.filter(user=request.user, listing_id=listing_id).delete()
    return redirect("property:shortlist")

@csrf_exempt
def inbound_email_webhook(request):
    # simple shared-secret auth (works fine behind Mailgun/SendGrid inbound parse)
    secret = request.headers.get("X-Inbound-Secret")
    expected = request.META.get("INBOUND_EMAIL_SECRET", "")
    if not expected or secret != expected:
        return HttpResponseForbidden("Forbidden")

    subject = request.POST.get("subject", "")
    body_plain = request.POST.get("body-plain", "") or request.POST.get("text", "")
    body_html = request.POST.get("body-html", "") or request.POST.get("html", "")
    text = body_plain or body_html or ""

    urls = set(RIGHTMOVE_RE.findall(text)) | set(ZOOPLA_RE.findall(text))
    new_listings = []

    for url in urls:
        portal = Portal.RIGHTMOVE if "rightmove.co.uk" in url else Portal.ZOOPLA
        listing, created = Listing.objects.get_or_create(
            canonical_url=url,
            defaults={
                "portal": portal,
                "first_seen": timezone.now(),
                "last_seen": timezone.now(),
                "raw_source": {"subject": subject},
            },
        )
        if created:
            new_listings.append(listing)
        else:
            listing.last_seen = timezone.now()
            listing.save(update_fields=["last_seen"])

    if new_listings:
        notify_instant_matches(new_listings)

    return JsonResponse({"ok": True, "found_urls": len(urls), "new": len(new_listings)})
