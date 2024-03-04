"""
Dynamic reaction general-use function to interract neatly with user.
Command uses eval() -> Be careful with usage.
Consider subfunctions for regularly-used cases.
"""


##########################################################################
# IMPORTS
##########################################################################



import discord as DSC
from discord.ext import commands as CMDS
from discord.ext.commands import Context as CTX

import asyncio

from dsc_converter import dsc_obj



##########################################################################
# Main function
##########################################################################



async def reactech(BOT: CMDS.bot, ctx, emoji: str, react: bool = True,
                   recursive: int = -1, timeout: int = 3600, cond: str = "True",
                   method: str = "pass", *args) -> None:
    """
    Configure and execute a dynamic reaction event handler. Example usage :
    await reactech(BOT, ctx, "👍", True, 10, 300, "1+1==2", f"msg.channel.send('Hello World !')")
    > will send 'Hello World !' in the channel if any user reacts with 👍 and 1+1==2.
    > will expire after 5 minutes or 10 messages.
    """
    msg = dsc_obj(BOT, ctx, "message")
    if react: await msg.add_reaction(emoji)
    
    # Here the Bot waits for a reaction add that matches (check)
    def check(reaction: DSC.Reaction, user: DSC.User) -> bool:
        return (msg == reaction.message
                and emoji == reaction.emoji and user != BOT.user
                and eval(cond, globals(), locals()|{"ctx": ctx, "emoji": emoji}))
    
    try: reaction, user = await BOT.wait_for("reaction_add",
                            check = check, timeout = timeout)
    except asyncio.TimeoutError: pass
    except Exception as e: raise e
    
    # If an user reacts, it executes the method
    else:
        await eval(method, globals(), locals())
        # Able to repeat this process until Bot disconnect
        if recursive != 0:
            await reactech(BOT, msg, emoji, False, recursive-1,
                            timeout, cond, method, *args)



##########################################################################
# REACTECH SUBFUNCTIONS
##########################################################################



async def rt_err(BOT: CMDS.bot, ctx, emoji: str, txt: str) -> None:
    """Error message. Per user, recursive, 5 min."""
    await reactech(BOT, ctx, emoji, True, -1, 900, "True", "user.send(*args)", txt)


async def rt_ok(BOT: CMDS.bot, ctx, txt: str) -> None:
    """Validation message. Once in channel then per user, recursive, 1h."""
    func =  "msg.channel.send(*args) \
             if recursive == -1 else \
             user.send(*args)"
    await reactech(BOT, ctx, "✅", True, -1, 3600, "True", func, txt)


async def rt_warn(BOT: CMDS.bot, ctx, txt: str) -> None:
    """Validation message. Once in channel then per user, recursive, 1h."""
    func =  "msg.channel.send(*args) \
             if recursive == -1 else \
             user.send(*args)"
    await reactech(BOT, ctx, "⚠️", True, -1, 1800, "True", func, txt)



