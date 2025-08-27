from datetime import timedelta
from django.utils import timezone
from django.db.models import F, IntegerField, Value, ExpressionWrapper
from celery import shared_task
from .models import Theme, DailyTop, Channel, Post
from .openai_client import rewrite_post, moderate
from .bot_sender import send_text
import os
import logging

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

POSTS_TOP_LIMIT = int(os.getenv("POSTS_TOP_LIMIT", "5"))
LOOKBACK_HOURS = int(os.getenv("POSTS_LOOKBACK_HOURS", "6"))

def popularity_qs():
    # Пример метрики: score = views + 3*forwards (можно заменить на ERR, взвешивание и т.п.)
    return ExpressionWrapper(
        (F("views") + 3 * F("forwards")), output_field=IntegerField()
    )

@shared_task(name="tgstatapp.publish_popular_posts")
def publish_popular_posts():
    """
    1) Берём последний срез топов по темам.
    2) За последние N часов собираем посты этих каналов.
    3) Ранжируем по популярности, берём top-K.
    4) Рерайтим и отправляем в Telegram (с модерацией).
    """
    now = timezone.now()
    since = now - timedelta(hours=LOOKBACK_HOURS)

    # Список актуальных каналов из последнего среза по всем темам
    latest_top_channels = (
        DailyTop.objects
        .values("theme")
        .annotate(latest_date=F("as_of_date"))
        .values_list("theme", "latest_date")
    )
    logger.info(latest_top_channels)

    # Соберём usernames из последнего среза для каждой темы
    channels_usernames = set()
    for theme_id, _ in latest_top_channels:
        theme = Theme.objects.get(id=theme_id)
        latest = (
            DailyTop.objects.filter(theme=theme)
            .order_by("-as_of_date", "rank")
            .select_related("channel")
        )
        usernames = latest.values_list("channel__username", flat=True).distinct()
        channels_usernames.update(usernames)

    if not channels_usernames:
        return "no channels to process"

    posts = (
        Post.objects.filter(channel__username__in=list(channels_usernames),
                            published_at__gte=since)
        .annotate(score=popularity_qs())
        .order_by("-score", "-published_at")
    )[:POSTS_TOP_LIMIT]
    logger.info(posts)

    sent = 0
    for p in posts:
        title = p.channel.title or p.channel.username
        body = (p.text or "").strip()
        if not body:
            continue

        # Модерация исходника (опционально можно модерацию и на рерайт)
        if not moderate(body):
            continue

        rewritten = rewrite_post(title, body)

        # safety: короткая повторная модерация на финальный текст
        if not moderate(rewritten):
            continue

        # Отправляем
        header = f"<b>{title}</b>\n"
        footer = f"\n<i>Просмотры:</i> {p.views or 0} | <i>Репосты:</i> {p.forwards or 0}"
        send_text(header + rewritten + footer)
        sent += 1

    return f"published {sent} messages"
