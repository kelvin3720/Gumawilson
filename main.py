import functools
from typing import Any, Callable, List, Tuple
import discord
from discord.ext import commands
import core
import global_variables as gv


# Discord bot setup
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=commands.DefaultHelpCommand(no_category="Commands"),
)


async def run_blocking(blocking_func: Callable, *args, **kwargs) -> Any:
    """Runs a blocking function in a non-blocking way"""
    func = functools.partial(
        blocking_func, *args, **kwargs
    )  # `run_in_executor` doesn't support kwargs, `functools.partial` does
    return await bot.loop.run_in_executor(None, func)


# Discord bot commands
@bot.command()
async def check(
    ctx,
    summoner_name=commands.parameter(default=None, description="Name of summoner"),
    period=commands.parameter(
        default=None, description=f"Use !show_period to show options"
    ),
    mode=commands.parameter(default="normal", description=f"normal or detailed"),
) -> None:
    """Check a player, call !check only will check the default one"""
    # Use default if None is given
    if summoner_name is None:
        summoner_name = gv.default_summoner_name
    if period is None:
        period = gv.default_period

    if summoner_name == "":
        await ctx.send("Please specify a summoner name or set a default one")
        return
    if period == "":
        await ctx.send(
            f"Please specify a period or set a default one from [{', '.join(gv.DEFAULT_PERIOD_LIST)}]"
        )
        return
    if gv.region_v4 == "":
        await ctx.send(f"Please set region_v4 from [{', '.join(gv.REGION_V4_LIST)}]")
        return
    if gv.region_v5 == "":
        await ctx.send(f"Please set region_v5 from [{', '.join(gv.REGION_V5_LIST)}]")
        return
    if mode not in ["normal", "detailed"]:
        await ctx.send("mode should be one normal or detailed")
        return

    await ctx.send(
        f"Checking {summoner_name} in {gv.region_v4}, {gv.region_v5} for {period}..."
    )

    result: Tuple[bool, str] = await run_blocking(
        core.blocking_check, summoner_name, period, mode
    )

    for text in core.split_string(result[1], 1950):
        await ctx.send(f"```{text}```")


@bot.command()
async def set_default(
    ctx,
    summoner_name=commands.parameter(
        default=gv.default_summoner_name, description="Name of summoner"
    ),
    region4=commands.parameter(
        default=gv.region_v4,
        description=f"One of [{', '.join(gv.REGION_V4_LIST)}]",
    ),
    region5=commands.parameter(
        default=gv.region_v5, description=f"One of [{', '.join(gv.REGION_V5_LIST)}]'"
    ),
    period=commands.parameter(
        default=gv.default_period,
        description=f"One of [{', '.join(gv.DEFAULT_PERIOD_LIST)}]'",
    ),
) -> None:
    """Set the default values"""
    # If wrong args are inputted
    if region4 not in gv.REGION_V4_LIST:
        await ctx.send(
            f"Incorrect region_v4, available: [{', '.join(gv.REGION_V4_LIST)}]"
        )
        return
    if region5 not in gv.REGION_V5_LIST:
        await ctx.send(
            f"Incorrect region_v5, available: [{', '.join(gv.REGION_V5_LIST)}]"
        )
        return
    if period not in gv.DEFAULT_PERIOD_LIST:
        await ctx.send(
            f"Incorrect period, available: [{', '.join(gv.DEFAULT_PERIOD_LIST)}]"
        )
        return

    gv.default_summoner_name = summoner_name
    gv.region_v4 = region4
    gv.region_v5 = region5
    gv.default_period = period
    await ctx.send(
        f"Default checking parameters updated: {gv.default_summoner_name} in {gv.region_v4}, {gv.region_v5} for {gv.default_period}."
    )


@bot.command()
async def info(ctx):
    """Show legal boilerplate"""
    legal_boilerplate = "Gumawilson isn't endorsed by Riot Games and doesn't reflect the views or opinions of Riot Games or anyone officially involved in producing or managing Riot Games properties. Riot Games, and all associated properties are trademarks or registered trademarks of Riot Games, Inc."
    await ctx.send(legal_boilerplate)


@bot.command()
async def show_period(ctx):
    """Show available options for period"""
    await ctx.send(f"```[{', '.join(gv.DEFAULT_PERIOD_LIST)}]```")


# Start the bot
bot.run(gv.DISCORD_TOKEN)
