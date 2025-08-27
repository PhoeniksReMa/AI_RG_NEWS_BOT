from celery import shared_task

from .services import refresh_tops_for_all_themes, fetch_recent_posts_for_top
from .bot_sender import send_text

import os
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)
load_dotenv()

POSTS_TOP_LIMIT = int(os.getenv("POSTS_TOP_LIMIT", "5"))
LOOKBACK_HOURS = int(os.getenv("POSTS_LOOKBACK_HOURS", "6"))

@shared_task(name="app.refresh_tops_daily")
def refresh_tops_daily():
    refreshed = refresh_tops_for_all_themes()
    logger.info(refreshed)
    return "tops refreshed"

@shared_task(name="app.fetch_and_publish_every_3h")
def fetch_and_publish_every_3h():
    data = fetch_recent_posts_for_top()
    send_text(data)
    logger.info(data)
    return "posts published"