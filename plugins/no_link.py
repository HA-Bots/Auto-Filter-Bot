import os 
import pyrogram
from info import ADMINS
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.errors.exceptions.bad_request_400 import UserNotParticipant, MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty
import time
from datetime import datetime
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

@Client.on_message((filters.group) & (filters.regex("@")  | filters.regex("t.me") | filters.regex("https")))
async def nolink(bot,message):
	if message.from_user.id in ADMINS:
		return

	try:
              
                aks = await message.reply_text("<b>are you mad??\nwhy you send link in group 🤬</b>")
                await asyncio.sleep(60)      
                k = await aks.delete()
                await message.delete()
	except:
		return
