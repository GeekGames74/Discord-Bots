"""
Manage Twitch API calls and features.
"""



##################################################
# IMPORTS
##################################################



from discord.ext.commands import Bot
from aiohttp import ClientSession, ClientResponse
from Modules.Twitch.user import TwitchUser
from Modules.Twitch.action import Action, ACTIONS



##################################################
# TWITCH MANAGER
##################################################



class TwitchManager:
    """Manage Twitch API calls and features."""
    def __init__(self, bot: Bot, client_id: str, client_secret: str) -> None:
        self.bot = bot # Discord bot instance
        # APP Twitch user, instantiated as such to use client credentials flow
        # check TwitchUser.refresh() override in user.py
        self.app = TwitchUser(
            twitch_id=client_id,
            refresh_token=client_secret,
            service="APP"
        )
        # Service account Twitch user (the bot's user)
        # Should be authenticated via OAuth2 with all scopes
        # Check Twitch.Twitch_oauth.twitch_login()
        self.user = None


    async def get_user(self) -> TwitchUser|None:
        """Get the Twitch user for the manager."""
        if self.user is None:
            # If not already set, try to get from DB
            self.user = await TwitchUser.get_from(self.bot.db, "discord_id", self.bot.user.id)
            # If sucessfully retreived, ensure its service property is set
            if self.user is not None: self.user.service = "BOT"
        if self.user is None:
            # If still None, create a new TwitchUser instance with bot's Discord ID
            self.user = TwitchUser(
                discord_id=str(self.bot.user.id),
                service="BOT"
            )
        return self.user


    @classmethod
    def get(cls, bot: Bot) -> 'TwitchManager':
        """Get the TwitchManager instance from the bot, if it exists."""
        return getattr(bot, 'twitch', None)
    

    @classmethod
    async def create(cls, bot: Bot, config: tuple = None) -> None:
        """Create and return a TwitchManager instance."""
        if config is None: return None
        # If config is a string, split by newlines
        if isinstance(config, str): config = config.split("\n")
        # Config must be a tuple/list of (client_id, client_secret)
        manager = cls(bot, config[0], config[1])
        bot.twitch = manager # Attach to bot instance


    async def execute_action(self, action: Action) -> ClientResponse:
        """Execute a Twitch Action via Helix API."""
        if isinstance(action.user, str):
            # If user is a Twitch ID string, get TwitchUser instance from DB
            action.user = await TwitchUser.get_from(self.bot.db, "twitch_id", action.user)
            if action.user is None:
                raise ValueError(f"Twitch user with ID '{action.user}' not found in database.")
        
        # Set default headers if not provided
        if "headers" in ACTIONS[action.type]:
            if action.headers is None:
                # Set required headers from action template
                action.headers = ACTIONS[action.type]["headers"]
            # Fill in Client-ID and Authorization if needed
            if "Client-ID" in action.headers:
                action.headers["Client-ID"] = self.app.twitch_id
            if "Authorization" in action.headers:
                if action.user is not None:
                    token = await action.user.get_token(self)
                else: # Use app token if no user specified
                    token = await self.app.get_token(self)
                if token is None:
                    raise ValueError("No valid OAuth token available for this action.")
                action.headers["Authorization"] = f"Bearer {token}"

        async with ClientSession() as session:
            async with session.request(action.method, action.url, headers=action.headers,
                    params=action.params, json=action.json) as resp:
                await resp.read() # Ensure response is read before returning
                # (This avoids issues with closed connections)
                return resp
    


##################################################
# MAIN
##################################################



if __name__ == "__main__":
    pass