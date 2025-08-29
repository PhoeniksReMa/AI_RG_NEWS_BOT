import asyncio
import os
from typing import List, Optional
from aiogram.types import Message
from aiogram import Bot
from asgiref.sync import sync_to_async
from aiogram.utils.media_group import MediaGroupBuilder
from .models import TargetChannel, GeneratePost
import logging

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

@sync_to_async
def create_generated_post(text: str, theme) -> None:
    GeneratePost.objects.create(text=text, theme=theme)

async def _send_text_async(
    data: dict,
    chat_id: int,
    theme: Optional[str],
    parse_mode: Optional[str] = "Markdown",
) -> List[Message]:
    """
    Отправляет текст и (при наличии) медиагруппу.
    Фильтрует мусорные медиа: без file_url или с type не из {"image", "video"}.
    Возвращает список отправленных сообщений.
    """
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    sent_messages: List[Message] = []

    text: str = data.get("text") or ""
    medias: list = data.get("media") or []

    # Оставляем только валидные элементы
    valid_medias = [
        m for m in medias
        if m.get("file_url") and m.get("type") in {"image", "video"}
    ]

    try:
        # Если валидных медиа нет — отправляем просто текст
        if not valid_medias:
            msg = await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
            sent_messages.append(msg)

            await create_generated_post(text=text, theme=theme)

            return sent_messages

        # Есть валидные медиа — собираем медиагруппу
        mg = MediaGroupBuilder(caption=text)
        for media in valid_medias:
            kind = media.get("type")
            file_url = media.get("file_url")

            if kind == "image":
                mg.add_photo(media=file_url, parse_mode=parse_mode)
            elif kind == "video":
                mg.add_video(media=file_url, parse_mode=parse_mode)

        # На всякий случай проверим, что не получилось пусто
        if mg.count() == 0:
            # fallback на текст
            msg = await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
            sent_messages.append(msg)

            await create_generated_post(text=text, theme=theme)

            return sent_messages

        # Отправляем медиагруппу (вернётся список Message)
        group_msgs = await bot.send_media_group(chat_id=chat_id, media=mg.build())
        sent_messages.extend(group_msgs)

        await create_generated_post(text=text, theme=theme)

        return sent_messages

    finally:
        await bot.session.close()

def send_text(data: dict, theme,  parse_mode: str | None = "Markdown"):
    telegram_target_chat = TargetChannel.objects.filter(theme=theme)
    telegram_id_chat = [i.tg_id for i in telegram_target_chat]
    logger.info(f'send_text: {data}')
    for chat_id in telegram_id_chat:
        asyncio.run(_send_text_async(data=data, parse_mode=parse_mode, chat_id=chat_id, theme=theme))
    return True