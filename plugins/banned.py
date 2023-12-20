from pyrogram import Client, filters
from utils import temp
from pyrogram.types import Message
from database.users_chats_db import db
from info import SUPPORT_LINK
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

async def banned_users(_, __, message: Message):
    return (
        message.from_user is not None or not message.sender_chat
    ) and message.from_user.id in temp.BANNED_USERS

banned_user = filters.create(banned_users)

async def disabled_chat(_, __, message: Message):
    return message.chat.id in temp.BANNED_CHATS

disabled_group=filters.create(disabled_chat)

@Client.on_message(filters.private & banned_user & filters.incoming)
async def is_user_banned(bot, message):
    buttons = [[
        InlineKeyboardButton('Support Group', url=SUPPORT_LINK)
    ]]
    reply_markup=InlineKeyboardMarkup(buttons)
    ban = await db.get_ban_status(message.from_user.id)
    await message.reply(f'Sorry {message.from_user.mention},\nMy owner you are banned to use me! If you want to know more about it contact support group.\nReason - <code>{ban["ban_reason"]}</code>',
                        reply_markup=reply_markup)

@Client.on_message(filters.group & disabled_group & filters.incoming)
async def is_group_disabled(bot, message):
    buttons = [[
        InlineKeyboardButton('Support Group', url=SUPPORT_LINK)
    ]]
    reply_markup=InlineKeyboardMarkup(buttons)
    vazha = await db.get_chat(message.chat.id)
    k = await message.reply(
        text=f"<b><u>Chat Not Allowed</u></b>\n\nMy owner has restricted me from working here! If you want to know more about it contact support group.\nReason - <code>{vazha['reason']}</code>",
        reply_markup=reply_markup)
    try:
        await k.pin()
    except:
        pass
    await bot.leave_chat(message.chat.id)
