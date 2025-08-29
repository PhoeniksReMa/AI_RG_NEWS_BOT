import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
from django.db import transaction
from .openai_client import generate_post_from_open_ai

from .models import Theme, SourceChannel, TargetChannel

from dotenv import load_dotenv

load_dotenv()

TGSTAT_TOKEN = os.getenv("TGSTAT_TOKEN")
TGSTAT_BASE_URL = os.getenv("TGSTAT_BASE_URL", "https://api.tgstat.ru")
TGSTAT_COUNTRY = os.getenv("TGSTAT_COUNTRY", "ru")

THEMES = [t.strip() for t in os.getenv("THEMES", "news,tech,finance").split(",") if t.strip()]
TOP_K = int(os.getenv("TOP_K", 5))
POSTS_PER_CHANNEL = int(os.getenv("POSTS_PER_CHANNEL", "3"))

class TGStatClient:
    def __init__(self):
        self._client = httpx.Client(
            base_url=TGSTAT_BASE_URL,
            timeout=15.0,
            headers={"User-Agent": "tgstat-worker/1.0"}
        )

    def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        p = {"token": TGSTAT_TOKEN, **params}
        r = self._client.get(path, params=p)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict) and data.get("ok") is False:
            raise RuntimeError(f"TGStat error: {data}")
        return data

    def search_channels(self, category_code: str, limit: int = 100) -> List[Dict[str, Any]]:
        data = self._get("/channels/search", {"category": category_code, "peer_type": "channel", "country": TGSTAT_COUNTRY, "limit": limit})
        return data.get("response").get("items")

    def get_posts(self, channel_id: str, start_time, hide_forwards: int = 1) -> List[Dict[str, Any]]:
        data = self._get("/channels/posts", {"channelId": channel_id, "startTime": start_time, "hideForwards": hide_forwards})
        return data.get("response").get("items")

@transaction.atomic
def refresh_tops_for_all_themes():
    client = TGStatClient()

    # берём именно коды тем (строки), а не объекты
    themes = Theme.objects.all()

    for theme in themes:
        code=theme.code
        items = client.search_channels(code, limit=100) or []
        top_channels = sorted(items, key=lambda x: x.get("ci_index") or 0, reverse=True)[:TOP_K]

        to_create: List[SourceChannel] = []
        usernames: List[str] = []

        for item in top_channels[:theme.channel_count]:
            usernames.append((item.get("username") or "").lstrip("@"))
            to_create.append(
                SourceChannel(
                    theme = theme,
                    tgstat_id=item.get("id"),
                    tg_id=item.get("tg_id"),
                    link=item.get("link"),
                    peer_type=item.get("peer_type"),
                    username=(item.get("username") or "").lstrip("@"),
                    title=item.get("title") or "",
                    about=item.get("about") or "",
                    image100=item.get("image100"),
                    image640=item.get("image640"),
                    participants_count=item.get("participants_count") or 0,
                    ci_index=item.get("ci_index") or 0.0,
                )
            )

        if to_create:
            SourceChannel.objects.filter(theme=theme).delete()
            SourceChannel.objects.bulk_create(to_create, ignore_conflicts=True)

    return list(
                SourceChannel.objects.all()
                .values(
                    "id", "tgstat_id", "tg_id", "link", "peer_type", "username",
                    "title", "about", "image100", "image640",
                    "participants_count", "ci_index", "created_at",
                )
            )

def fetch_recent_posts_for_top(theme):
    client = TGStatClient()

    objects = SourceChannel.objects.filter(theme=theme.id)
    posts_from_chanels = []
    for channel in objects:
        start_time = (datetime.now() - timedelta(hours=3))
        posts = client.get_posts(channel.tg_id, start_time=start_time)
        posts_from_chanels.append([post for post in posts])

    generate_json = generate_post_from_open_ai(posts_from_chanels)
    result = generate_json.get("result")
    text_markdown = result.get("text_markdown")
    media = result.get("media")
    mode = result.get("mode")
    return {
        'text': text_markdown,
        'media': media,
        'mode': mode
    }
