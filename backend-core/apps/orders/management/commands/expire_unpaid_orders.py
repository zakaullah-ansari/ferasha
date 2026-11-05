"""Release the stock of orders that were never paid.

Run every few minutes: docker-compose runs it from the `scheduler` service;
in production a cron job or systemd timer calling this command does the same.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.orders.services import expire_unpaid_orders


class Command(BaseCommand):
    help = "Cancel orders left unpaid past UNPAID_ORDER_TTL_MINUTES and release their stock."

    def handle(self, *args, **options):
        expired = expire_unpaid_orders()
        if expired:
            noun = "order" if len(expired) == 1 else "orders"
            self.stdout.write(f"Cancelled {len(expired)} unpaid {noun}: {', '.join(expired)}")
