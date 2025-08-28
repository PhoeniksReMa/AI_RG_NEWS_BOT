import asyncio
import os
from aiogram import Bot
from aiogram.utils.media_group import MediaGroupBuilder
from .models import Theme, TargetChannel

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_TARGET_CHAT_ID = int(os.getenv("TELEGRAM_TARGET_CHAT_ID", "0"))

async def _send_text_async(data: dict, chat_id, parse_mode: str | None = "Markdown"):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    text=data.get('text')
    medias = data.get('media')
    mg = MediaGroupBuilder(caption=text)

    for media in medias:
        type = media.get("type")
        if type == "image":
            mg.add_photo(media=media.get('file_url'), parse_mode=parse_mode)
        elif type == "video":
            mg.add_video(media=media.get('file_url'), parse_mode=parse_mode)
        else:
            continue
    try:
        await bot.send_media_group(chat_id=chat_id, media=mg.build())
    finally:
        await bot.session.close()

def send_text(data: dict, theme,  parse_mode: str | None = "Markdown"):
    telegram_target_chat = TargetChannel.objects.filter(theme=theme)
    telegram_id_chat = [i.tg_id for i in telegram_target_chat]
    for chat_id in telegram_id_chat:
        asyncio.run(_send_text_async(data=data, parse_mode=parse_mode, chat_id=chat_id))
    return True