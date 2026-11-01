from django.core.management.base import BaseCommand
from inventory.jobs import check_expiry_job


class Command(BaseCommand):
    help = "Manually triggers the automated product expiry check and sends Email, SMS & WhatsApp alerts."

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting manual product expiry check for Ohodo Retail Store..."))
        processed_count = check_expiry_job()
        self.stdout.write(
            self.style.SUCCESS(
                f"Done! Processed {processed_count} expired/expiring product(s) and logged alerts."
            )
        )