from datetime import datetime, timedelta
import os
import time
from typing import List, Tuple
import requests
import discord
from discord.ext import commands
import pytz
from tzlocal import get_localzone

# CONSTANT
DISCORD_TOKEN = os.getenv("GUMAWILSON_DISCORD_TOKEN")
RIOT_API_KEY = os.getenv("GUMAWILSON_RIOT_API_KEY")
DEFAULT_PERIOD_LIST = ["today", "yesterday", "last_week", "last_month"]


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
bot = commands.Bot(command_prefix="!", intents=intents)


# Helper functions
# Get summoner puuid by name
def get_ids(summoner_name: str) -> Tuple[str, str]:
    url = f"https://{region_v4}.api.riotgames.com/lol/summoner/v4/summoners/by-name/{summoner_name}"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    response = requests.get(url, headers=headers)

    # Wait and retry if Rate limit for API exceeded
    while response.status_code == 429:
        time.sleep(1)
        response = requests.get(url, headers=headers)

    if response.status_code == 200:
        puuid: str = response.json()["puuid"]
        summoner_id = response.json()["id"]
        return puuid, summoner_id


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
    response = requests.get(url, params, headers=headers)

    # Wait and retry if Rate limit for API exceeded
    while response.status_code == 429:
        time.sleep(1)
        response = requests.get(url, params, headers=headers)

    if response.status_code == 200:
        matches: List[str] = response.json()
        return matches


# Get match details by match id
def get_match_details(match_id: str) -> dict:
    url = f"https://{region_v5}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    response = requests.get(url, headers=headers)

    # Wait and retry if Rate limit for API exceeded
    while response.status_code == 429:
        time.sleep(1)
        response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()


# Count the number of win of lose of a player given the match
def count_win_lose(
    match_detail_list: List[dict], puuid: str
) -> Tuple[int, int]:
    wins = 0
    losses = 0
    for match in match_detail_list:
        for participant in match["info"]["participants"]:
            # Skip other players
            if participant["puuid"] != puuid:
                continue
            if participant["win"]:
                wins += 1
            else:
                losses += 1

    return wins, losses


# Get the current solo rank and LP by summoner id
def get_solo_rank_lp(summoner_id: str) -> dict:
    url = f"https://{region_v4}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}"
    headers = {"X-Riot-Token": RIOT_API_KEY}
    response = requests.get(url, headers=headers)

    # Wait and retry if Rate limit for API exceeded
    while response.status_code == 429:
        time.sleep(1)
        response = requests.get(url, headers=headers)

    if response.status_code == 200:
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


# Discord bot commands
@bot.command()
async def check(
    ctx, summoner_name=default_summoner_name, period=default_period
) -> None:
    await ctx.send(
        f"Checking {summoner_name} in {region_v4}, {region_v5} for {period}...(Max 100 games)"
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
        last_sunday = today - timedelta(days=today.weekday() + 1)
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
    puuid, summoner_id = get_ids(summoner_name)

    if puuid is None:
        await ctx.send(f"Error getting puuid")
        return

    # Get the list of match ids in the period of time
    match_id_list = get_solo_ranked_match_ids(puuid, start_time, end_time)

    if match_id_list is None:
        await ctx.send(f"Error getting match_id_list")
        return
    elif len(match_id_list) == 0:
        await ctx.send(f"No match is played in the time period")
        return

    # Get the details of matches
    match_detail_list_raw = []
    for match_id in match_id_list:
        match_detail_list_raw.append(get_match_details(match_id))

    if match_detail_list_raw is None:
        await ctx.send(f"Error getting match_detail_list_raw")
        return

    # Calculate the result for displaying
    wins, losses = count_win_lose(match_detail_list_raw, puuid)
    games = wins + losses

    # Calculate win rate in selected period
    win_rate = str(int(wins * 100 / games)) + "%"

    # Use LEAGUE-V4 to get current rank and LP
    profile_dict = get_solo_rank_lp(summoner_id)

    # Calculate the total win rate
    total_wins = profile_dict["total_wins"]
    total_losses = profile_dict["total_losses"]
    total_games = total_wins + total_losses
    total_win_rate = str(int(total_wins * 100 / total_games)) + "%"

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
    summoner_name=default_summoner_name,
    region4=region_v4,
    region5=region_v5,
    period=default_period,
) -> None:
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


# Start the bot
bot.run(DISCORD_TOKEN)
