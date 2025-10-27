"""
Twitch EventSub subscription manager.
"""



##################################################
# IMPORTS
##################################################



from discord.ext.commands import Bot
from websockets import connect as ws_connect, ConnectionClosed
import asyncio
from aiohttp import ClientResponse
from json import loads as json_loads
from Modules.data import data
from Modules.Twitch.manager import TwitchManager
from Modules.Twitch.action import Action
from Modules.Twitch.subscription import Subscription



##################################################
# GLOBALS
##################################################



_WS_URL = "wss://eventsub.wss.twitch.tv/ws"
_DATA_PATH = "Data/eventsub.json"



##################################################
# EVENTSUB MANAGER
##################################################



class EventSubManager(TwitchManager):
    """Manage Twitch EventSub subscriptions."""
    def __init__(self, bot: Bot, client_id: str, client_secret: str) -> None:
        super().__init__(bot, client_id, client_secret)
        self.wanted = {} # Saved subscriptions for persistence (key -> dict)
        self.active = {} # Currently active subscriptions (key -> helix)
        self._session_id = None
        self.task = None
        self.websocket = None
        self._lock = asyncio.Lock()
        self._backoff = 1 # Backoff time for reconnects
        self._stop = False # Flag to stop the manager


    @classmethod
    def get(cls, bot: Bot, enforce: bool = True) -> 'EventSubManager':
        """Get the EventSubManager instance from the bot, if it exists."""
        manager = getattr(bot, 'twitch', None) # bot.twitch
        # Check if the manager is an instance of EventSubManager
        if enforce and not isinstance(manager, cls): return None
        return manager


    async def _read_wanted(self, register: bool = True) -> None:
        """Load the wanted subscriptions from file and optionally register them."""
        # Retrieve wanted subscriptions from file (default {})
        self.wanted = data(_DATA_PATH, {}, str(self.bot.user.id), filenotfound=None)
        if register: await self.register_all()


    def _write_wanted(self) -> None:
        """Save the wanted subscriptions to file."""
        data(_DATA_PATH, self.wanted, str(self.bot.user.id), read_only=False)


    async def start(self, update: bool = True, register: bool = None) -> None:
        """Start the EventSub connection."""
        async with self._lock:
            # If no task is running, start it
            if self.task is None or self.task.done():
                # Save the running task in self.task
                self.task = asyncio.create_task(self._run())
        if register is None: register = update
        if update: await self._read_wanted(register=register)
    

    async def stop(self) -> None:
        """Stop the EventSub connection."""
        self._stop = True # Set the stop flag
        async with self._lock:
            # Cancel the running task if any
            if self.task and not self.task.done():
                self.task.cancel()
                try: await self.task # Await task cancellation
                except asyncio.CancelledError: pass
                self.task = None # Clear the task reference
            # Close the websocket if open
            if self.websocket:
                await self.websocket.close()
                # Clear the websocket reference
                self.websocket = None


    async def add_subscription(self, sub: Subscription, register: bool = True) -> ClientResponse|None:
        """Add a subscription to the wanted list and register it if connected."""
        async with self._lock:
            if self.websocket and self._session_id and register:
                response = await self._register_subscription(sub)
            else: response = None
            # Save updated wanted list to file (under bot's ID)
            if response is None or response.ok:
                await self._read_wanted(False) # Refresh wanted list
                self.wanted[sub.key] = sub.to_dict() # Add new subscription
                self._write_wanted()
            return response
    

    async def remove_subscription(self, sub: Subscription|str, unregister: bool = True) -> ClientResponse|None:
        """Remove a subscription from the wanted list and unregister it if connected."""
        async with self._lock:
            # Accept either a Subscription object or a key string
            if isinstance(sub, Subscription): key = sub.key
            else: key = str(sub)
            if key and self.websocket and unregister:
                response = await self._unregister_subscription(key)
            else: response = None
            if key in self.wanted and (response is None or response.ok):
                await self._read_wanted(False)
                del self.wanted[key] # Remove from wanted list
                # Save updated wanted list to file (under bot's ID)
                self._write_wanted()
        return response


    async def _register_subscription(self, sub: Subscription|str) -> ClientResponse|None:
        """Register a subscription with Twitch."""
        # Accept either a Subscription object or a key string
        if isinstance(sub, str): sub = self.wanted.get(sub)
        # Subscription not found or already registered
        if sub is None: return None
        if sub.key in self.active: return None
        # Get the Action to register the subscription
        action = sub.get_action(self._session_id)
        response = await self.execute_action(action)
        if response.ok is False: # Registration failed
            print(f"Failed to register subscription '{sub.key}': {response.reason}")
        else: # Registration succeeded
            result = await response.json() # Parse JSON response
            # The important data is in result['data'][0]
            data = result.get("data", [{}])[0]
            helix_id = data.get("id") # Helix ID assigned by Twitch
            self.active[sub.key] = helix_id # Save active subscription
            print(f"Registered subscription '{sub.key}' with Helix ID '{helix_id}'")
        return response


    async def _unregister_subscription(self, sub: Subscription|str) -> ClientResponse|None:
        """Unregister a subscription from Twitch."""
        # Accept either a Subscription object or a key string
        if isinstance(sub, str): sub = self.wanted.get(sub)
        # Subscription not found or not already registered
        if sub is None: return None
        if sub.key not in self.active: return None
        action = Action( # Create Action to remove subscription
            type = "eventsub_remove",
            params = {"id": sub.helix_id},
            user = sub.twitch_id
        )
        response = await self.execute_action(action)
        if response.ok is False: # Unregistration failed
            print(f"Failed to unregister subscription '{sub.key}': {response.reason}")
        else: # Unregistration succeeded
            del self.active[sub.key]
            print(f"Unregistered subscription '{sub.key}' with Helix ID '{sub.helix_id}'")
        return response


    async def register_all(self) -> None:
        """Update the subscriptions to match the wanted list."""
        async with self._lock:
            # Add: is in wanted but not in active
            to_add = [(key, sub) for key, sub in self.wanted.items() if key not in self.active]
            # Remove: is in active but not in wanted
            to_remove = [key for key in self.active.keys() if key not in self.wanted]
            for key in to_remove: # Remove unwanted subscriptions
                await self._unregister_subscription(key)
            if self._session_id: # Register new subscriptions
                for key, sub in to_add:
                    await self._register_subscription(Subscription.from_dict(sub))
            else: pass


    async def _listen(self) -> None:
        """Listen to websocket messages: capture session id, notifications and dispatch to handlers."""
        async for raw in self.websocket:
            try: msg = json_loads(raw)
            except Exception: continue

            payload = msg.get("payload") or {}
            session = payload.get("session") or {}
            session_id = session.get("id")
            if session_id and session_id != self._session_id:
                # Update session ID and re-register subscriptions
                self._session_id = session_id
                await self.register_all()
            
            metadata = msg.get("metadata") or {}
            message_type = metadata.get("message_type")
            if message_type == "notification":
                event = payload.get("event") or {}
                subscription = payload.get("subscription") or {}
                helix_id = subscription.get("id")
                # Find the corresponding active subscription
                for key, id in self.active.items():
                    if id == helix_id:
                        sub_dict = self.wanted.get(key)
                        if sub_dict:
                            sub = Subscription.from_dict(sub_dict)
                            # Dispatch event to subscription handlers
                            await sub.handle(self.bot, event)
                            break
                else: print(f"Received notification for unknown subscription ID '{helix_id}'")


    async def _run(self) -> None:
        """Main loop to maintain the WebSocket connection and handle events."""
        print("EventSubManager started.")
        while True: # Run forever until stopped
            try: # Connect to Twitch EventSub WebSocket
                async with ws_connect(_WS_URL) as ws:
                    self.websocket = ws
                    await self._listen()
            # Handle connection closed or task cancelled
            except (ConnectionClosed, asyncio.CancelledError):
                if self._stop: # Flag is set: stop the manager
                    print("EventSubManager stopped.")
                    break
                # Otherwise, attempt to reconnect
            except Exception as e:
                if self._backoff > 1: # Only log on repeated errors
                    print(f"WebSocket error: {e}. Waiting {self._backoff}s.")
                await asyncio.sleep(self._backoff)
                self._backoff = min(self._backoff * 2, 300)
            else: self._backoff = 1 # Reset backoff on clean exit



##################################################
# MAIN
##################################################



if __name__ == "__main__":
    pass