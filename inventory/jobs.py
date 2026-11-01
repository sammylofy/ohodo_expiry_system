import logging
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution
from django_apscheduler import util
from .models import Product
from .alert_service import send_all_alerts

logger = logging.getLogger(__name__)
_scheduler_started = False


def check_expiry_job():
    """
    Finds all products with quantity > 0 and expiry_date <= today + 30 days
    and triggers multi-channel alerts (Email, SMS, WhatsApp).
    """
    today = timezone.localdate()
    threshold_date = today + timedelta(days=30)
    products_at_risk = Product.objects.filter(
        quantity__gt=0,
        expiry_date__lte=threshold_date
    ).order_by('expiry_date')

    count = 0
    for product in products_at_risk:
        send_all_alerts(product)
        count += 1

    logger.info("Automated expiry check completed. Dispatched alerts for %d products.", count)
    return count


@util.close_old_connections
def delete_old_job_executions(max_age=604_800):
    """Deletes APScheduler job execution logs older than 7 days (604,800 seconds)."""
    DjangoJobExecution.objects.delete_old_job_executions(max_age)


def start_scheduler():
    """Starts the BackgroundScheduler daily at 08:00 Africa/Lagos time."""
    global _scheduler_started
    if _scheduler_started or not getattr(settings, 'ENABLE_SCHEDULER', True):
        return

    try:
        scheduler = BackgroundScheduler(timezone=settings.TIME_ZONE)
        scheduler.add_jobstore(DjangoJobStore(), "default")

        scheduler.add_job(
            check_expiry_job,
            trigger=CronTrigger(hour="08", minute="00"),
            id="daily_product_expiry_check",
            max_instances=1,
            replace_existing=True,
        )

        scheduler.add_job(
            delete_old_job_executions,
            trigger=CronTrigger(day_of_week="mon", hour="00", minute="00"),
            id="delete_old_job_executions",
            max_instances=1,
            replace_existing=True,
        )

        scheduler.start()
        _scheduler_started = True
        logger.info("APScheduler started: Daily expiry check scheduled for 08:00 AM (Africa/Lagos).")
    except Exception as exc:
        logger.warning("Scheduler could not start yet (migrations may be pending): %s", exc)