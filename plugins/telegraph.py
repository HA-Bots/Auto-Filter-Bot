import os
from pyrogram import Client, filters
from telegraph import upload_file

@Client.on_message(filters.private & filters.photo)
async def telegraph_upload(bot, message):
    text = await message.reply_text(text="<code>ᴘʀᴏᴄᴇssɪɴɢ....</code>")   
    media = await message.download()  
    try:
        response = upload_file(media)
    except Exception as e:
        await text.edit_text(text=f"Error :- {e}")
        return    
    try:
        os.remove(media)
    except:
        pass
    await text.edit_text(f"<b>❤️ ʏᴏᴜʀ ᴛᴇʟᴇɢʀᴀᴘʜ ʟɪɴᴋ ᴄᴏᴍᴘʟᴇᴛᴇᴅ 👇</b>\n\n<code>https://telegra.ph/{response[0]}</code></b>")

