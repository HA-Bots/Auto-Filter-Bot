from pyrogram import Client, filters, enums
from info import INDEX_CHANNELS
from database.ia_filterdb import save_file

media_filter = filters.document | filters.video


@Client.on_message(filters.chat(INDEX_CHANNELS) & media_filter)
async def media(bot, message):
    print(f'mmm______{message}')
    """Media Handler"""
    media = getattr(message, message.media.value, None)
    print(media)
    if media.mime_type in ['video/mp4', 'video/x-matroska']:
        media.file_type = message.media.value
        media.caption = message.caption
        await save_file(media)
