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
    Отправляет текст и медиа:
    - фильтрует мусорные медиа (без file_url или с type не из {"image", "video"});
    - 0 медиа -> send_message;
    - 1 медиа -> send_photo/send_video с caption;
    - 2+ медиа -> send_media_group (caption на первый элемент).
    Возвращает список отправленных сообщений.
    """
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    sent: List[Message] = []

    text: str = data.get("text") or ""
    medias: list = data.get("media") or []

    # Оставляем только валидные элементы
    valid_medias = [
        m for m in medias
        if m.get("file_url") and m.get("type") in {"image", "video"}
    ]

    try:
        # 0 медиа -> просто текст
        if len(valid_medias) == 0:
            msg = await bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode)
            sent.append(msg)
            # если нужно логировать/сохранять и для текстов:
            await create_generated_post(text=text, theme=theme)
            return sent

        # 1 медиа -> отправляем отдельным сообщением
        if len(valid_medias) == 1:
            media = valid_medias[0]
            file_url = media["file_url"]
            kind = media["type"]

            if kind == "image":
                msg = await bot.send_photo(chat_id=chat_id, photo=file_url, caption=text, parse_mode=parse_mode)
            else:  # "video"
                msg = await bot.send_video(chat_id=chat_id, video=file_url, caption=text, parse_mode=parse_mode)

            sent.append(msg)
            await create_generated_post(text=text, theme=theme)
            return sent

        # 2+ медиа -> медиагруппа
        mg = MediaGroupBuilder(caption=text)
        for m in valid_medias:
            file_url = m["file_url"]
            kind = m["type"]
            if kind == "image":
                mg.add_photo(media=file_url, parse_mode=parse_mode)
            else:
                mg.add_video(media=file_url, parse_mode=parse_mode)

        group_msgs = await bot.send_media_group(chat_id=chat_id, media=mg.build())
        sent.extend(group_msgs)
        await create_generated_post(text=text, theme=theme)
        return sent

    finally:
        await bot.session.close()

def send_text(data: dict, theme,  parse_mode: str | None = "Markdown"):
    telegram_target_chat = TargetChannel.objects.filter(theme=theme)
    telegram_id_chat = [i.tg_id for i in telegram_target_chat]
    logger.info(f'send_text: {data}')
    for chat_id in telegram_id_chat:
        asyncio.run(_send_text_async(data=data, parse_mode=parse_mode, chat_id=chat_id, theme=theme))
    return True