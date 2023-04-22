from pyrogram import Client, filters, enums
from info import INDEX_CHANNELS
from database.ia_filterdb import save_file

media_filter = filters.document | filters.video


@Client.on_message(filters.chat(INDEX_CHANNELS) & media_filter)
async def media(bot, message):
    """Media Handler"""
    for file_type in ("document", "video"):
        media = getattr(message, file_type, None)
        print(f'heyy{media}')
    print(f'hiii\n{media}')

    media.file_type = file_type
    media.file_type = file_type
    await save_file(media)
