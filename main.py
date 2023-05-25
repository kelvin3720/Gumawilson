from datetime import datetime, timedelta
import os
from typing import List, Tuple
import requests
import discord
from discord.ext import commands
import pytz
from tzlocal import get_localzone
import call_api
import database_operations as dbo

# CONSTANT
DISCORD_TOKEN = os.getenv("GUMAWILSON_DISCORD_TOKEN")
RIOT_API_KEY = os.getenv("GUMAWILSON_RIOT_API_KEY")
DEFAULT_PERIOD_LIST = [
    "today",
    "yesterday",
    "last_week",
    "last_month",
]


# Global variables
# Summoner name
default_summoner_name = ""
# For SUMMONER-V4 API
region_v4 = ""
# For MATCH-V5 API
region_v5 = ""
# In DEFAULT_PERIOD_LIST
default_period = "today"
# Timezone
local_timezone = str(get_localzone())


# Discord bot setup
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=commands.DefaultHelpCommand(no_category="Commands"),
)


# Helper functions
# Get summoner puuid by name
def get_summoner_details(summoner_name: str) -> dict:
    url = f"https://{region_v4}.api.riotgames.com/lol/summoner/v4/summoners/by-name/{summoner_name}"
    headers = {"X-Riot-Token": RIOT_API_KEY}

    response = call_api.call(url, headers)
    return response


# Get list of match ids by the summoner name and a period of time
def get_solo_ranked_match_ids(
    puuid: str, start_time: datetime, end_time: datetime
) -> List[str]:
    # Convert datetime objects to timestamps
    start_time: int = int(start_time.timestamp())
    end_time: int = int(end_time.timestamp())

    # Make a request to the Riot API to get match history
    url = f"https://{region_v5}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
    # 420 = Solo rank
    headers = {"X-Riot-Token": RIOT_API_KEY}
    params = {
        "queue": 420,
        "type": "ranked",
        "startTime": start_time,
        "endTime": end_time,
        "count": 100,
    }

    response = call_api.call(url, headers, params)

    return response


# Get match details by match id
def get_match_details(match_id: str) -> dict:
    url = f"https://{region_v5}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    headers = {"X-Riot-Token": RIOT_API_KEY}

    response = call_api.call(url, headers)
    return response


# Get the current solo rank and LP by summoner id
def get_solo_rank_lp(summoner_id: str) -> dict:
    url = f"https://{region_v4}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}"
    headers = {"X-Riot-Token": RIOT_API_KEY}

    response = call_api.call(url, headers)

    response = requests.get(url, headers=headers)
    result: List[dict] = response.json()

    # List for return
    return_dict = {}
    for profile in result:
        if profile["queueType"] != "RANKED_SOLO_5x5":
            continue

        # Append str in format like "SILVER III"
        tier = profile["tier"]
        rank = profile["rank"]
        return_dict.update({"rank": f"{tier} {rank}"})

        # Append str LP
        lp = profile["leaguePoints"]
        return_dict.update({"lp": str(lp)})

        # Append total win and lose
        wins = profile["wins"]
        losses = profile["losses"]
        return_dict.update({"total_wins": wins})
        return_dict.update({"total_losses": losses})

        return return_dict


# Get the timestamp of gameEndTimestamp by match id, return timestamp in seconds
def get_game_end_timestamp(match_id: str) -> int:
    url = f"https://{region_v5}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    headers = {"X-Riot-Token": RIOT_API_KEY}

    response = call_api.call(url, headers)
    # Convert to seconds timestamp
    timestamp = response["info"]["gameEndTimestamp"] // 1000
    return timestamp


# Discord bot commands
@bot.command()
async def check(
    ctx,
    summoner_name=commands.parameter(
        default=None, description="Name of summoner"
    ),
    period=commands.parameter(
        default=None,
        description='One of ["today", "yesterday", "last_week", "last_month"]',
    ),
) -> None:
    """Check a player, call !check only will check the default one"""
    # Use default if None is given
    if summoner_name is None:
        summoner_name = default_summoner_name
    if period is None:
        period = default_period

    if summoner_name == "":
        await ctx.send("Please specify a summoner name or set a default one")
        return
    if period == "":
        await ctx.send(
            'Please specify a period or set a default one from ["today", "yesterday", "last_week", "last_month"]'
        )
        return
    if region_v4 == "":
        await ctx.send(
            'Please set region_v4 from ["br1", "eun1", "euw1", "jp1", "kr", "la1", "la2", "na1", "oc1", "tr1", "ru", "ph2", "sg2", "th2", "tw2", "vn2"]'
        )
        return
    if region_v5 == "":
        await ctx.send(
            'Please set region_v5 from ["americas", "asia", "europe", "sea"]'
        )
        return

    await ctx.send(
        f"Checking {summoner_name} in {region_v4}, {region_v5} for {period}..."
    )

    # Get the start_time according to period
    now = datetime.now()
    today = datetime.today()
    if period == "today":
        start_time = datetime(now.year, now.month, now.day)
        end_time = now
    elif period == "yesterday":
        yesterday = (now - timedelta(days=1)).date()
        start_time = datetime.combine(yesterday, datetime.min.time())
        end_time = datetime.combine(yesterday, datetime.max.time())
    elif period == "last_week":
        last_sunday = today - timedelta(days=today.weekday() + 1 + 7)
        last_saturday = last_sunday + timedelta(days=6)
        start_time = datetime.combine(last_sunday, datetime.min.time())
        end_time = datetime.combine(last_saturday, datetime.max.time())
    elif period == "last_month":
        first_day_of_last_month = datetime(today.year, today.month - 1, 1)
        last_day_of_last_month = first_day_of_last_month.replace(
            day=28
        ) + timedelta(days=4)
        last_day_of_last_month = last_day_of_last_month - timedelta(
            days=last_day_of_last_month.day
        )
        start_time = datetime.combine(
            first_day_of_last_month, datetime.min.time()
        )
        end_time = datetime.combine(
            last_day_of_last_month, datetime.max.time()
        )

    # Convert to UTC for Riot API
    local = pytz.timezone(local_timezone)
    local_start = local.localize(start_time, is_dst=None)
    local_end = local.localize(end_time, is_dst=None)
    start_time = local_start.astimezone(pytz.utc)
    end_time = local_end.astimezone(pytz.utc)

    # Get summoner's puuid
    try:
        details = get_summoner_details(summoner_name)
        puuid: str = details["puuid"]
        summoner_id: str = details["id"]
    except Exception as e:
        await ctx.send(f"{str(e)} when getting summoner id")
        return

    if puuid is None:
        await ctx.send(f"Error getting puuid")
        return

    # Check if summoner exists in database, create new if not exist
    try:
        summoner_exist = dbo.summoner_exists(puuid)
        if not summoner_exist:
            dbo.add_summoner(summoner_name, summoner_id, puuid)
            summoner_exist = True
    except Exception as e:
        await ctx.send(
            f"Failed to collect database data, using Riot data directly"
        )

    # Get the list of match ids in the period of time
    try:
        match_id_list = []
        result = get_solo_ranked_match_ids(puuid, start_time, end_time)
        match_id_list.extend(result)
        # Continue using the api with different time params if the length of list is 100
        # Riot Match-V5 API can at most reply 100 match ids in one call
        while len(result) == 100:
            last_match_in_list = result[-1]
            # Get the gameEndTimestamp by Match-V5 API
            # API for a specific match uses timestamp in milliseconds,
            # but timestamp for list of match ids uses timestamp in seconds
            end_time_extend = get_game_end_timestamp(last_match_in_list)
            result = get_solo_ranked_match_ids(
                puuid, start_time, end_time_extend
            )
            match_id_list.extend(result)
        # Remove duplicate
        match_id_list = list(set(match_id_list))
    except Exception as e:
        await ctx.send(str(e))
        f"{str(e)} when getting match ids"
        return

    if match_id_list is None:
        await ctx.send(f"Error getting match_id_list")
        return
    elif len(match_id_list) == 0:
        await ctx.send(f"No match is played in the time period")
        return

    # Check if the matches exist in db
    match_list_not_in_db = dbo.get_match_ids_not_in_db(match_id_list)

    for match_id in match_list_not_in_db:
        result = get_match_details(match_id)
        # match_detail (a row in match_detail_list) should be:
        # [match_id, region_v5, gameStartTimeStamp, gameMode, gameType, gameDuration, gameEndTimestamp, queueId, platformId, game_end_datetime]
        # Where item in snake case is from python and camel case is from Riot's API
        # Timestamps here are in milliseconds (From Riot Match-V5 API)
        match_detail = [match_id, region_v5]
        # gameStartTimestamp
        match_detail.append(result["info"]["gameStartTimestamp"])
        # gameMode
        match_detail.append(result["info"]["gameMode"])
        # gameType
        match_detail.append(result["info"]["gameType"])
        # gameDuration
        match_detail.append(result["info"]["gameDuration"])
        # gameEndTimestamp
        match_detail.append(result["info"]["gameEndTimestamp"])
        # gameEndedInEarlySurrender
        early_surrender = result["info"]["participants"][0][
            "gameEndedInSurrender"
        ]
        match_detail.append(early_surrender)
        # queueId
        match_detail.append(result["info"]["queueId"])
        # platformId
        match_detail.append(result["info"]["platformId"])
        # Calculate game_end_datetime GMT in string
        game_end = result["info"]["gameEndTimestamp"]
        # Translate to timestamp in seconds
        game_end_datetime = datetime.fromtimestamp(game_end / 1000.0)
        match_detail.append(game_end_datetime.strftime("%Y-%m-%d %H:%M:%S"))

        # Insert the row to table matches
        dbo.insert_to_matches(match_detail)

        # Insert player's details of this match to match_players table
        dbo.insert_to_match_players(result)

    # Calculate the result for displaying
    try:
        wins, losses = dbo.count_win_lose(match_id_list, puuid)
    except Exception as e:
        await ctx.send(str(e))
        f"{str(e)} when getting number of win and losses"
        return
    games = wins + losses

    # Calculate win rate in selected period
    if not games == 0:
        win_rate = str(int(wins * 100 / games)) + "%"
    else:
        win_rate = "0%"

    # Use LEAGUE-V4 to get current rank and LP
    try:
        profile_dict = get_solo_rank_lp(summoner_id)
    except Exception as e:
        await ctx.send(str(e))
        f"{str(e)} when getting rank and lp"
        return

    # Calculate the total win rate
    total_wins = profile_dict["total_wins"]
    total_losses = profile_dict["total_losses"]
    total_games = total_wins + total_losses
    if not total_games == 0:
        total_win_rate = str(int(total_wins * 100 / total_games)) + "%"
    else:
        total_win_rate = "0%"

    # Display details on chat
    message = f"""Player: {summoner_name}

=== Period Data ===
Period: {period}
Wins: {wins}
Losses: {losses}
Win rate: {win_rate}

=== Season Data ===
Total wins: {str(total_wins)}
Total losses: {str(total_losses)}
Total win rate: {total_win_rate}"""
    await ctx.send(message)


@bot.command()
async def set_default(
    ctx,
    summoner_name=commands.parameter(
        default=default_summoner_name, description="Name of summoner"
    ),
    region4=commands.parameter(
        default=region_v4,
        description='One of ["br1", "eun1", "euw1", "jp1", "kr", "la1", "la2", "na1", "oc1", "tr1", "ru", "ph2", "sg2", "th2", "tw2", "vn2"]',
    ),
    region5=commands.parameter(
        default=region_v5,
        description='One of ["americas", "asia", "europe", "sea"]',
    ),
    period=commands.parameter(
        default=default_period,
        description='One of ["today", "yesterday", "last_week", "last_month"]',
    ),
) -> None:
    """Set the default values"""
    # If wrong period in inputted
    if period not in DEFAULT_PERIOD_LIST:
        await ctx.send(
            f"Incorrect period, available: [{', '.join(DEFAULT_PERIOD_LIST)}]"
        )
        return

    global default_summoner_name, region_v4, region_v5, default_period
    default_summoner_name = summoner_name
    region_v4 = region4
    region_v5 = region5
    default_period = period
    await ctx.send(
        f"Default checking parameters updated: {default_summoner_name} in {region_v4}, {region_v5} for {default_period}."
    )


@bot.command()
async def info(ctx):
    """Show legal boilerplate"""
    legal_boilerplate = "Gumawilson isn't endorsed by Riot Games and doesn't reflect the views or opinions of Riot Games or anyone officially involved in producing or managing Riot Games properties. Riot Games, and all associated properties are trademarks or registered trademarks of Riot Games, Inc."
    await ctx.send(legal_boilerplate)


# Start the bot
bot.run(DISCORD_TOKEN)
