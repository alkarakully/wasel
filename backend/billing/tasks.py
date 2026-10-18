from celery import shared_task

from .weeks import close_finished_weeks


@shared_task
def close_weeks():
    """Make last week's statements once Saturday comes; runs hourly and does nothing when up to date."""
    return len(close_finished_weeks())
