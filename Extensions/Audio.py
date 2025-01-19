"""
Main handler for voice channel and audio interaction.
"""



##################################################
# IMPORTS
##################################################



import discord as DSC
from discord.ext import commands as CMDS
from discord.ext.commands.bot import Bot
from discord.ext.commands.context import Context as CTX

from Modules.reactech import Reactech
from Modules.discord_utils import DscConverter
from Modules.basic import mixmatch, plural


async def setup(bot: Bot):
    await bot.add_cog(Voice(bot))



##################################################
# VOICE
##################################################



class Voice(CMDS.Cog):
    """Voice interaction."""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.Reactech = Reactech(bot)
        self.DscConverter = DscConverter(bot)
    

    @CMDS.command(name = "join", aliases = mixmatch(["join", "connect", ""],
            ["", "vc", "voice", "vchannel", "voicechannel"], remove="join"))
    async def join(self, ctx: CTX, channel: str = None) -> bool:
        """Join the voice channel you are currently in (or the one specified)."""
        if ctx.guild is None:
            await self.Reactech.reactech_user(ctx, "🚫",
                "Command only works in servers.")
            return False
        
        if channel is None:
            if ctx.author.voice is None:
                await self.Reactech.reactech_user(ctx, "⁉️",
                    "No channel specified to join.")
                return False
            channel = ctx.author.voice.channel
        
        else: # resolve given channel
            try: channel = self.DscConverter.convertobj(channel, "voice", ctx)
            except TypeError: channel = None
            if channel is None:
                await self.Reactech.reactech_user(ctx, "❓",
                    "Could not find specified channel.")
                return False
            if not isinstance(channel, DSC.VoiceChannel):
                await self.Reactech.reactech_user(ctx, "🚫",
                    "The channel provided is not a voice channel.")
                return False

        if ctx.guild.voice_client is not None:
            if ctx.guild.voice_client.is_connected():
                await self.Reactech.reactech_user(ctx, "🚫",
                    "Bot is already in a voice channel on this server.")
                return False
        
        try:
            await channel.connect()
            await self.Reactech.reactech_valid(ctx,
                f"Joined voice channel {channel.mention}.")
        except DSC.Forbidden:
            await self.Reactech.reactech_user(ctx, "‼️",
                "Bot does not have the permission to join.")
        except Exception as e:
            await self.Reactech.reactech_user(ctx, "❌",
                f"`{e.__class__.__name__}`: {e}.")
        else: return True
        return False


    @CMDS.command(name = "leave", aliases = mixmatch(["quit", "leave", "disconnect", "dc"],
            ["", "vc", "voice", "vchannel", "voicechannel"], remove="leave"))
    async def leave(self, ctx: CTX) -> None:
        """Leave the voice channel the bot is in."""
        if ctx.guild is None:
            await self.Reactech.reactech_user(ctx, "🚫",
                "Command only works in servers.")
            return
        
        if not ctx.guild.voice_client is not None or \
            not ctx.guild.voice_client.is_connected():
                await self.Reactech.reactech_user(ctx, "🚫",
                    "Bot is not connected to a voice channel.")
                return
        
        try:
            channel = ctx.guild.voice_client.channel
            await ctx.guild.voice_client.disconnect()
            await self.Reactech.reactech_valid(ctx,
                f"Left voice channel {channel.mention}.")
        except Exception as e:
            await self.Reactech.reactech_user(ctx, "❌",
                f"`{e.__class__.__name__}`: {e}.")
    
    @CMDS.command(name = "voicechannels", aliases = mixmatch(["list", ""],
            ["vcs", "vchannels", "voicechannels"], remove="voicechannels")
            + mixmatch("list", ["vc", "voice", "vchannel", "voicechannel"]))
    @CMDS.is_owner()
    async def voicechannels(self, ctx: CTX, cmd: str = None) -> bool:
        """Count all voice channels the bot is currently connected to."""
        vcs = self.bot.voice_clients; msg = ""
        if cmd is None or cmd.lower() in ["l", "ls", "list", "c", "count"]:
            if len(vcs) == 0:
                await ctx.send("The bot is not connected to any voice channels.")
                return
            msg += f"The bot is connected to `{len(vcs)}` voice channel{plural(len(vcs))}."
            if cmd is not None and cmd.lower() in ["l", "ls", "list"]:
                for vc in vcs:
                    if ctx.guild and ctx.guild == vc.guild:
                        msg += f"\n- {vc.channel.mention} in '{vc.guild.name}'"
                    elif not ctx.guild and vc.guild.get_member(ctx.author.id):
                        msg += f"\n- '#{vc.channel.name}' in '{vc.guild.name}'"
                    else:
                        msg += f"\n- #{vc.channel.id} in {vc.guild.id}"
            await ctx.send(msg)
            return

        if cmd.lower() in ["q", "quit", "dc", "disconnect", "leave"]:
            success = 0; errors = {}
            for vc in vcs:
                try:
                    await vc.disconnect()
                    success += 1
                except Exception as e:
                    errors[vc] = e
            msg += f"Left `{success}` channel{plural(success)}."
            
            if len(errors) > 0:
                msg += f"Raised `{len(errors)}` error{plural(len(errors))}."
                for vc,e in errors.items():
                    msg += f"\n- #{vc.channel.id}: `{e.__class__.__name__}`: {e}"
            
            if ctx: await self.Reactech.reactech_valid(ctx, msg)
            else: print(msg.replace("`", ""))
            return
        
        await self.Reactech.reactech_user(ctx, "⁉️",
                f"Invalid or unknown command argument `{cmd}`.")



