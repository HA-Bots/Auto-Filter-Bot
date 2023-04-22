from pyrogram import Client, filters, enums
from info import INDEX_CHANNELS
from database.ia_filterdb import save_file

media_filter = filters.document | filters.video


@Client.on_message(filters.chat(INDEX_CHANNELS) & media_filter)
async def media(bot, message):
    print(message)
    """Media Handler"""
    for file_type in ("document", "video"):
        media = getattr(message, file_type, None)
        print(media)
    print(f'hiii\n{media}')

    await save_file(media)
