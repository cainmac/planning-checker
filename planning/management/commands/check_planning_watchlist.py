from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

from planning.models import PlanningWatch
from planning.scrapers import ealing  # Croydon blocked, so we only monitor Ealing safely


class Command(BaseCommand):
    help = "Checks active planning watches and emails when new applications are found."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force-email-first-run",
            action="store_true",
            help="If last_seen is empty, still email results (default is NO email on first run).",
        )

    def handle(self, *args, **options):
        force_email_first_run = options["force_email_first_run"]

        qs = PlanningWatch.objects.filter(active=True).order_by("created_at")
        self.stdout.write(f"Checking {qs.count()} active watch(es)...")

        for watch in qs:
            if watch.borough_code != "ealing":
                self.stdout.write(f"Skip {watch.id} ({watch.borough_code}) - not supported for monitoring.")
                continue

            query = watch.query.strip()
            self.stdout.write(f"\nWatch #{watch.id}: {query}")

            # 1) Scrape current results
            results = ealing.scrape(query)

            # Use URL as stable unique ID for now
            seen_now = [r.get("url") for r in results if r.get("url")]
            seen_now_set = set(seen_now)

            seen_before = watch.last_seen_urls or []
            seen_before_set = set(seen_before)

            new_urls = list(seen_now_set - seen_before_set)

            # Update last checked
            watch.last_checked_at = timezone.now()

            # First run behaviour:
            # If we have no history yet, we store what exists and DO NOT email
            # (unless --force-email-first-run was provided)
            if not seen_before and not force_email_first_run:
                watch.last_seen_urls = list(seen_now_set)
                watch.save(update_fields=["last_seen_urls", "last_checked_at"])
                self.stdout.write("First run: stored baseline (no email sent).")
                continue

            if not new_urls:
                watch.last_seen_urls = list(seen_now_set)
                watch.save(update_fields=["last_seen_urls", "last_checked_at"])
                self.stdout.write("No new applications found.")
                continue

            # 2) Build email content for new applications only
            new_items = [r for r in results if r.get("url") in new_urls]

            lines = [
                f"New planning applications found for: {query}",
                "",
                f"Count: {len(new_items)}",
                "",
            ]

            for item in new_items:
                title = item.get("title", "Untitled")
                addr = item.get("address", "")
                url = item.get("url", "")
                lines.append(f"- {title}")
                if addr:
                    lines.append(f"  {addr}")
                if url:
                    lines.append(f"  {url}")
                lines.append("")

            subject = f"New planning applications: {query}"

            send_mail(
                subject=subject,
                message="\n".join(lines),
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "admin@astorholdings.com.au"),
                recipient_list=[watch.email],
                fail_silently=False,
            )

            # 3) Save updated snapshot so we don’t re-email the same items
            watch.last_seen_urls = list(seen_now_set)
            watch.save(update_fields=["last_seen_urls", "last_checked_at"])

            self.stdout.write(f"Emailed {watch.email} about {len(new_items)} new application(s).")
