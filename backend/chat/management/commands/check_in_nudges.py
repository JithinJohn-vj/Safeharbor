from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from chat.models import UserProgress
from chat.tools import send_sms_nudge


class Command(BaseCommand):
    help = (
        "Proactive scheduler: users with no message in 24h+ get an SMS nudge "
        "(if phone_e164 set and Twilio configured)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--hours",
            type=int,
            default=24,
            help="Inactive threshold (default 24)",
        )

    def handle(self, *args, **options):
        hours = options["hours"]
        cutoff = timezone.now() - timedelta(hours=hours)
        qs = UserProgress.objects.filter(
            last_message_at__isnull=False,
            last_message_at__lt=cutoff,
        ).select_related("session")

        n = 0
        for prog in qs:
            phone = prog.session.phone_e164
            if not phone:
                continue
            name = prog.session.display_name or "there"
            msg = (
                f"Hi {name}, it's SafeHarbor — just checking in. "
                f"Reply when you're ready; no pressure."
            )[:1400]
            send_sms_nudge(phone, msg)
            n += 1
            prog.last_message_at = timezone.now()
            prog.save(update_fields=["last_message_at", "updated_at"])

        self.stdout.write(self.style.SUCCESS(f"Processed {n} SMS nudge(s) (dry-run if Twilio unset)"))
