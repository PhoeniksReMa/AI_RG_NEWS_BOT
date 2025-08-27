from datetime import timedelta
from django.utils import timezone
from django.db.models import F, IntegerField, ExpressionWrapper
from celery import shared_task
from django.db import transaction

from .services import refresh_tops_for_all_themes, fetch_recent_posts_for_top
from .models import Theme, DailyTop, Post
from .openai_client import rewrite_post, moderate
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

# def _popularity_expr():
#     return ExpressionWrapper(F("views") + 3 * F("forwards"), output_field=IntegerField())
#
# @shared_task(name="app.fetch_and_publish_every_3h")
# def fetch_and_publish_every_3h():
#     """
#     1) Тянем свежие посты для каналов из актуального топа и сохраняем в БД.
#     2) За последние N часов собираем непубликованные посты.
#     3) Ранжируем по популярности, берём top-K.
#     4) Модерация → рерайт → отправка в Telegram.
#     5) Помечаем пост как опубликованный (idempotency).
#     """
#     # Шаг 1: обновить посты в БД
#     fetch_recent_posts_for_top(store_in_db=True)
#
#     now = timezone.now()
#     since = now - timedelta(hours=LOOKBACK_HOURS)
#
#     # Вычисляем «актуальный топ» по всем темам (последний срез на дату)
#     themes = list(Theme.objects.all())
#     top_usernames = set()
#     for theme in themes:
#         latest = (
#             DailyTop.objects.filter(theme=theme)
#             .order_by("-as_of_date", "rank")
#             .select_related("channel")
#         )
#         # Берём ровно TOP_K каналов (как в .env) с верхнего среза
#         usernames = latest.values_list("channel__username", flat=True).distinct()
#         top_usernames.update(usernames)
#
#     if not top_usernames:
#         return "no channels in latest top"
#
#     # Шаг 2/3: выбираем непубликованные посты из последних N часов, ранжируем
#     posts_qs = (
#         Post.objects
#         .filter(
#             channel__username__in=list(top_usernames),
#             published_at__gte=since,
#             published_to_tg=False,     # не слать повторно
#         )
#         .annotate(score=_popularity_expr())
#         .order_by("-score", "-published_at")
#     )[:POSTS_TOP_LIMIT]
#
#     sent = 0
#     for p in posts_qs:
#         title = p.channel.title or p.channel.username
#         body = (p.text or "").strip()
#         if not body:
#             continue
#
#         # Базовая модерация исходного и финального текста
#         try:
#             if not moderate(body):
#                 continue
#             rewritten = rewrite_post(title, body)
#             if not rewritten or not moderate(rewritten):
#                 continue
#         except Exception as e:
#             # не сваливаем всю задачу из-за одного поста
#             continue
#
#         header = f"<b>{title}</b>\n"
#         footer = f"\n<i>Просмотры:</i> {p.views or 0} | <i>Репосты:</i> {p.forwards or 0}"
#
#         try:
#             msg_id = send_text(header + rewritten + footer)
#         except Exception:
#             # Отправка в TG могла упасть — просто пропустим
#             continue
#
#         # Отмечаем пост как опубликованный (idempotency)
#         with transaction.atomic():
#             # повторная проверка, если параллельно ещё один воркер отправил
#             post = Post.objects.select_for_update().get(pk=p.pk)
#             if not post.published_to_tg:
#                 post.published_to_tg = True
#                 post.published_to_tg_at = timezone.now()
#                 post.tg_message_id = msg_id
#                 post.save(update_fields=["published_to_tg", "published_to_tg_at", "tg_message_id"])
#                 sent += 1
#
#     return f"fetched+published: {sent}"