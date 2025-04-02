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

from asyncio import TimeoutError, CancelledError, run, gather

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
# REACTECH
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
                    and user != self.bot.user # Reaction does not originate from the bot
                    and (not cond # And, if specified, checking another condition
                    or eval(cond, globals(), locals()|{"ctx": ctx, "emoji": emoji})))
        # Default unzip, these variables can be used in 'method'
        try: reaction, user = await self.bot.wait_for("reaction_add", check = check, timeout = timeout)
        except (TimeoutError, CancelledError):
            pass # Timeout is expected, Cancelled is often called on bot shutdown
        except Exception as e: raise e
        
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
# USER_INPUT
##################################################



    async def user_input(self, ctx: CTX, emojis: str, default: str = None,
                            timeout: int = 300, cond: str = None) -> str:
            """
            Give the user a choice among several reactions, and return the chosen.
            On timeout, returns <default>, which is emojis[0] by default.
            """
            # Ensure the msg object is actually a message
            msg = self.converter.convertobj(ctx, "message")
            # Message cannot have more than 20 reactions
            if len(emojis) > 20:
                print("Warning: Cannot have more than 20 emojis here!")
                emojis = emojis[:20]
            gather(*[msg.add_reaction(e) for e in emojis])

            def check(reaction: DSC.Reaction, user: DSC.User) -> bool:
                return (msg == reaction.message # On the current message
                        and reaction.emoji in emojis # Among the emojis
                        and user != self.bot.user # Reaction does not orriginate from the bot
                        and (not cond # And, if specified, checking another condition
                        or eval(cond, globals(), locals()|{"ctx": ctx, "emojis": emojis})))
            # Default unzip, these variables can be used in 'method'
            try: reaction, user = await self.bot.wait_for("reaction_add", check = check, timeout = timeout)
            except TimeoutError:
                if default is not None: return default
                else: return emojis[0] # Default is the first emoji if not specified
            except Exception as e:
                raise e
            else: return reaction.emoji



##################################################
# SUBFUNCTIONS
##################################################



    async def react_confirm(self, ctx: CTX, false: str, true: str,
            txt: str, default: bool = False, timeout: int = 300) -> bool:
        """Creates a basic yes/no condition for the user to react.""" # TODO: Condition
        msg = await ctx.send(txt)
        choice = await self.user_input(msg, false+true, "default", timeout)
        if choice == "default": return default
        return choice == true



##################################################
# MAIN
##################################################



if __name__ == "__main__":
    pass