"""
oauth helper functions for Twitch
"""



##################################################
# IMPORTS
##################################################



from time import time
from asyncpg import Pool
from urllib.parse import urlencode
from secrets import token_urlsafe
from Modules.data import data
from Modules.Twitch.action import Action



##################################################
# GLOBALS
##################################################



_OAUTH_URL = "https://id.twitch.tv/oauth2/authorize"
SCOPES = data("Resources/Files/Twitch/scopes.json", filenotfound = False)
REVERSE_SCOPES = {
    s: k for k, v in SCOPES.items() for s in
    v.get("scopes", []) + v.get("hidden_scopes", [])
}



##################################################
# TWITCH USER
##################################################



class TwitchUser:
    """Represent a Twitch user with OAuth token and related info."""
    def __init__(self, discord_id: str = None, twitch_id: str = None,
                 login: str = None, display_name: str = None,
                 token: str = None, refresh_token: str = None,
                 scopes: set[str] = None, state: str = None,
                 first_login: int = None, last_refresh: int = None,
                 token_expiry: int = None, profile_image_url: str = None,
                 service: str = "USER") -> None:
        self.discord_id = discord_id
        self.twitch_id = twitch_id

        self.login = login
        self.display_name = display_name

        self._token = token
        self.refresh_token = refresh_token

        self.scopes = scopes or set()
        self.state = state

        self.first_login = first_login or int(time())
        self.last_refresh = last_refresh or int(time())
        self._token_expiry = token_expiry

        self.profile_image_url = profile_image_url

        self.service = service


    async def get_token(self, TwitchManager) -> str|None:
        """Get a valid OAuth token, refreshing if needed."""
        # Refresh if expired or about to expire
        if self._token_expiry is None or time() >= self._token_expiry - 60:
            success = await self.refresh(TwitchManager)
            if success is False: return None
        # Validate if last refresh was over an hour ago
        if self.last_refresh is None or time() - self.last_refresh >= 3600:
            success = await self.validate(TwitchManager)
            if success is False: return None
        return self._token


    async def update(self, TwitchManager, save: bool = True) -> bool|None:
        """Update the user's data."""
        if self.service == "APP": return None
        if self._token is None: return False
        action = Action(
            type = "user",
            user = self
        )
        # Execute action to get user data
        response = await TwitchManager.execute_action(action)
        if response.ok is False: return False
        response = await response.json() # Parse JSON response
        user_data = response.get("data", [{}])[0] # Get user data
        # (data is a list of user info, we want the first entry)
        # Update user fields
        self.twitch_id = user_data.get("id", self.twitch_id)
        self.login = user_data.get("login", self.login)
        self.display_name = user_data.get("display_name", self.display_name)
        self.profile_image_url = user_data.get("profile_image_url", self.profile_image_url)
        self.last_refresh = int(time()) # Update last refresh time
        if save: return await self.save(TwitchManager.bot.db)
        return True


    async def refresh(self, TwitchManager, update: bool = True, save: bool = True) -> bool|None:
        """Refresh the user's OAuth token."""
        action = Action(
            # APP credential flow
            type = "client_credentials",
            params = {
                "client_id": TwitchManager.app.twitch_id,
                "client_secret": TwitchManager.app.refresh_token
            }
        ) if self.service == "APP" else Action(
            # USER/BOT refresh token flow
            type = "refresh_token",
            json = {
                "client_id": TwitchManager.app.twitch_id,
                "client_secret": TwitchManager.app.refresh_token,
                "refresh_token": self.refresh_token
            }
        )
        # Execute action to refresh token
        token_data = await TwitchManager.execute_action(action)
        if token_data.ok is False: return False

        token_data = await token_data.json() # Parse JSON response
        # Update token fields
        self._token = token_data.get("access_token", self._token)
        self.refresh_token = token_data.get("refresh_token", self.refresh_token)
        self._token_expiry = time() + token_data.get("expires_in", self._token_expiry)
        self.last_refresh = int(time()) # Update last refresh time
        if update: return await self.update(TwitchManager, save = save)
        elif save: return await self.save(TwitchManager.bot.db)
        return True
    

    async def validate(self, TwitchManager, refresh: bool = True,
                       update: bool = True, save: bool = True) -> bool|None:
        """Validate the user's OAuth token."""
        if self.service == "APP": return None
        if self._token is None: return False
        action = Action(
            type = "validate_token",
            headers={
                "Authorization": f"OAuth {self._token}"
            }
        )
        # Execute action to validate token
        validation_data = await TwitchManager.execute_action(action)
        if validation_data.ok is False: # Invalid token
            if refresh: # Try to refresh the token
                return await self.refresh(TwitchManager, update = update, save = save)
            return False
        else: self.last_refresh = int(time()) # Update last refresh time
        if update: return await self.update(TwitchManager, save = save)
        elif save: return await self.save(TwitchManager.bot.db)
        return True


    @classmethod
    async def get_from(cls, db: Pool, source: str, identifier: str) -> 'TwitchUser':
        """
        Get a Twitch user from the database.
        source: field to search by (discord_id, twitch_id, login, state)
        """
        # Source must be one of the valid fields
        if source not in {"discord_id", "twitch_id", "login", "state"}:
            raise ValueError(f"Invalid source '{source}'"
                f"Expected one of: discord_id, twitch_id, login, state")
        # Fetch user from database
        async with db.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT * FROM twitch WHERE {source} = $1", str(identifier)
            )
            if row is None: return None # User not found
            return cls(
                discord_id = row["discord_id"],
                twitch_id = row["twitch_id"],
                login = row["login"],
                display_name = row["display_name"],
                token = row["token"],
                refresh_token = row["refresh_token"],
                scopes = set(row["scopes"].split(" ")) if row["scopes"] else set(),
                state = row["state"],
                first_login = row["first_login"],
                last_refresh = row["last_refresh"],
                token_expiry = row["token_expiry"],
                profile_image_url = row["profile_image_url"]
            )
    

    async def save(self, db: Pool) -> bool|None:
        """Insert or update the user in the database."""
        if self.service == "APP": return None
        # Insert or update user in database
        async with db.acquire() as conn:
            result = await conn.execute(
                """
                INSERT INTO twitch (discord_id, twitch_id, login, display_name,
                    token, refresh_token, scopes, state, first_login,
                    last_refresh, token_expiry, profile_image_url)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                ON CONFLICT (discord_id) DO UPDATE SET
                    twitch_id = EXCLUDED.twitch_id,
                    login = EXCLUDED.login,
                    display_name = EXCLUDED.display_name,
                    token = EXCLUDED.token,
                    refresh_token = EXCLUDED.refresh_token,
                    scopes = EXCLUDED.scopes,
                    state = EXCLUDED.state,
                    first_login = EXCLUDED.first_login,
                    last_refresh = EXCLUDED.last_refresh,
                    token_expiry = EXCLUDED.token_expiry,
                    profile_image_url = EXCLUDED.profile_image_url
                """,
                self.discord_id,
                self.twitch_id,
                self.login,
                self.display_name,
                self._token,
                self.refresh_token,
                " ".join(self.scopes),
                self.state,
                self.first_login,
                self.last_refresh,
                self._token_expiry,
                self.profile_image_url
            )
            return result == "INSERT 0 1" or result == "UPDATE 1"


    async def delete(self, db: Pool) -> bool|None:
        """Delete the user from the database."""
        if self.service == "APP": return None
        # Delete user from database
        async with db.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM twitch WHERE discord_id = $1",
                str(self.discord_id)
            )
            return result == "DELETE 1"


    def get_scope_amount(self) -> dict[str, int]:
        """Get the amount of scopes per category."""
        if self.service == "APP": return {}
        # Default amount is 0 for each
        amounts = {c: 0 for c in SCOPES}
        for scope in self.scopes: # For every scope
            category = REVERSE_SCOPES.get(scope)
            if category: # If category is valid
                amounts[category] += 1 # Increment amount
        return amounts


    async def create_state(self, db: Pool = None) -> str|None:
        """Create and set a new state string for this user."""
        if self.service == "APP": return None
        # State format: discord_id:random_string:timestamp
        state = f"{self.discord_id}:{token_urlsafe(16)}:{int(time())}"
        self.state = state # Set new state
        # Save to database if provided
        if db: await self.save(db)
        return self.state
    

    @classmethod
    def redirect_uri(cls, port: str = None) -> str:
        """Get the redirect URI for OAuth."""
        domain = data("Secret/domain.json", # Get the domain from Secrets/
            {"name": "localhost", "ip": "127.0.0.1", "api": ":", "port": "6860"},
            filenotfound = None) # Default to localhost if not found
        # Determine protocol based on domain (localhost -> http, else https)
        protocol = "http" if domain["name"] == "localhost" or domain["ip"] == "127.0.0.1" else "https"
        # http[s]://domain:port/twitch
        return f"{protocol}://{domain['name']}{domain['api']}{port or domain['port']}/twitch"


    def oauth_url(self, client_id: str, port: str = None, scopes: set[str] = None) -> str|None:
        """Generate the OAuth URL for this user."""
        if self.service == "APP": return None
        if scopes is None: scopes = self.scopes
        params = { # Create the query parameters
            "client_id": client_id,
            "redirect_uri": self.redirect_uri(port),
            "response_type": "code",
            "scope": " ".join(scopes),
        }
        if self.state: # If state is set
            params["state"] = self.state
        # Build and return the full OAuth URL
        return f"{_OAUTH_URL}?{urlencode(params)}"
        


##################################################
# MAIN
##################################################



if __name__ == "__main__":
    pass