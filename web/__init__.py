# Credit - adarsh-goel

from aiohttp import web
from web.stream_routes import routes


web_app = web.Application()
web_app.add_routes(routes)
