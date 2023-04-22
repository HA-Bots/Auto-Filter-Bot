from pyrogram import Client, filters, enums
from info import INDEX_CHANNELS
from database.ia_filterdb import save_file

media_filter = filters.document | filters.video


@Client.on_message(filters.chat(INDEX_CHANNELS) & media_filter)
async def media(bot, message):
    print(message)
    """Media Handler"""

    media = getattr(message, message.media.value, None)
    print(media)

      #  if media.mime_type not in ['video/mp4', 'video/x-matroska']:  # Non .mp4 and .mkv files are skipped
         #   continue
       # if media is not None:
        #    print(media.mime_type)
        #    break
  #  else:
       # return

  #  media.file_type = file_type
  #  media.caption = msg.caption
 #   await save_file(media)
