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
from math import log10

from Extensions.Common import get_prefix
from Modules.inv import *
from Modules.data import data
from Modules.reactech import Reactech
from Modules.discord_utils import DscConverter
from Modules.basic import mixmatch, format_number


async def setup(bot: Bot):
    await bot.add_cog(Inventory_base(bot))
    await bot.add_cog(Inventory_manage(bot))



##################################################
# FUNCTIONS
##################################################



async def inventory_show(ctx: CTX, target: CTX|DSC.User, inventory: dict,
        user: DSC.User|DSC.Member, item: str = None) -> None:
    """
    Show the inventory of a user, either as a DM or in the current channel.
    If an item is specified, show only that item's quantity.
    Otherwise, list all items in the user's inventory.
    """
    inv = get_user_inv(inventory, user)
    # Determine possessive or "Your" for the inventory label
    target_name = f"`{user.display_name}`'s" if isinstance(target, CTX) or target != user else "Your"

    if item:
        # Show only a specific item
        item_data = get_item(inventory["items"], item)
        quantity, present = check_quantity(inventory, inv, item)
        if quantity is None:
            return await inv_send(target, f"Item `{item}` was not recognized.")
        # Use inventory_name for display
        if item_data and inventory["settings"]["secret"] and not present:
            item_data = None
        item_name = item_display_name(item_data or item, quantity)
        # Log the action (show if public, view if DM)
        gather(log_action(
            ctx, inventory["logs"],
            "show" if isinstance(target, CTX) else "view",
            item_name, user
        ))
        return await inv_send(target, f"{target_name} inventory has {quantity} {item_name}.")

    # If no item specified, show all items in inventory
    if not inv:
        return await inv_send(target, f"{target_name} inventory is empty.")
    msg = [f"{target_name} inventory:"]
    for item, quantity in inv.items():
        item_data = inventory["items"].get(item)
        if not item_data:
            if item.isdigit():
                await log_error(ctx, inventory["logs"],
                    f"Item ID `{item}` in `{user.display_name}`'s inventory not found in item list.")
                continue
        msg += [f"- {item_display_name(item_data or item, quantity)} : {quantity}"]
    
    # Add inventory stats if applicable
    num_items, total_quantity, total_size = get_stats(inventory, inv)
    stats = [
        (num_items, inventory["settings"]["slots"], "unique items"),
        (total_quantity, inventory["settings"]["capacity"], "total quantity"),
        (total_size, inventory["settings"]["volume"], "volume taken")
    ]
    for current, limit, label in stats:
        if limit is None: continue
        msg += [f"**{format_number(current)}** / {format_number(limit)} {label}."]

    # Log the action (show if public, view if DM)
    gather(log_action(
        ctx, inventory["logs"],
        "show" if isinstance(target, CTX) else "view",
        None, user
    ))
    return await inv_send(target, "\n".join(msg))


async def inventory_info(ctx: CTX, inventory: dict, user: DSC.User|DSC.Member, item: str) -> None:
    """
    Display information about an item for a user.
    Returns either a Discord embed (with item info) or a string if not recognized.
    If the inventory is secret and the user doesn't have the item, hides info.
    """
    inv = get_user_inv(inventory, user)
    quantity, present = check_quantity(inventory, inv, item)
    if quantity is None:
        return (f"Item `{item}` was not recognized.", "❓")
    item_data = get_item(inventory["items"], item)
    if not item_data or (inventory["settings"]["secret"] and not present):
        return (f"Item `{item}` was not recognized.", "❓")

    color = item_data.get('color', inventory['item_default']['color'])
    embed = DSC.Embed(
        title=item_data['name'],
        description=item_data.get('description'),
        color=int(color.removeprefix("#"), 16)
    )

    # Show emoji as thumbnail or prefix in title
    if item_data["emoji"]:
        emoji = DSC.PartialEmoji.from_str(item_data['emoji'].strip())
        if emoji.url:
            embed.set_thumbnail(url=emoji.url)
        else:
            embed.title = f"{item_data['emoji']}{embed.title}"
    embed.set_image(url=item_data.get('image'))
    
    # Add item attributes to footer if they differ from defaults
    attributes = {
        "fractions": "Divisible by ",
        "min": "Minimum quantity: ",
        "base": "Default quantity: ",
        "max": "Maximum quantity: ",
        "size": "Unit size: ",
    }
    attrs = ["ID: " + item_data['id']]
    for k, v in attributes.items():
        if k == "size" and inventory['settings']['volume'] is None:
            continue
        if item_data.get(k) != inventory['item_default'][k]:
            if k == "fractions" and item_data[k] in [0, 1]:
                if item_data[k] == 0:
                    attrs.append("Decimal")
                if item_data[k] == 1:
                    attrs.append("Integer")
                continue
            attrs.append(f"{v}{item_data[k]}")
    embed.set_footer(text=" | ".join(attrs))
    return (embed, None)


def inventory_modify(ctx: CTX, inventory: dict, user: DSC.User|DSC.Member,
        action: str, item: str, quantity: tuple) -> (str, str):
    """
    Modify the inventory of a user.
    Handles give, remove, change, and clear actions.
    Returns a tuple (emoji, message) for feedback.
    """
    target_name = f"`{user.display_name}`'s" if ctx.author != user else "your"
    inv = get_user_inv(inventory, user)
    item_data = get_item(inventory["items"], item)
    if not item_data and inventory["settings"]["strict"]:
        return "❓", f"Item {item} was not recognized."
    old, present = check_quantity(inventory, inv, item)
    if old is None:
        return "❓", f"Item {item} was not recognized."
    if item_data:
        item = item_data["id"]
    # Use inventory_name for display
    item_name = item_display_name(item_data or item, old)
    # Handle clearing inventory or a specific item
    if action == "clear":
        if not item:
            # Clear all items for the user
            data("Data/servers.json", None, str(ctx.guild.id), "inventory", "users", str(user.id), read_only=False)
            gather(log_action(ctx, inventory["logs"], "change", None, user))
            return "✅", f"Cleared {target_name} inventory."
        if present is True:
            base = item_data["base"] if item_data else inventory["item_default"]["base"]
            if old != base:
                if base == 0:
                    del inv[item]
                else:
                    inv[item] = base
                data("Data/servers.json", inv, str(ctx.guild.id), "inventory", "users", str(user.id), read_only=False)
                gather(log_change(ctx, inventory["logs"], item_data or item_name, old, base, user))
        return "✅", f"Removed {item_name} from {target_name} inventory."

    # Calculate new quantity based on action and quantity type
    new = quantity[0] if action != "remove" else -quantity[0]
    if "percentage" in quantity[1]:
        new = int(old * quantity[0])
    if ("relative" in quantity[1] or action in ["give", "remove"]) \
            and "absolute" not in quantity[1]:
        new += old

    # Enforce fractions (divisibility)
    fractions = item_data["fractions"] if item_data else inventory["item_default"]["fractions"]
    if fractions != 0:
        new = round(new * fractions) / fractions
    if isinstance(new, float) and new.is_integer():
        new = int(new)

    # Enforce min/max constraints
    item_min = item_data["min"] if item_data else inventory["item_default"]["min"]
    item_max = item_data["max"] if item_data else inventory["item_default"]["max"]
    if (item_min != "-∞" and new < item_min) or \
            (item_max != "+∞" and new > item_max):
        return "❌", f"Quantity for {item_name} must be between `{format_number(item_min)}` and `{format_number(item_max)}`."
    inv[item] = new

    # Check for inventory limits (slots, capacity, volume)
    slots, capacity, volume = get_stats(inventory, inv)
    attrs = {"slots": slots, "capacity": capacity, "volume": volume}
    for attr, value in attrs.items():
        if inventory["settings"][attr] is not None and value > inventory["settings"][attr]:
            culprit = attr
            break
    else:
        culprit = None
    if culprit:
        return "❌", f"Could not update: {target_name} inventory would exceeds its {culprit} limit."

    # Remove item if quantity is zero and base is zero
    base = item_data["base"] if item_data else inventory["item_default"]["base"]
    if new == 0 and base == 0:
        del inv[item]
    data("Data/servers.json", inv, str(ctx.guild.id), "inventory", "users", str(user.id), read_only=False)

    # Prepare log and feedback message
    delta = new - old if action in ["give", "remove"] else new
    delta = round(delta, int(log10(fractions+1))+1)
    txt = {
        "give": "Added {delta} {item_name} to {target_name} inventory.",
        "remove": "Removed {delta} {item_name} from {target_name} inventory.",
        "change": "Set {item_name} quantity to {delta} in {target_name} inventory."
    }[action]
    if action in ["give", "remove"]:
        delta = abs(delta)
    item_name = item_display_name(item_data or item, delta)
    gather(log_change(ctx, inventory["logs"], item_name, old, new, user))
    return "✅", txt.format(delta=format_number(delta), item_name=item_name, target_name=target_name)



##################################################
# Inventory base
##################################################



class Inventory_base(CMDS.Cog):
    """Basic commands to check and manage an item system."""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.Reactech = Reactech(bot)
        self.DscConverter = DscConverter(bot)


    @CMDS.command(name = "inventory", aliases = WORDS["inv"][1:])
    async def inventory(self, ctx: CTX, *args: str) -> None:
        """
        Main command to manage a user's inventory.
        Parses arguments to determine action, target user, item, and quantity.
        Handles permission checks, argument validation, and dispatches to inventory logic.
        """
        if not ctx.guild:
            return await self.Reactech.reactech_user(
                ctx, "🚫", "This command can only be used in a server.")
        inventory = data("Data/servers.json", None, str(ctx.guild.id), "inventory", keynotfound=None)
        if not inventory:
            return await self.Reactech.reactech_user(ctx, "🚫",
                "Inventory system is not setup on this server.\n" + 
                f"Use `{self.bot.prefix}manage_inventory` to setup it up.")

        action = None ; user = None
        item = None ; quantity = None

        # Parse arguments for member, quantity, action, and item
        for arg in args:
            try:
                member = self.DscConverter.convertobj(arg, "member", ctx)
                if user:
                    return await self.Reactech.reactech_user(
                        ctx, "⁉️", "More than one target specified.")
                if member:
                    user = member
                    continue
            except TypeError:
                pass

            quant = resolve_value(arg)
            if quant[0] is not None:
                if quantity is not None:
                    return await self.Reactech.reactech_user(
                        ctx, "⁉️", "More than one quantity specified.")
                quantity = quant
                if action is None:
                    action = "change" if "absolute" in quant[1] else "give"
                continue

            act = resolve_action(arg)
            if act:
                if action:
                    return await self.Reactech.reactech_user(
                        ctx, "⁉️", "More than one action specified.")
                action = act
            else:
                if item:
                    return await self.Reactech.reactech_user(
                        ctx, "⁉️", "More than one item specified.")
                item = name_to_alias(arg, capitalize=True)

        if not action:
            action = "view"
        if not user:
            user = ctx.author
        if quantity is None:
            quantity = (1, ["relative"]) \
                if action in ["give", "remove"] \
                else (0, ["absolute"])
        # If item is required but not specified, try to use default or only item
        if action in ["give", "remove", "change", "info"] and not item:
            if inventory["settings"]["default_item"]:
                item = inventory["items"].get(inventory["settings"]["default_item"])
                if not item:
                    gather(log_error(ctx, inventory["logs"],
                        f"Default item `#{inventory['settings']['default_item']}` not found in inventory items."))
            elif len(inventory["items"]) == 1:
                item = list(inventory["items"].values())[0]["name"]
            else:
                return await self.Reactech.reactech_user(
                    ctx, "⁉️", "No item specified.")

        allowed = await check_inv_perm(ctx, action, user == ctx.author, inventory)
        if not allowed:
            gather(log_deny(ctx, inventory["logs"], f"Action `{action}` was denied for `{ctx.author.display_name}`.", user))
            return await self.Reactech.reactech_user(ctx, "⛔",
                f"You do not have the required permissions to use `{action}` on {['yourself', 'others'][user != ctx.author]}.");

        # Handle view/show actions (show inventory in DM or channel)
        if action in ["view", "show"]:
            target = ctx if action == "show" else ctx.author
            await inventory_show(ctx, target, inventory, user, item)
            if action == "view":
                await self.Reactech.reactech_valid(
                    ctx, f"Sent `{user.display_name}`'s inventory in DMs.")
            return

        # Handle info action (show item info)
        if action == "info":
            message, emoji = await inventory_info(ctx, inventory, ctx.author, item)
            if inventory["settings"]["secret"]:
                await inv_send(ctx, message, True)
                return await self.Reactech.reactech_valid(
                    ctx, f"Sent information about item `{item}` in DMs.")
            if emoji is None:
                return await inv_send(ctx, message)
            return await self.Reactech.reactech_channel(ctx, emoji, message)

        # Handle give/remove/change actions
        result = inventory_modify(ctx, inventory, user, action, item, quantity)
        if not result:
            return
        return await self.Reactech.reactech_channel(ctx, *result)


    @CMDS.command(name = "inventory_view", aliases = mixmatch(
            WORDS["inv"], [i for i in INV_ACTIONS["view"] if len(i) > 1], remove="inventory_view"))
    async def inventory_view(self, ctx, *args):
        """Alias for `inventory view`."""
        await self.inventory(ctx, "view", *args)
    
    @CMDS.command(name = "inventory_show", aliases = mixmatch(
            WORDS["inv"], [i for i in INV_ACTIONS["show"] if len(i) > 1], remove="inventory_show"))
    async def inventory_show(self, ctx, *args):
        """Alias for `inventory show`."""
        await self.inventory(ctx, "show", *args)
    
    @CMDS.command(name = "inventory_info", aliases = mixmatch(
            WORDS["inv"], [i for i in INV_ACTIONS["info"] if len(i) > 1], remove="inventory_info"))
    async def inventory_info(self, ctx, *args):
        """Alias for `inventory info`."""
        await self.inventory(ctx, "info", *args)
    
    @CMDS.command(name = "inventory_give", aliases = mixmatch(
            WORDS["inv"], [i for i in INV_ACTIONS["give"] if len(i) > 1], remove="inventory_give"))
    async def inventory_give(self, ctx, *args):
        """Alias for `inventory give`."""
        await self.inventory(ctx, "give", *args)
    
    @CMDS.command(name = "inventory_remove", aliases = mixmatch(
            WORDS["inv"], [i for i in INV_ACTIONS["remove"] if len(i) > 1], remove="inventory_remove"))
    async def inventory_remove(self, ctx, *args):
        """Alias for `inventory remove`."""
        await self.inventory(ctx, "remove", *args)
    
    @CMDS.command(name = "inventory_change", aliases = mixmatch(
            WORDS["inv"], [i for i in INV_ACTIONS["change"] if len(i) > 1], remove="inventory_change"))
    async def inventory_change(self, ctx, *args):
        """Alias for `inventory change`."""
        await self.inventory(ctx, "change", *args)



##################################################
# Inventory Manage
##################################################


class Inventory_manage(CMDS.Cog):
    """Command to setup and manage the inventory system on a server."""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.Reactech = Reactech(bot)


    @CMDS.command(name = "manage_inventory", aliases = mixmatch(WORDS["inv"], WORDS["conf"], remove="manage_inventory"))
    async def manage_inventory(self, ctx: CTX, *args: str) -> None:
        """
        Setup and manage the inventory system on this server.
        Only administrators can use this command.
        Initializes inventory if not present, and provides help/configuration info.
        """
        if not ctx.guild:
            return await self.Reactech.reactech_user(
                ctx, "🚫", "This command can only be used in a server.")
        inventory = data("Data/servers.json", None, str(ctx.guild.id), "inventory", keynotfound=None)
        if not ctx.author.guild_permissions.administrator:
            if inventory:
                gather(log_deny(ctx, inventory["logs"],
                    f"User `{ctx.author.display_name}` tried to use `{ctx.command.name}` with args `{' '.join(args)}`", ctx.author))
            return await self.Reactech.reactech_user(ctx, "⛔",
                "You must have `administrator` permissions to use this command.")

        # If no args or help/config requested, show help or initialize
        if not args or args[0].lower() in WORDS["help"] + WORDS["conf"]:
            msg = ""
            if not inventory:
                data("Data/servers.json", SERVER_DEFAULTS, str(ctx.guild.id), "inventory", read_only=False)
            if args and args[0].lower() in WORDS["help"]:
                msg += data("Resources/Help/Inventory/help.txt", filenotfound=False)
            else:
                msg += "Inventory system has been initialized on this server.\n" + \
                    "Use `{prefix}manage_inventory help` to see how to configure it."
            return await ctx.reply(msg.format(prefix=get_prefix(ctx)[0]))
            


##################################################
# MAIN
##################################################



if __name__ == "__main__":
    pass