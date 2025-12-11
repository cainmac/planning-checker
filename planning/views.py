import re
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render

from .forms import AddressSearchForm
from .models import PlanningWatch
from .scrapers import ealing, croydon
from .tasks import send_planning_alert_email

logger = logging.getLogger(__name__)

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
    Very simple postcode-based borough detection.
    Currently supports common outward codes for Ealing and Croydon.
    """
    t = (text or "").upper()

    # basic UK postcode regex – we only care about the outward code (first bit)
    m = re.search(r"\b([A-Z]{1,2}\d[A-Z\d]?)\s*\d[A-Z]{2}\b", t)
    if not m:
        return None, None

    outward = m.group(1)  # e.g. UB6, W5, CR0, CR7

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

    borough_code = outward_to_borough.get(outward)
    borough_label = BOROUGH_LABELS.get(borough_code)
    return borough_code, borough_label


def _run_search(address: str):
    """
    Shared search logic used by planning_search (GET+POST).
    Returns:
        (all_results, borough_code, borough_label, error_message, croydon_manual_url)
    """
    all_results = []
    error = None
    croydon_manual_url = None

    borough_code, borough_label = detect_borough_from_text(address)

    if not borough_code:
        return (
            [],
            None,
            None,
            (
                "Couldn't determine the borough from that postcode. "
                "Right now this tool supports Ealing (UB1, UB2, UB5, UB6, "
                "W3, W5, W7, W13) and Croydon (CR0, CR2, CR4, CR7, CR8)."
            ),
            None,
        )

    # Croydon blocks automated access
    if borough_code == "croydon":
        return (
            [],
            "croydon",
            borough_label,
            (
                "The Croydon planning website blocks automated access, "
                "so results can't be shown here. "
                "Please use the Croydon public access site directly."
            ),
            "https://publicaccess3.croydon.gov.uk/online-applications/",
        )

    scrape_fn = SCRAPERS.get(borough_code)
    if not scrape_fn:
        return (
            [],
            borough_code,
            borough_label,
            "This borough is recognised but has no scraper configured.",
            None,
        )

    try:
        all_results = scrape_fn(address)
    except Exception as exc:
        logger.exception("SCRAPER ERROR: %r", exc)
        return (
            [],
            borough_code,
            borough_label,
            "There was an error contacting the borough planning system.",
            None,
        )

    return all_results, borough_code, borough_label, None, None


def planning_search(request):
    """
    Single page:
    - POST action=search -> run search
    - POST action=create_alert -> save watch + send email + re-run search (so results stay visible)
    - GET supports pagination using ?q=...&page=...
    """
    results_page = None
    error = None
    success = None
    borough_label = None
    last_query = None
    croydon_manual_url = None
    all_results = []

    if request.method == "POST":
        form = AddressSearchForm(request.POST)
        if form.is_valid():
            address = form.cleaned_data["address"].strip()
            last_query = address
            action = request.POST.get("action", "search")

            # 1) If user clicked "Create alert"
            if action == "create_alert":
                borough_code, borough_label = detect_borough_from_text(address)

                if borough_code != "ealing":
                    error = (
                        "Alerts are currently only supported for Ealing postcodes "
                        "(UB1, UB2, UB5, UB6, W3, W5, W7, W13)."
                    )
                else:
                    # Create/reuse watch
                    PlanningWatch.objects.get_or_create(
                        email="cain@bridgeparkcapital.co.uk",
                        query=address,
                        borough_code=borough_code,
                        defaults={"active": True},
                    )

                    # Send confirmation email (safe wrapper handles logging)
                    try:
                        send_planning_alert_email(
                            address=address,
                            borough_label=BOROUGH_LABELS.get(borough_code, "London Borough of Ealing"),
                            recipient_email="cain@bridgeparkcapital.co.uk",
                        )
                        success = f"Alert created for {address}. A confirmation email has been sent."
                    except Exception as exc:
                        logger.exception("Error sending alert email: %r", exc)
                        success = f"Alert created for {address}, but email failed to send."

                # Re-run search so results remain on screen
                (
                    all_results,
                    _code,
                    borough_label_from_search,
                    search_error,
                    croydon_manual_url,
                ) = _run_search(address)

                if borough_label_from_search:
                    borough_label = borough_label_from_search
                if not error and search_error:
                    error = search_error

            # 2) Normal search
            else:
                (
                    all_results,
                    _code,
                    borough_label,
                    error,
                    croydon_manual_url,
                ) = _run_search(address)

            if not error and all_results:
                paginator = Paginator(all_results, 20)
                results_page = paginator.get_page(1)

    else:
        # GET pagination: /planning/?q=UB6+8JF&page=2
        q = request.GET.get("q")
        page_num = request.GET.get("page", 1)

        if q:
            last_query = q
            (
                all_results,
                _code,
                borough_label,
                error,
                croydon_manual_url,
            ) = _run_search(q)

            if not error and all_results:
                paginator = Paginator(all_results, 20)
                results_page = paginator.get_page(page_num)

        # Keep the search input filled when paginating
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


@login_required
def watch_list(request):
    watches = PlanningWatch.objects.order_by("-created_at")
    return render(request, "planning/watch_list.html", {"watches": watches})


def watch_thanks(request):
    return render(request, "planning/watch_thanks.html")
