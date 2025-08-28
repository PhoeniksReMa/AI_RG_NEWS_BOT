from celery import shared_task

from .models import Theme
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
    try:
        refreshed = refresh_tops_for_all_themes()
        logger.info(f'refresh_tops_daily: {refreshed}')
    except Exception as e:
        logger.error(e)
    return "tops refreshed"

@shared_task(name="app.fetch_and_publish_every_3h")
def fetch_and_publish_every_3h():
    try:
        for theme in Theme.objects.all():
            data = fetch_recent_posts_for_top(theme)
            send_result = send_text(data, theme)
            logger.info(f'send_result:{send_result}, {data}')
    except Exception as e:
        logger.error(e)
    return "posts published"