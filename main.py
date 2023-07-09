import functools
from typing import Any, Callable, List, Tuple
import discord
from discord import option
import core
import global_variables as gv


# Discord bot setup
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = discord.Bot(
    intents=intents,
)


async def run_blocking(blocking_func: Callable, *args, **kwargs) -> Any:
    """Runs a blocking function in a non-blocking way"""
    func = functools.partial(
        blocking_func, *args, **kwargs
    )  # `run_in_executor` doesn't support kwargs, `functools.partial` does
    return await bot.loop.run_in_executor(None, func)


# Discord bot commands
@bot.slash_command(name="check")
@option(
    "summoner_name",
    str,
    description="Name of the summoner",
    required=False,
)
@option(
    "period",
    str,
    description="Period to check",
    choices=gv.DEFAULT_PERIOD_LIST,
    required=False,
)
@option(
    "mode",
    str,
    description="Checking mode",
    choices=["normal", "detailed"],
    required=False,
    default="normal",
)
@option(
    "days",
    int,
    description="Overwrite period to last n days",
    required=False,
    min_value=1,
    max_value=150,
)
async def check(
    interaction: discord.Interaction,
    summoner_name: str,
    period: str,
    mode: str,
    days: int,
) -> None:
    """Check a player, call !check only will check the default one"""
    # Use default if None is given
    if summoner_name is None:
        summoner_name = gv.default_summoner_name
    if period is None:
        period = gv.default_period

    if summoner_name == "":
        await interaction.response.send_message(
            "Please specify a summoner name or set a default one"
        )
        return
    if period == "":
        await interaction.response.send_message(
            f"Please specify a period or set a default one from [{', '.join(gv.DEFAULT_PERIOD_LIST)}]"
        )
        return
    if gv.region_v4 == "":
        await interaction.response.send_message(
            f"Please set region_v4 from [{', '.join(gv.REGION_V4_LIST)}]"
        )
        return
    if gv.region_v5 == "":
        await interaction.response.send_message(
            f"Please set region_v5 from [{', '.join(gv.REGION_V5_LIST)}]"
        )
        return

    # Overwrite period if there is input in days (old last_n_days parameter)
    if days is not None:
        period = f"last_{str(days)}_days"

    result: Tuple[bool, str] = await run_blocking(
        core.blocking_check, summoner_name, period, mode
    )

    for text in core.split_string(result[1], 1950):
        await interaction.response.send_message(f"```{text}```")


@bot.slash_command(name="set_default")
@option("summoner_name", str, description="Name of the summoner")
@option("region4", str, description="Region for Riot V4 API", choices=gv.REGION_V4_LIST)
@option("region5", str, description="Region for Riot V5 API", choices=gv.REGION_V5_LIST)
@option(
    "period",
    str,
    description="One of the period listed on show_period",
    choices=gv.DEFAULT_PERIOD_LIST,
)
async def set_default(
    ctx,
    # interaction: discord.Interaction,
    summoner_name: str,
    region4: str,
    region5: str,
    period: str,
) -> None:
    """Set the default values"""
    gv.default_summoner_name = summoner_name
    gv.region_v4 = region4
    gv.region_v5 = region5
    gv.default_period = period
    await ctx.respond(
        f"Default checking parameters updated: \
{gv.default_summoner_name} in {gv.region_v4}, {gv.region_v5} for {gv.default_period}."
    )


@bot.slash_command(name="info")
async def info(interaction: discord.Interaction):
    """Show legal boilerplate"""
    legal_boilerplate = "Gumawilson isn't endorsed by Riot Games and doesn't reflect the views or opinions of Riot Games or anyone officially involved in producing or managing Riot Games properties. Riot Games, and all associated properties are trademarks or registered trademarks of Riot Games, Inc."
    await interaction.response.send_message(legal_boilerplate, ephemeral=True)


@bot.slash_command(name="show_period")
async def show_period(interaction: discord.Interaction):
    """Show available options for period"""
    await interaction.response.send_message(
        f"```[{', '.join(gv.DEFAULT_PERIOD_LIST)}]```", ephemeral=True
    )


# Start the bot
bot.run(gv.DISCORD_TOKEN)
