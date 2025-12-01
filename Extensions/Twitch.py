"""
Twitch Extension for Discord Bot
"""



##################################################
# IMPORTS
##################################################



import discord as DSC
from discord.ext.commands import Cog
from discord.ext.commands.bot import Bot
from discord.ext import commands as CMDS
from discord.ext.commands.context import Context as CTX

from asyncio import TimeoutError, CancelledError
from aiohttp import web

from Modules.basic import mixmatch, least_one
from Modules.reactech import Reactech
from Modules.Twitch.manager import TwitchManager
from Modules.Twitch.action import Action
from Modules.Twitch.eventsub import EventSubManager
from Modules.Twitch.user import SCOPES, TwitchUser


async def setup(bot: Bot):
    await bot.add_cog(Twitch_oauth(bot))



##################################################
# GLOBALS
##################################################



_LOGIN = ["login", "log", "user", "username", "name", "id", "grant", "connect", "link", "auth", "authenticate", "signin", "signon", "attach"]
_LOGOUT = ["logout", "logoff", "revoke", "signout", "signoff", "disconnect"]
_LOGIN_WAIT_TIMEOUT = 600 # 10 minutes


def login_embed(user: TwitchUser, scopes: dict) -> DSC.Embed:
    """Generate an embed showing the login status and scopes."""
    amounts = user.get_scope_amount() # Get amount of scopes per category
    # Build the embed (color Twitch purple, current timestamp)
    embed = DSC.Embed(color=0x9146ff, timestamp=DSC.utils.utcnow())
    if user.login: # If logged in, show user info
        embed.set_author(
            name=user.login,
            icon_url=user.profile_image_url,
            url=f"https://twitch.tv/{user.login}"
        )
        embed.title = f"Currently logged-in as `{user.display_name}`."
    # If not logged in, show generic message
    else: embed.title = "The bot cannot access your Twitch account."
    description = "React to this message to enable scopes (optional), and ✅ to generate the login link.\n" + \
        f"Message expiry: <t:{int(DSC.utils.utcnow().timestamp()) + _LOGIN_WAIT_TIMEOUT}:R>.\n"

    for category in scopes.values(): # For each scope category
        # Update amount of scopes enabled in this category
        category['amount'] = amounts.get(category["name"], 0)
        # "## {emoji} **{name}** *({amount}/{total})*" 
        description += f"## {category['emoji']} **{category['name']}** *({category['amount']}/{len(category['scopes'])})*\n"
        description += f"{category['description']}\n"

        for scope in category["scopes"]: # For each scope
            # Scope is in bold if the user has already granted it
            has_scope = "**" if scope in user.scopes else ""
            # Scopes are in an unordered list and in code blocks
            description += f"- {has_scope}`{scope}`{has_scope}\n"
        
        if category.get("extends"): # If category also inherits
            # Add inherited categories as quoted text
            description += "> Includes all scopes from " + \
                ", ".join([f"**{ext}**" for ext in category['extends']]) + "\n"
    
    embed.description = description # Set the embed description
    return embed



##################################################
# TWITCH OAUTH
##################################################



class Twitch_oauth(Cog):
    """Handle Twitch login and token refresh."""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.Reactech = Reactech(bot)
        self.TwitchManager = TwitchManager.get(bot)
    

    @Cog.listener()
    async def on_ready(self):
        manager = EventSubManager.get(self.bot)
        # If an EventSubManager is present, start it
        if manager is not None: await manager.start()


    @CMDS.command(name = "twitch_login", aliases = mixmatch(
        _LOGIN, "twitch", remove="twitch_login"))
    async def twitch_login(self, ctx: CTX, *, args: str = "") -> None:
        """Perform Twitch login."""
        if ctx.guild is not None:
            return await self.Reactech.reactech_user(
                ctx, "🚫", "This command can only be used in DMs.")
        if self.TwitchManager is None:
            return await self.Reactech.reactech_user(
                ctx, "🚫", "Twitch integration is not enabled on this bot.")

        # Owner may use this command to login the service account
        if await self.bot.is_owner(ctx.author) and least_one(args, "⚙️🤖"):
            user = await self.TwitchManager.get_user()
        # Otherwise, get the user from the database
        else: user = await TwitchUser.get_from(self.bot.db, "discord_id", ctx.author.id)
        # If user is not found, create a new one
        if user is None: user = TwitchUser(discord_id = str(ctx.author.id))

        # If the command args include scope emojis,
        # skip the reaction selection process
        if least_one(args, [c['emoji'] for c in SCOPES.values()]):
            scopes = {k:v for k,v in SCOPES.copy().items() if v['emoji'] in args}
            message = ctx.message
        else: # No scope emojis provided, use reaction selection
            scopes = {k:v for k,v in SCOPES.copy().items() if not v.get("hidden")}  
            embed = login_embed(user, scopes) # Generate the embed
            message = await ctx.reply(embed=embed)

            for category in scopes.values(): # For each scope category
                # Add reaction only if not all scopes are already granted
                if category['amount'] < len(category['scopes']):
                    await message.add_reaction(category["emoji"])
            await message.add_reaction("✅")

            def check(reaction: DSC.Reaction, user: DSC.User) -> bool: # Check function
                return (reaction.message == message # Same message
                    and user == ctx.author # Same user
                    and reaction.emoji == "✅") # Checkmark emoji
                
            try: await self.bot.wait_for("reaction_add", # Wait for the checkmark reaction
                timeout = _LOGIN_WAIT_TIMEOUT, check = check)
            except TimeoutError: # On timeout, remove checkmark reaction and exit
                try: return await message.remove_reaction("✅", self.bot.user)
                except Exception: return
            except CancelledError: return
            # Once checkmark is added, remove it to indicate processing
            try: await message.remove_reaction("✅", self.bot.user)
            except Exception: pass
            
            # Fetch the message again to get up-to-date reactions
            try: message = await message.fetch()
            except Exception: return await self.Reactech.reactech_user(ctx,
                "❓", "Could not fetch the login message.")
            
            # Determine which scopes to keep based on reactions with at least 2 counts (bot and user)
            scopes = {k:v for k,v in scopes.items() if getattr(
                DSC.utils.get(message.reactions, emoji=v["emoji"]), "count", 0) >= 2}
        
        categories = set(scopes.keys()) # Determine all selected categories
        for category in list(categories): # For each selected category
            # Add extended categories as well
            categories.update(scopes[category].get("extends", []))
        user_scopes = set() # Final set of scopes to request
        for category in categories:
            # Add all scopes from each category
            user_scopes.update(SCOPES[category].get("scopes", []))
            if user.service == "BOT": # If bot service account
                # Also add hidden (unused) scopes
                user_scopes.update(SCOPES[category].get("hidden_scopes", []))

        # Message specifying that the last login request has been invalidated
        author = None if user.state is None else "The previously requested login has been cancelled."
        await user.create_state(self.bot.db) # Create new state and save to DB
        # Send the login URL using an embed
        # While discord limits message length to 2000 characters,
        # embed description supports up to 4096 characters,
        # ensuring the URL fits within that limit.
        url = user.oauth_url(self.TwitchManager.app.twitch_id, self.bot.port, user_scopes)
        link = f"Authorize the bot using this link: [id.twitch.tv/oauth2/authorize]({url})"
        link_embed = DSC.Embed( # Create the embed
            title="Twitch oAuth Login",
            # URL must be at most 2000 characters (discord limitation)
            url=url if len(url) <= 2000 else None,
            description=link,
            color=0x9146ff,
            timestamp=DSC.utils.utcnow()
        )
        if author is not None: link_embed.set_author(name=author)
        link_embed.set_footer(text="This link will expire in 10 minutes.")
        await message.reply(embed=link_embed)


    async def handle_callback(self, request: web.Request) -> web.Response:
        """Handle the OAuth callback from Twitch."""
        manager = TwitchManager.get(self.bot)
        if manager is None: # If no TwitchManager is present
            return web.Response(status=503, text="Twitch OAuth is not available on this bot (TwitchManager not found).")
        
        code = request.query.get("code")
        state = request.query.get("state")
        if not code or not state: # Check for missing code or state
            return web.Response(status=400, text="Missing code or state in the callback URL.")
        # Retrieve the user associated with the state
        user = await TwitchUser.get_from(self.bot.db, "state", state)
        if user is None: # If user is not found
            return web.Response(status=400, text="Invalid state parameter.")
        if user.discord_id == str(self.bot.user.id): # If the user is the bot account
            # Ensure we get the correct TwitchUser instance (by reference)
            user = await manager.get_user()
        
        # Split the state in discord_id:token:timestamp
        discord_id, token, timestamp = state.split(":")
        if discord_id != str(user.discord_id): # Check Discord ID match
            return web.Response(status=400, text="State does not match the Discord user.")
        # Check for expired login session
        if int(timestamp) + _LOGIN_WAIT_TIMEOUT < int(DSC.utils.utcnow().timestamp()):
            return web.Response(status=408, text="The login session has expired.")
        
        action = Action( # Exchange code for token
            type="oauth_token",
            json={
                "client_id": manager.app.twitch_id,
                "client_secret": manager.app.refresh_token,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": user.redirect_uri(self.bot.port)
            }
        )
        response = await manager.execute_action(action)
        if response.ok is False: # Token exchange failed
            return web.Response(status=response.status, text=response.reason)

        response = await response.json()
        # Store the token in the user object
        user._token = response.get("access_token")
        user.refresh_token = response.get("refresh_token")
        user._token_expiry = int(DSC.utils.utcnow().timestamp()) + response.get("expires_in", 0)
        user.scopes = set(response.get("scope", []))
        user.state = None # Clear state after use
        result = await user.update(manager)
        if result is False: # Saving the user failed
            return web.Response(status=500, text="Failed to get user information from Twitch.")

        # Send a DM to the user indicating successful login
        if str(self.bot.user.id) != str(user.discord_id):
            dsc_user = self.bot.get_user(int(user.discord_id))
            if dsc_user is not None:
                await dsc_user.send(f"✅ Successfully logged in to Twitch as `{user.display_name}`.")
        return web.Response(status=200, text="Login successful.")


    @CMDS.command(name = "twitch_logout", aliases = mixmatch(
        _LOGOUT, "twitch", remove="twitch_logout"))
    async def twitch_logout(self, ctx: CTX, *, args: str = "") -> None:
        """Perform Twitch logout."""
        # Owner may use this command to logout the service account
        if await self.bot.is_owner(ctx.author) and least_one(args, "⚙️🤖"):
            user = await self.TwitchManager.get_user()
        # Otherwise, get the user from the database
        else: user = await TwitchUser.get_from(self.bot.db, "discord_id", ctx.author.id)
        
        if user is None: return await self.Reactech.reactech_channel(
            ctx, "ℹ️", "You are not logged in to Twitch.")
        revoked = await user.delete(self.bot.db) # Delete the user from DB
        if revoked: return await self.Reactech.reactech_valid(
            ctx, "You have been logged out from Twitch.")
        else: return await self.Reactech.reactech_user(
            ctx, "❓", "An error occurred while logging you out from Twitch.")


    @CMDS.command(name = "twitch")
    async def twitch(self, ctx: CTX, *args) -> None:
        """Twitch-related commands."""
        if not args or args[0].lower() in _LOGIN:
            await self.twitch_login.callback(self, ctx, args=" ".join(args[1:]))
        elif args[0].lower() in _LOGOUT:
            await self.twitch_logout.callback(self, ctx, args=" ".join(args[1:]))
        else: await self.Reactech.reactech_user(ctx, "⁉️",
            "Invalid Twitch command. Use `twitch login` or `twitch logout`.")



##################################################
# MAIN
##################################################



if __name__ == "__main__":
    pass