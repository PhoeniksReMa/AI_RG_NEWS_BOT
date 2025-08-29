import json
from openai import OpenAI
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from .models import GeneratePost
import logging

logger = logging.getLogger(__name__)
client = OpenAI()

class NewsSource(BaseModel):
    id: str
    link: str
    channel_id: int
    views: Optional[int] = None


class NewsMedia(BaseModel):
    id: str
    type: Literal["video", "image", "none"]
    mime_type: Optional[str] = None
    file_url: Optional[str] = None


class NewsResult(BaseModel):
    title: str
    text_markdown: str
    sources: List[NewsSource]
    media: List[NewsMedia]


class NewsPost(BaseModel):
    mode: Literal["single", "combined"] = Field(description="single — выбран один источник; combined — объединение нескольких"
    )
    selected_ids: List[str]
    reason: str
    result: NewsResult

def generate_post_from_open_ai(posts_groups: list[list[dict]], theme) -> dict:
    """
    На вход: массив групп постов (как в вашем примере).
    На выход: строго типизированный dict с итоговой новостью/сводкой.
    """
    # 2) Инструкция + данные одной строкой (без input_json блоков!)
    guidelines = (
        "Ты — редактор-агрегатор. Тебе дан массив групп постов (каждая группа — посты нескольких каналов по одной теме).\n"
        "Поля: id, date (unix), views, link, channel_id, text (HTML/телеграм), media{type, mime_type, file_url, file_thumbnail_url}.\n\n"
        "Задача: вернуть РОВНО ОДИН материал:\n"
        "- mode: 'single' (лучший один пост) или 'combined' (объединение 2–4 постов).\n"
        "- Критерии отбора: свежесть (date), значимость (views), фактическая насыщенность, отсутствие дублей.\n"
        "- Рерайт: нейтрально и сжато (2–5 предложений или короткий список), HTML → Markdown, убрать рекламные хвосты типа «Подписаться…».\n"
        "- Ссылки сохраняй в Markdown. Медиа: file_url\n"
        "- Не повторяй предыдущие посты, если в них нет новых данных \n"
        "Ответ верни ТОЛЬКО вызовом функции emit_news (без обычного текста)."
    )

    # при желании можно подсократить вход (например, выкинуть большие поля), но здесь шлём как есть:
    payload_str = json.dumps(posts_groups, ensure_ascii=False)
    last_posts_objects = GeneratePost.objects.filter(theme=theme).order_by('-created_at')[:3]

    last_posts = [i.text for i in last_posts_objects]

    messages = [
        {"role": "system", "content": "Отвечай строго вызовом функции emit_news с корректным JSON."},
        {"role": "user", "content": f"{guidelines}\n\nВходные данные JSON:\n```json\n{payload_str}\n```\n\nПредыдущие посты: {last_posts} "}
    ]

    # 3) Вызов Chat Completions с tools
    resp = client.chat.completions.parse(
        model="gpt-5-mini",
        messages=messages,
        response_format=NewsPost
    )

    msg = resp.choices[0].message
    if not getattr(msg, "tool_calls", None):
        # Подстраховка: вдруг модель вернула текст
        content = (msg.content or "").strip()
        try:
            return json.loads(content)
        except Exception as e:
            raise RuntimeError(f"Модель не вызвала функцию и вернула не-JSON: {content[:500]}") from e

    # 4) Забираем аргументы функции — это наш строго типизированный JSON
    args = msg.tool_calls[0].function.arguments
    return json.loads(args)
