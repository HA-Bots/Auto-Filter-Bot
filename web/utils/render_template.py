from info import BIN_CHANNEL, URL
from utils import temp
from web.utils.custom_dl import TGCustomYield
from utils import get_size
import urllib.parse
import secrets
import mimetypes
import aiofiles
import logging
import aiohttp


async def media_watch(message_id):
    media_msg = await temp.BOT.get_messages(BIN_CHANNEL, message_id)
    file_properties = await TGCustomYield().generate_file_properties(media_msg)
    file_name, mime_type = file_properties.file_name, file_properties.mime_type
    src = urllib.parse.urljoin(URL, f'download/{message_id}')
    tag = mime_type.split('/')[0].strip()
    if tag == 'video':
        async with aiofiles.open('web/template/watch.html') as r:
            heading = 'Watch - {}'.format(file_name)
            html = (await r.read()).replace('tag', tag) % (heading, file_name, src)
    else:
        html = '<h1>This is not streamable file</h1>'
    return html
