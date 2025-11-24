import re

from django.core.mail import send_mail
from django.conf import settings
from django.core.paginator import Paginator
from django.shortcuts import render, redirect

from .forms import AddressSearchForm, WatchForm
from .scrapers import ealing, croydon

from .models import PlanningWatch
from django.contrib.auth.decorators import login_required


SCRAPERS = {
    "ealing": ealing.scrape,
    "croydon": croydon.scrape,
}

BOROUGH_LABELS = {
    "ealing": "London Borough of Ealing",
    "croydon": "London Borough of Croydon",
}


def detect_borough_from_text(text: str):
    """
    Postcode + keyword-based borough detection.
    Currently supports Ealing & Croydon.
    """
    t = text.upper()

    # 1) Try to detect a full UK postcode first (e.g. UB6 8JF, CR0 6YL)
    m = re.search(r"\b([A-Z]{1,2}\d[A-Z\d]?)\s*\d[A-Z]{2}\b", t)
    outward = m.group(1) if m else None  # e.g. UB6, W5, CR0, CR7

    outward_to_borough = {
        # Ealing postcodes
        "UB1": "ealing",
        "UB2": "ealing",
        "UB5": "ealing",
        "UB6": "ealing",
        "W3": "ealing",
        "W5": "ealing",
        "W7": "ealing",
        "W13": "ealing",
        # Croydon postcodes
        "CR0": "croydon",
        "CR2": "croydon",
        "CR4": "croydon",
        "CR7": "croydon",
        "CR8": "croydon",
    }

    borough_code = outward_to_borough.get(outward) if outward else None

    # 2) Fallback by looking for borough names in the text
    if borough_code is None:
        if "CROYDON" in t:
            borough_code = "croydon"
        elif "EALING" in t:
            borough_code = "ealing"

    borough_label = BOROUGH_LABELS.get(borough_code)
    return borough_code, borough_label


def _run_search(address: str):
    """Shared search logic used by both GET (pagination) and POST."""
    all_results = []
    error = None
    croydon_manual_url = None
    borough_code, borough_label = detect_borough_from_text(address)

    if not borough_code:
        error = (
            "Couldn't determine the borough from that postcode. "
            "Right now this tool supports Ealing (UB1, UB2, UB5, UB6, W3, W5, W7, W13) "
            "and Croydon (CR0, CR2, CR4, CR7, CR8)."
        )
    elif borough_code == "croydon":
        croydon_manual_url = "https://publicaccess3.croydon.gov.uk/online-applications/"
        error = (
            "The Croydon planning website blocks automated access, "
            "so results can't be shown here. "
            "Please use the Croydon public access site directly."
        )
    else:
        scrape_fn = SCRAPERS.get(borough_code)
        try:
            all_results = scrape_fn(address)
        except Exception as e:
            error = "There was an error contacting the borough planning system."
            print("SCRAPER ERROR:", repr(e))

    return all_results, borough_code, borough_label, error, croydon_manual_url


def planning_search(request):
    results_page = None
    error = None
    success = None
    borough_label = None
    last_query = None
    croydon_manual_url = None

    all_results = []

    # ----------------- POST: search or create alert -----------------
    if request.method == "POST":
        form = AddressSearchForm(request.POST)
        if form.is_valid():
            address = form.cleaned_data["address"].strip()
            last_query = address
            action = request.POST.get("action", "search")

            # run the search once; we reuse the data for both paths
            all_results, borough_code, borough_label, error, croydon_manual_url = _run_search(address)

            if action == "create_alert":
                # CREATE ALERT PATH
                if borough_code != "ealing":
                    error = "Alerts are currently only supported for Ealing postcodes."
                else:
                    # Save (or reuse) the watch
                    PlanningWatch.objects.get_or_create(
                        email="cain@bridgeparkcapital.co.uk",   # or later: form field
                        query=address,
                        borough_code=borough_code,
                        defaults={"active": True},
                    )

                    # Send confirmation email
                    send_mail(
                        subject="Planning alert set up",
                        message=(
                            f"A planning alert has been set up for '{address}' "
                            f"({borough_label})."
                        ),
                        from_email=getattr(
                            settings,
                            "DEFAULT_FROM_EMAIL",
                            "alerts@bridgeparkcapital.co.uk",
                        ),
                        recipient_list=["cain@bridgeparkcapital.co.uk"],
                        fail_silently=False,
                    )
                    success = (
                        f"Alert created for {address}. A confirmation email has been sent."
                    )

                # After creating alert, also run the search so results stay on screen
                if borough_code == "ealing":
                    all_results, borough_code, borough_label, error, croydon_manual_url = _run_search(address)

            # paginate for POST (both search + create_alert) if we have results and no fatal error
            if not error and all_results:
                paginator = Paginator(all_results, 20)
                results_page = paginator.get_page(1)

    # ----------------- GET: pagination / fresh page -----------------
    else:
        # If we're clicking a pagination link (?page=2&q=UB6+8JF)
        q = request.GET.get("q")
        page_number = request.GET.get("page", 1)

        if q:
            last_query = q
            all_results, borough_code, borough_label, error, croydon_manual_url = _run_search(q)

            if not error and all_results:
                paginator = Paginator(all_results, 20)
                results_page = paginator.get_page(page_number)

        # build the search form (prefill address if we have a query)
        if last_query:
            form = AddressSearchForm(initial={"address": last_query})
        else:
            form = AddressSearchForm()

    return render(
        request,
        "planning/search.html",
        {
            "form": form,
            "results_page": results_page,
            "error": error,
            "success": success,
            "borough_label": borough_label,
            "last_query": last_query,
            "croydon_manual_url": croydon_manual_url,
        },
    )

def create_watch(request):
    message = None

    if request.method == "POST":
        form = WatchForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            query = form.cleaned_data["query"].strip()

            borough_code, borough_label = detect_borough_from_text(query)

            if not borough_code:
                message = (
                    "Couldn't determine the borough from that postcode. "
                    "Right now alerts only support Ealing postcodes."
                )
            elif borough_code != "ealing":
                message = "Alerts are currently only enabled for Ealing."
            else:
                PlanningWatch.objects.create(
                    email=email,
                    query=query,
                    borough_code=borough_code,
                )
                return redirect("watch_thanks")
    else:
        # GET: pre-fill the query from ?q=...
        initial_query = request.GET.get("q", "")
        form = WatchForm(initial={"query": initial_query})

    return render(
        request,
        "planning/create_watch.html",
        {"form": form, "message": message},
    )

def watch_thanks(request):
    return render(request, "planning/watch_thanks.html")

@login_required
def watch_list(request):
    watches = PlanningWatch.objects.order_by("-created_at")
    return render(request, "planning/watch_list.html", {"watches": watches})
