import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from telegraph import upload_file
from utils import get_file_id

@Client.on_message(filters.private & (filters.command("telegraph") | filters.photo))
async def telegraph_upload(bot, message):
    replied = message.reply_to_message
    if not replied:
        await message.reply_text("⚠️ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴘʜᴏᴛᴏ ᴏʀ ᴠɪᴅᴇᴏ ᴜɴᴅᴇʀ 5 ᴍʙ")
        return
    file_info = get_file_id(replied)
    if not file_info:
        await message.reply_text("⁉️ ɴᴏᴛ sᴜᴘᴘᴏʀᴛᴇᴅ 😑")
        return
    text = await message.reply_text(text="<code>ᴘʀᴏᴄᴇssɪɴɢ....</code>")   
    media = await message.reply_to_message.download()  
    try:
        response = upload_file(media)
    except Exception as e:
        await text.edit_text(text=f"Error :- {e}")
        return    
    try:
        os.remove(media)
    except:
        pass
    await text.delete()
    await message.reply_photo(
        photo=f'https://telegra.ph/{response[0]}',
        caption=f"<b>❤️ ʏᴏᴜʀ ᴛᴇʟᴇɢʀᴀᴘʜ ʟɪɴᴋ ᴄᴏᴍᴘʟᴇᴛᴇᴅ 👇</b>\n\n<code>https://telegra.ph/{response[0]}</code></b>",       
        reply_markup=InlineKeyboardMarkup(
          [[
            InlineKeyboardButton(text="✅ ᴏᴘᴇɴ ʟɪɴᴋ ✅", url=f"https://telegra.ph/{response[0]}"),
            InlineKeyboardButton(text="🔁 sʜᴀʀᴇ ʟɪɴᴋ 🔁", url=f"https://telegram.me/share/url?url=https://telegra.ph/{response[0]}")
          ],[
            InlineKeyboardButton(text="❌ ᴄʟᴏsᴇ ❌", callback_data="close_data")
          ]]
        )
    )

