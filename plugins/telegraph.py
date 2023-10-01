import os
from pyrogram import Client, filters
from telegraph import upload_file

@Client.on_message((filters.photo | filters.video) & filters.private)
async def telegraph_upload(bot, message):
    file = message.photo or message.video
    if file.file_size >= 5242880:
        await message.reply_text(text="Send less than 5MB")   
        return
    text = await message.reply_text(text="ᴘʀᴏᴄᴇssɪɴɢ....")   
    media = await message.download()  
    try:
        response = upload_file(media)
    except Exception as e:
        await text.edit_text(text=f"Error - {e}")
        return    
    try:
        os.remove(media)
    except:
        pass
    await text.edit_text(f"<b>❤️ ʏᴏᴜʀ ᴛᴇʟᴇɢʀᴀᴘʜ ʟɪɴᴋ ᴄᴏᴍᴘʟᴇᴛᴇᴅ 👇</b>\n\n<code>https://telegra.ph/{response[0]}</code></b>")

