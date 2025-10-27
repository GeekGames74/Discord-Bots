"""
Extension responsible for the bot api, webserver, callbacks, etc.
"""



##################################################
# IMPORTS
##################################################



import discord as DSC
from discord.ext import commands as CMDS
from discord.ext.commands.bot import Bot
from discord.ext.commands.context import Context as CTX

import asyncio
from aiohttp import web

from Modules.data import path_from_root
from Modules.reactech import Reactech
from Modules.basic import mixmatch
from Modules.Twitch.manager import TwitchManager


async def setup(bot: Bot):
    await bot.add_cog(Api(bot))



##################################################
# GLOBALS
##################################################



_APP = None
_RUNNER = None
_SITE = None
_TASK = None

_START = ["start", "run", "go", "serve", "launch", "spinup"]
_STOP = ["stop", "end", "halt", "terminate", "kill", "shutdown"]
_SERVER = ["api"] + mixmatch(["web", ""], ["server", "site", ""], keeporder=True)



##################################################
# API
##################################################



class Api(CMDS.Cog):
    """Serve the bot's API endpoints on designated port."""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.Reactech = Reactech(bot)
    

    async def cog_load(self):
        await self.start()

    
    async def cog_unload(self):
        await self.stop()

    
    @CMDS.command(name = "start_webserver", aliases = mixmatch(
        _START, _SERVER, remove="start_webserver"))
    @CMDS.is_owner()
    async def start_webserver(self, ctx: CTX) -> bool|None:
        """Start the webserver on the given port."""
        return await self.start(ctx)
    

    @CMDS.command(name = "stop_webserver", aliases = mixmatch(
        _STOP, _SERVER, remove="stop_webserver"))
    @CMDS.is_owner()
    async def stop_webserver(self, ctx: CTX) -> bool|None:
        """Stop the webserver."""
        return await self.stop(ctx)


    async def start(self, ctx: CTX = None) -> bool|None:
        """Start the webserver on the given port."""
        if self.bot.port is None: # Port is required to start
            if ctx: await self.Reactech.reactech_user(
                ctx, "❌", "Webserver port is not configured.")
            return False
        else: port = int(self.bot.port)
        global _APP, _RUNNER, _SITE, _TASK
        if _APP is not None:
            if ctx: await self.Reactech.reactech_user(
                ctx, "ℹ️", "Webserver is already running.")
            return None
        _APP = web.Application() # Create the app

        # Setup routes
        _APP.router.add_get('/', self.handle_root)
        _APP.router.add_get('/twitch', self.handle_twitch)

        # Runner
        _RUNNER = web.AppRunner(_APP)
        await _RUNNER.setup()
        # Create the site
        _SITE = web.TCPSite(_RUNNER, 'localhost', port)
        # Start and keep the task
        _TASK = asyncio.create_task(_SITE.start())
        if ctx: await self.Reactech.reactech_valid(
            ctx, f"Webserver started on port {port}.")
        else: print(f"Webserver started on port {port}.")
        return True


    async def stop(self, ctx: CTX = None) -> bool|None:
        """Stop the webserver."""
        global _APP, _RUNNER, _SITE, _TASK
        if _APP is None:
            if ctx: await self.Reactech.reactech_user(
                ctx, "ℹ️", "Webserver is not running.")
            return None
        _TASK.cancel()
        await _SITE.stop()
        await _RUNNER.cleanup()
        _APP = None ; _RUNNER = None
        _SITE = None ; _TASK = None
        if ctx: await self.Reactech.reactech_valid(
            ctx, "Webserver stopped.")
        else: print("Webserver stopped.")
        return True



##################################################
# ROUTES
##################################################



    async def handle_root(self, request: web.Request):
        return web.Response(text="Hello, World!")
    

    async def handle_twitch(self, request: web.Request):
        cog = self.bot.get_cog('Twitch_oauth')
        if cog is None:
            return web.Response(status=503, text="Twitch OAuth is not available on this bot (CogNotFound).")
        return await cog.handle_callback(request)



##################################################
# MAIN
##################################################



if __name__ == "__main__":
    pass