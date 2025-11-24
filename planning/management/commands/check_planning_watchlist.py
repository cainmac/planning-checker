from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.mail import send_mail

from planning.models import PlanningWatch
from planning.scrapers import ealing  # using your existing scraper
from planning.views import detect_borough_from_text  # OK here



class Command(BaseCommand):
    help = "Check planning applications for watched addresses and send alerts."

    def handle(self, *args, **options):
        watches = PlanningWatch.objects.filter(active=True)

        if not watches.exists():
            self.stdout.write("No active watches.")
            return

        for watch in watches:
            self.stdout.write(f"Checking watch: {watch}")

            # right now: only Ealing-supported
            if watch.borough_code != "ealing":
                self.stdout.write(f"Skipping {watch} (borough {watch.borough_code} not implemented).")
                continue

            try:
                apps = ealing.scrape(watch.query, max_pages=5)
            except Exception as e:
                self.stderr.write(f"Error scraping for {watch}: {e}")
                continue

            # identify new URLs
            seen = set(watch.seen_urls or [])
            new_apps = [a for a in apps if a["url"] not in seen]

            if not new_apps:
                self.stdout.write("No new applications.")
                continue

            # build email content
            subject = f"New planning application(s) for {watch.query}"
            lines = [
                f"The following new planning applications were found for {watch.query}:",
                "",
            ]
            for a in new_apps:
                lines.append(f"- {a['title']}")
                lines.append(f"  {a['address']}")
                lines.append(f"  {a['url']}")
                lines.append("")

            body = "\n".join(lines)
            from_email = getattr(settings, "EMAIL_FROM", "alerts@example.com")

            send_mail(
                subject,
                body,
                from_email,
                [watch.email],
                fail_silently=False,
            )

            # update seen URLs
            updated_seen = list(seen.union(a["url"] for a in new_apps))
            watch.seen_urls = updated_seen
            watch.save(update_fields=["seen_urls"])

            self.stdout.write(
                f"Sent {len(new_apps)} alert(s) to {watch.email} and updated seen URLs."
            )
