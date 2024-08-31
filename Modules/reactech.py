"""
Dynamic reaction general-use function to interract neatly with user.
Command uses eval() -> Be careful with usage.
Consider subfunctions for regularly-used cases.
"""



##################################################
# IMPORTS
##################################################



import discord as DSC
from discord.ext.commands import Bot as Bot
from discord.ext.commands.context import Context as CTX

from asyncio import TimeoutError, run

from Modules.discord_utils import DscConverter



##################################################
# CLASS
##################################################



class Reactech:
    """Dynamic reaction general-use function to interract neatly with user."""
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.converter = DscConverter(bot)



##################################################
# FUNCTIONS
##################################################



    async def reactech(self, ctx: CTX, emoji: str, react: bool = True,
                    recursive: int = -1, timeout: int = 3600, cond: str = None,
                    method: str = "pass", *args) -> None:
        """
        Configure and execute a dynamic reaction event handler. Example usage :
        await Reactech.reactech(ctx, "👍", True, 10, 300, "1+1==2", "msg.channel.send('Hello World !')")
        > will send 'Hello World !' in the channel if any user reacts with 👍 and 1+1==2.
        > will expire after 300 seconds or 10 messages.
        """
        # Ensure the msg object is actually a message
        msg = self.converter.convertobj(ctx, "message")
        # Add the reaction if needed
        if react: await msg.add_reaction(emoji)
        
        # Here the Bot waits for a reaction add that matches (check)
        def check(reaction: DSC.Reaction, user: DSC.User) -> bool:
            return (msg == reaction.message # On the current message
                    and emoji == reaction.emoji # With specified emoji
                    and user != self.bot.user # Reaction does not orriginate from the bot
                    and (not cond # And, if specified, checking another condition
                    or eval(cond, globals(), locals()|{"ctx": ctx, "emoji": emoji})))
        # Default unzip, these variables can be used in 'method'
        try: reaction, user = await self.bot.wait_for("reaction_add", check = check, timeout = timeout)
        except TimeoutError:
            pass # Timeout is expected
        except Exception as e:
            print(e)
            raise e
        
        else: # Activates on valid reaction
            await eval(method, globals(), locals())
            # Able to repeat this process until Bot disconnect
            if recursive != 0: # Apply recursively
                await self.reactech(msg, emoji, False, recursive-1,
                                timeout, cond, method, *args)
                # recursive = -1 means this value never reaches 0, so applies infinitely
                # Despite this, the value is still decremented and in local scope
                # Meaning it can still be used in 'cond' or 'method' to count executions



##################################################
# SUBFUNCTIONS
##################################################



    async def reactech_user(self, ctx: CTX, emoji: str, txt: str) -> None:
        """Per user, recursive, 15 min."""
        await self.reactech(ctx, emoji, True, -1, 900, None, "user.send(*args)", txt)


    async def reactech_channel(self, ctx: CTX, emoji: str, txt: str) -> None:
        """Once in channel then per user, recursive, 1h."""
        func =  "msg.reply(*args, mention_author = False) " + \
                "if recursive == -1 else " + \
                "user.send(*args)"
        await self.reactech(ctx, emoji, True, -1, 3600, None, func, txt)

    async def reactech_valid(self, ctx: CTX, txt: str) -> None:
        """reactech_channel with auto ✅."""
        await self.reactech_channel(ctx, "✅", txt)



##################################################
# MAIN
##################################################



if __name__ == "__main__":
    pass