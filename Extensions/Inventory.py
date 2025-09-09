"""
Custom inventory model for discord servers, to run an item system.
"""



##################################################
# IMPORTS
##################################################



import discord as DSC
from discord.ext import commands as CMDS
from discord.ext.commands.bot import Bot
from discord.ext.commands.context import Context as CTX

from asyncio import gather

from Modules.data import data
from Modules.reactech import Reactech
from Modules.discord_utils import DscConverter
from Modules.basic import mixmatch



async def setup(bot: Bot):
    await bot.add_cog(Items(bot))



##################################################
# GLOBALS
##################################################



_LIMITS = {
    "numerical": 10**12,
    "name": 50,
    "description": 500,
}
_WORDS = ["inventory", "inv", "item", "items"]
_ALL = ["everyone", "all", "*"]
def is_help(arg: str) -> bool: return arg.lower() in ["help", "-h", "--help", "info", "information", "?"]
_INV_ACTIONS = {
    "view":    ["view", "check", "v"],
    "show":    ["show", "display"],
    "give":    ["give", "add", "grant", "g", "a", "+"],
    "remove":  ["remove", "delete", "take", "withdraw", "del", "r", "rm", "-"],
    "set":     ["set", "update", "change", "modify", "="],
    "clear":   ["clear", "empty", "reset"],
}
_ITEM_ACTIONS = {
    "create":  ["create", "new", "add", "c", "+"],
    "edit":    ["edit", "update", "change", "modify", "e"],
    "delete":  ["delete", "remove", "del", "d", "-"],
    "list":    ["list", "ls", "l"],
    "info":    ["info", "information", "i"],
}
_SERVER_DEFAULTS = {
    "items": {}, # "item_id": {item_data}
    "users": {}, # "user_id": {"item_id": quantity}
    "settings": {
        "slots": None, "capacity": None, "volume": None, "size": 1,
        "min": 0, "base": 0, "max": _LIMITS["numerical"],
        "fractions": 1, "strict": True, "secret": True
    },
    "permissions": # "action": [["can_self"], ["can_others"]]
        {act: [["administrator"], ["administrator"]] for act in _INV_ACTIONS}
        | {act: ["administrator"] for act in _ITEM_ACTIONS},
    "log": # "action": (channel_id, log_self)
        {act: (None, True) for act in list(_INV_ACTIONS.keys())}
        | {act: None for act in list(_ITEM_ACTIONS.keys())}
        | {"error": None, "deny": (None, True)},
}
_ITEM_DEFAULTS = {
    "name": None, "plural": None, "aliases": [], "emoji": None,
    "min": 0, "base": 0, "max": _LIMITS["numerical"],
    "fractions": 1, "size": 1, "id": None,
    "description": None, "image": None, "color": None
}



##################################################
# LOGGING
##################################################



async def log_channel(ctx: CTX, logs: dict, action: str, self: bool = False) -> DSC.TextChannel|None:
    """Log an action in the inventory log channel, if set."""
    if action not in logs: raise ValueError(f"Invalid action to log: '{action}'.")
    log = logs.get(action, (None, False))
    if not isinstance(log, (list, tuple)): log = (log, True)
    if not log[0] or (not self and not log[1]): return None
    channel = ctx.guild.get_channel(int(log[0]))
    if not channel:
        if action != "error":
            await inventory_log_error(ctx, logs,
                f"Log channel `<#{log[0]}>` for action `{action}` not found.")
            return None
        channel = ctx.channel
    return channel


def log_embed(ctx: CTX, action: str, title: str, description: str, user: DSC.User) -> DSC.Embed:
    """Create a basic embed for logging an action."""
    color = {
        "view": 0xffff00, "show": 0xffff00,
        "give": 0x00ff00, "remove": 0x00ff00,
        "set": 0x00ff00, "clear": 0x00ff00,
        "create": 0xffff00, "edit": 0xffff00, "delete": 0xffff00,
        "list": 0x0000ff, "info": 0x00ffff,
        "error": 0xff0000, "deny": 0xff00ff
    }.get(action, 0xffffff)
    embed = DSC.Embed(title=title, color=color, description=description,
        timestamp=ctx.message.created_at, url=ctx.message.jump_url)
    if user:
        author_icon = user.avatar.url if user.avatar else None
        embed.set_author(name=user.display_name, icon_url=author_icon)
    return embed


async def inventory_log_error(ctx: CTX, logs: dict, msg: str) -> None:
    """Log an error message in the inventory log channel, if set, or in the current channel."""
    channel = await log_channel(ctx, logs, "error")
    if not channel: return await Reactech(ctx.bot).reactech_channel(
        ctx, "⚠️", "An error occurred, but no error log channel is set.\n" +
        f"Use `{ctx.bot.prefix}manage_inventory log error <channel>` to set one up.")
    embed = log_embed(ctx, "error", "Inventory: System Error", msg, ctx.bot.user)
    embed.set_footer(text=f"Created by command '{ctx.command.name}' in #{ctx.channel.name}")
    return await channel.send(embed=embed)


async def inventory_log_deny(ctx: CTX, logs: dict, msg: str, user: DSC.User) -> None:
    """Log a deny message in the inventory log channel, if set, or in the current channel."""
    channel = await log_channel(ctx, logs, "deny", self=ctx.author == user)
    if not channel: return
    embed = log_embed(ctx, "deny", "Inventory: Action Denied", msg, ctx.author)
    if ctx.author != user:
        embed.set_footer(text=f"Command targeted {user.display_name}.", icon_url=user.avatar.url if user.avatar else None)
    return await channel.send(embed=embed)



##################################################
# FUNCTIONS
##################################################



def inventory_perm(converter: DscConverter, ctx: CTX, action: str, target_self: bool, permissions: dict) -> bool:
    """Check if the ctx author has the required permissions to do action on themself/others."""
    required_perms = permissions[action]
    if isinstance(required_perms, (list, tuple)) and len(required_perms) == 2:
        required_perms = required_perms[0 if target_self else 1]
    if not required_perms: return False
    for perm in required_perms:
        if isinstance(perm, int):
            if perm == ctx.author.id: return True
            else: continue
        elif perm in _ALL: return True
        elif perm.startswith("@"):
            try: role = converter.convertobj(perm[1:], "role", ctx)
            except TypeError:
                inventory_log_error(ctx, permissions, f"Invalid role `{perm}` in inventory permissions.")
                continue
            if role in ctx.author.roles: return True
        ctx_perm = getattr(ctx.author.guild_permissions, perm, None)
        if ctx_perm is None:
            inventory_log_error(ctx, permissions, f"Invalid permission `{perm}` in inventory permissions.")
            continue
        if ctx_perm: return True
    return False


def inventory_search(items: dict, item: str) -> dict:
    """Search for an item in the inventory."""
    if not item: raise ValueError("No item specified.")
    for item_data in items.values():
        if item.lower() in [item_data["name"].lower()]:
            return item_data
        if item_data["plural"] and item.lower() == item_data["plural"].lower():
            return item_data
        if item.lower() in [alias.lower() for alias in item_data["aliases"]]:
            return item_data
    return None


def inventory_value(txt: str) -> (int|float|None, list):
    """Extract a numerical value from a string."""
    if not txt: return None, []
    txt = txt.replace(",", ".").strip()
    txt = "".join([c for c in txt if c.isnumeric() or c in "+-.%="])
    if txt.startswith("="):
        result, type2 = inventory_value(txt[1:])
        if "relative" in type2: type2.remove("relative")
        return result, type2 + ["absolute"]
    if txt.startswith(("+", "-")):
        result, type2 = inventory_value(txt[1:])
        if not type2 or "relative" in type2: return None, []
        result *= -1 if txt.startswith("-") else 1
        return result, type2 + ["relative"]
    if txt.endswith("%"):
        result, type2 = inventory_value(txt[:-1])
        if not type2 or "percentage" in type2: return None, []
        return result / 100, type2 + ["percentage"]
    if txt.count(".") > 1: return None, []
    if "." in txt:
        try: return float(txt), ["float"]
        except ValueError: return None, []
    try: return int(txt), ["int"]
    except ValueError: return None, []


def inventory_quantity(inventory: dict, inv: dict, item: str) -> (int|None, bool):
    """
    Get the quantity of an item in the inventory.
    Second return value is True if the item is in inventory.
    """
    item_data = inventory_search(inventory["items"], item)
    if not item_data and inventory["settings"]["strict"] \
        and not inventory["settings"]["secret"]: return None, False
    if item_data: item = item_data["id"]
    if item in inv: return inv[item], True
    return 0, False


def inventory_stats(inventory: dict, inv: dict) -> (int, int|float, int|float):
    """
    Get statistics about the inventory :
    - number of unique items
    - quantity of all items
    - summed size of all items
    """
    num_items = len(inv)
    total_quantity = sum([abs(q) for q in inv.values()])
    total_size = 0
    for item, quantity in inv.items():
        item_data = inventory_search(inventory["items"], item)
        size = item_data["size"] if item_data else inventory["settings"]["size"]
        total_size += abs(quantity) * size
    return num_items, total_quantity, total_size


async def inventory_show(target: CTX|DSC.User, inventory: dict,
        user: DSC.User|DSC.Member, item: str = None) -> None:
    """Show the inventory of a user."""
    inv = inventory["users"].get(str(user.id), {})
    target_name = f"{user.display_name}'s" if isinstance(target, CTX) or target != user else "Your"
    async def send(target, msg):
        if isinstance(target, CTX): return await target.reply(msg, mention_author = False)
        return await target.send(msg)

    if item:
        item_data = inventory_search(inventory["items"], item)
        quantity, present = inventory_quantity(inventory, inv, item)
        if quantity is None: return await send(target, f"Item `{item}` was not recognized.")
        if item_data and (not inventory["settings"]["secret"] or present):
            item_name = item_data.get("name", item)
            if abs(quantity) != 1:
                item_name = item_data.get("plural", item_name + "s")
        else: item_name = item if abs(quantity) == 1 else item + "s"
        return await send(target, f"{target_name} inventory has {quantity} {item_name}.")

    if not inv: return await send(target, f"{target_name} inventory is empty.")
    msg = [f"{target_name} inventory:"]
    for item, quantity in inv.items():
        item_data = inventory["items"].get(item, {"name": item, "plural": item + "s"})
        if abs(quantity) != 1:
            item_name = item_data.get("plural", item_data["name"] + "s")
        else: item_name = item_data["name"]
        msg += [f"- {item_name} : {quantity}"]
    return await send(target, "\n".join(msg))


def inventory_modify(ctx: CTX, inventory: dict, user: DSC.User|DSC.Member,
        action: str, item: str, quantity: tuple) -> (str, str):
    """Modify the inventory of a user."""
    target_name = f"{user.display_name}'s" if ctx.author != user else "your"
    inv = inventory["users"].get(str(user.id), {})
    item_data = inventory_search(inventory["items"], item)
    if not item_data and inventory["settings"]["strict"]:
        return "❓", f"Item {item} was not recognized."
    current = inventory_quantity(inventory, inv, item)[0]
    
    if current is None: return "❓", f"Item {item} was not recognized."
    if "absolute" in quantity[1] and action in ["give", "remove"]:
        return "❌", f"Cannot use absolute quantity with `{action}` action."
    if item_data: item = item_data["id"]
    item_name = item_data["name"] if item_data else item

    if action == "clear":
        if not item:
            data("Data/servers.json", {}, str(ctx.guild.id), "inventory", "users", str(user.id), read_only=False)
            return "✅", f"Cleared {target_name} inventory."
        if item not in inv: return None
        del inv[item]
        data("Data/servers.json", inv, str(ctx.guild.id), "inventory", "users", str(user.id), read_only=False)
        return "✅", f"Removed {item_name} from {target_name} inventory."

    new = quantity[0] if action != "remove" else -quantity[0]
    if "percentage" in quantity[1]:
        new = int(current * quantity[0])
    if ("relative" in quantity[1] or action in ["give", "remove"]) \
            and "absolute" not in quantity[1]:
        new += current
    
    fractions = item_data["fractions"] if item_data else inventory["settings"]["fractions"]
    if fractions != 0: new = round(new * fractions) / fractions
    if new.is_integer(): new = int(new)

    item_min = item_data["min"] if item_data else inventory["settings"]["min"]
    item_max = item_data["max"] if item_data else inventory["settings"]["max"]
    if new < item_min or new > item_max:
        return "❌", f"Quantity for {item_name} must be between {item_min} and {item_max}."
    inv[item] = new
    slots, capacity, volume = inventory_stats(inventory, inv)
    attrs = {"slots": slots, "capacity": capacity, "volume": volume}
    for attr, value in attrs.items():
        if inventory["settings"][attr] is not None and value > inventory["settings"][attr]:
            culprit = attr
            break
    else: culprit = None
    if culprit: return "❌", f"Could not update: {target_name} inventory would exceeds its {culprit} limit."

    base = item_data["base"] if item_data else inventory["settings"]["base"]
    if new == 0 and base == 0: del inv[item]
    data("Data/servers.json", inv, str(ctx.guild.id), "inventory", "users", str(user.id), read_only=False)

    delta = new - current
    verb, prep = ("Added", "to") if delta > 0 else ("Removed", "from")
    if action in ["give", "remove"]:
        return "✅", f"{verb} {abs(delta)} {item_name} {prep} {target_name} inventory."
    else: return "✅", f"Set {item_name} quantity to {new} in {target_name} inventory."



##################################################
# Items
##################################################



class Items(CMDS.Cog):
    """Basic commands to check and manage an item system."""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.Reactech = Reactech(bot)
        self.DscConverter = DscConverter(bot)

    
    @CMDS.command(name = "inventory", aliases = _WORDS[1:])
    async def inventory(self, ctx: CTX, *args: str) -> None:
        """Manage a user's inventory."""
        if not ctx.guild: return await self.Reactech.reactech_user(
            ctx, "🚫", "This command can only be used in a server.")
        inventory = data("Data/servers.json", None, str(ctx.guild.id), "inventory", keynotfound=None)
        if not inventory: return await self.Reactech.reactech_user(ctx, "🚫",
            "Inventory system is not setup on this server.\n" + 
            f"Use `{self.bot.prefix}manage_inventory` to setup it up.")

        action = None ; user = None
        item = None ; quantity = None

        for arg in args:
            try:
                member = self.DscConverter.convertobj(arg, "member", ctx)
                if user: return await self.Reactech.reactech_user(
                    ctx, "⁉️", "More than one target specified.")
                if member:
                    user = member
                    continue
            except TypeError: pass

            quant = inventory_value(arg)
            if quant[0] is not None:
                if quantity is not None: return await self.Reactech.reactech_user(
                    ctx, "⁉️", "More than one quantity specified.")
                quantity = quant
                if action is None: action = "set" if "absolute" in quant[1] else "give"
                continue

            for act in _INV_ACTIONS:
                if arg.lower() in _INV_ACTIONS[act]:
                    if action: return await self.Reactech.reactech_user(
                        ctx, "⁉️", "More than one action specified.")
                    action = act
                    break
            else:
                if item: return await self.Reactech.reactech_user(
                    ctx, "⁉️", "More than one item specified.")
                item = arg.capitalize()

        if not action: action = "view"
        if not user: user = ctx.author
        if quantity is None:
            quantity = (1, ["relative"]) if action in ["give", "remove"] else (0, ["absolute"])
        if len(inventory["items"]) == 1:
            item = list(inventory["items"].values())[0]["name"]
        if action in ["give", "remove", "set"] and not item:
            return await self.Reactech.reactech_user(
                ctx, "⁉️", "No item specified.")

        allowed = inventory_perm(self.DscConverter, ctx, action, user == ctx.author, inventory["permissions"])
        if not allowed:
            gather(inventory_log_deny(ctx, inventory["log"], f"Action `{action}` was denied for {ctx.author.display_name}.", user))
            return await self.Reactech.reactech_user(ctx, "⛔",
                f"You do not have the required permissions to use `{action}` on {['yourself', 'others'][user != ctx.author]}.")
        if action in ["view", "show"]:
            target = ctx if action == "show" else ctx.author
            await inventory_show(target, inventory, user, item)
            if action == "view": await self.Reactech.reactech_valid(
                ctx, f"Sent {user.mention}'s inventory in DMs.")
            return

        result = inventory_modify(ctx, inventory, user, action, item, quantity)
        if not result: return
        return await self.Reactech.reactech_channel(ctx, *result)


    @CMDS.command(name = "manage_inventory", aliases = mixmatch(_WORDS,
        ["manage", "setup", "init", "setting", "settings", "config", "configure", "conf"], remove="manage_inventory"))
    async def manage_inventory(self, ctx: CTX, *args: str) -> None:
        """Setup and manage the inventory system on this server."""
        if not ctx.guild:
            return await self.Reactech.reactech_user(ctx, "🚫",
                "This command can only be used in a server.")
        inventory = data("Data/servers.json", None, str(ctx.guild.id), "inventory", keynotfound=None)
        if not ctx.author.guild_permissions.administrator:
            if inventory: gather(inventory_log_deny(ctx, inventory["log"],
                f"User {ctx.author.display_name} tried to use `{ctx.command.name}` with args `{' '.join(args)}`", ctx.author))
            return await self.Reactech.reactech_user(ctx, "⛔",
                "You must have administrator permissions to use this command.")
        
        if not args or is_help(args[0]):
            msg = ""
            if not inventory:
                data("Data/servers.json", _SERVER_DEFAULTS, str(ctx.guild.id), "inventory", read_only=False)
            if args and is_help(args[0]):
                msg += data("Resources/Help/Inventory/help.txt", filenotfound=False)
            else: msg += "Inventory system has been initialized on this server.\n" + \
                "Use `{prefix}manage_inventory help` to see how to configure it."
            return await ctx.reply(msg.replace("{prefix}", self.bot.prefix))
            
        


##################################################
# MAIN
##################################################



if __name__ == "__main__":
    pass