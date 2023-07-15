import re
from datetime import datetime, timedelta
from typing import List, Tuple
import pytz
import call_api
import database_operations as dbo
import global_variables as gv


def get_summoner_details(summoner_name: str) -> dict:
    """Get summoner puuid by name"""
    url = f"https://{gv.region_v4}.api.riotgames.com/lol/summoner/v4/summoners/by-name/{summoner_name}"
    headers = {"X-Riot-Token": gv.RIOT_API_KEY}
    return call_api.call(url, headers)


def get_solo_ranked_match_ids(
    puuid: str, start_time: datetime, end_time: datetime
) -> List[str]:
    """Get list of match ids by the summoner name and a period of time"""
    # Convert datetime objects to timestamps
    start_time: int = int(start_time.timestamp())
    end_time: int = int(end_time.timestamp())

    # Make a request to the Riot API to get match history
    url = f"https://{gv.region_v5}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
    # 420 = Solo rank
    headers = {"X-Riot-Token": gv.RIOT_API_KEY}
    params = {
        "queue": 420,
        "type": "ranked",
        "startTime": start_time,
        "endTime": end_time,
        "count": 100,
    }

    return call_api.call(url, headers, params)


def get_match_details(match_id: str) -> dict:
    """Get match details by match id"""
    url = f"https://{gv.region_v5}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    headers = {"X-Riot-Token": gv.RIOT_API_KEY}

    response = call_api.call(url, headers)
    return response


def get_solo_rank_lp(summoner_id: str) -> dict:
    """Get the current solo rank and LP by summoner id"""
    url = f"https://{gv.region_v4}.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}"
    headers = {"X-Riot-Token": gv.RIOT_API_KEY}

    result = call_api.call(url, headers)

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


def get_game_end_timestamp(match_id: str) -> int:
    """Get the timestamp of gameEndTimestamp by match id, return timestamp in seconds"""
    url = f"https://{gv.region_v5}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    headers = {"X-Riot-Token": gv.RIOT_API_KEY}

    response = call_api.call(url, headers)
    # Convert to seconds timestamp
    timestamp = response["info"]["gameEndTimestamp"] // 1000
    return timestamp


def blocking_check(summoner_name: str, period: str, mode: str) -> Tuple[bool, str]:
    """Long function, return status and message"""
    # Get the start_time according to period
    now = datetime.now()
    today = datetime.today()
    # For re
    pattern = r"^last_([1-9]\d*)_days$"
    if period == "today":
        start_time = datetime(now.year, now.month, now.day)
        end_time = now
    elif period == "yesterday":
        yesterday = (now - timedelta(days=1)).date()
        start_time = datetime.combine(yesterday, datetime.min.time())
        end_time = datetime.combine(yesterday, datetime.max.time())
    elif period == "last_week":
        date_index = (today.weekday() + 1) % 7
        last_sunday = today - timedelta(date_index + 7)
        last_saturday = last_sunday + timedelta(days=6)
        start_time = datetime.combine(last_sunday, datetime.min.time())
        end_time = datetime.combine(last_saturday, datetime.max.time())
    elif period == "last_month":
        first_day_of_last_month = datetime(today.year, today.month - 1, 1)
        last_day_of_last_month = first_day_of_last_month.replace(day=28) + timedelta(
            days=4
        )
        last_day_of_last_month = last_day_of_last_month - timedelta(
            days=last_day_of_last_month.day
        )
        start_time = datetime.combine(first_day_of_last_month, datetime.min.time())
        end_time = datetime.combine(last_day_of_last_month, datetime.max.time())
    elif period == "this_week":
        end_time = now
        if today.weekday() == 6:
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            start_date = now - timedelta(days=today.weekday() + 1)
            start_time = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "this_month":
        end_time = now
        start_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif re.search(pattern, period):
        end_time = now
        match = re.search(pattern, period)
        days = int(match.group(1))
        if days < 1:
            return False, f"Please input correct number of days (>0)"
        if days > 150:
            # My API key does not allow much calls at the same time
            # Let 150 be the end
            return False, f"Please search at most 150 days"
        start_time = now - timedelta(days=days)
    else:
        return False, f"Invaild period"

    # Convert to UTC for Riot API
    local = pytz.timezone(gv.local_timezone)
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
        return False, f"{str(e)} when getting summoner id"

    if puuid is None:
        return False, f"Error getting puuid"

    # Check if summoner exists in database, create new if not exist
    try:
        summoner_exist = dbo.summoner_exists(puuid)
        if not summoner_exist:
            dbo.add_summoner(summoner_name, summoner_id, puuid)
            summoner_exist = True
    except Exception as e:
        return False, f"Failed to collect database data, {str(e)}"

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
            # Convert to datetime
            section_end_time = datetime.fromtimestamp(end_time_extend)
            result = get_solo_ranked_match_ids(puuid, start_time, section_end_time)
            match_id_list.extend(result)
    except Exception as e:
        return False, f"{str(e)} when getting match ids"

    if match_id_list is None:
        return False, f"Error getting match_id_list"
    elif len(match_id_list) == 0:
        return False, f"No match is played in the time period"

    # Check if the matches exist in db
    match_list_not_in_db = dbo.get_match_ids_not_in_db(match_id_list)

    for match_id in match_list_not_in_db:
        result = get_match_details(match_id)
        # match_detail (a row in match_detail_list) should be:
        # [match_id, region_v5, gameStartTimeStamp, gameMode, gameType, gameDuration, gameEndTimestamp, queueId, platformId, game_end_datetime]
        # Where item in snake case is from python and camel case is from Riot's API
        # Timestamps here are in milliseconds (From Riot Match-V5 API)

        # Avoid bug caused by empty game returned by Riot
        # e.g. TW2_92598712
        if len(result["info"]["participants"]) == 0:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"{now_str} Error on match_id {match_id}")
            continue
        match_detail = [match_id, gv.region_v5]
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
        early_surrender = result["info"]["participants"][0]["gameEndedInSurrender"]
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
        return False, f"{str(e)} when getting number of win and losses"
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
        return False, f"{str(e)} when getting rank and lp"

    # Calculate the total win rate
    total_wins = profile_dict["total_wins"]
    total_losses = profile_dict["total_losses"]
    total_games = total_wins + total_losses
    rank = profile_dict["rank"]
    points = profile_dict["lp"]
    if not total_games == 0:
        total_win_rate = str(int(total_wins * 100 / total_games)) + "%"
    else:
        total_win_rate = "0%"

    # Add detailed content
    if mode == "normal":
        detailed_str = ""
    elif mode == "detailed":
        try:
            detailed_str = get_detailed_str(puuid, match_id_list)
        except Exception as e:
            detailed_str = f"Failed to get detail: {str(e)}"

    # Display details on chat
    message = f"""Player: {summoner_name}

{rank} {str(points)}

=== Period Data ===
Period: {period}
Wins: {wins}
Losses: {losses}
Win rate: {win_rate}

=== Season Data ===
Total wins: {str(total_wins)}
Total losses: {str(total_losses)}
Total win rate: {total_win_rate}{detailed_str}"""
    return True, message


def get_detailed_str(puuid: str, match_id_list: List[str]) -> str:
    """Get the detailed string for !check"""
    # Header
    result = "\n\n=== Details ===\n"
    # Content
    index = 1

    summary_dict = {"posistion_played": set(), "champion_played": set()}

    for match_id in match_id_list:
        # Get details in a game
        # KDA, champion, posistion, cs, gold, damage, gold/damage
        details: dict = dbo.get_details(match_id, puuid)
        if details["posistion"] == "UTILITY":
            details["posistion"] = "SUPPORT"

        if details["win"]:
            win_lose = "WIN ✅"
        else:
            win_lose = "Lose ❌"
        end_time = details["game_end"][:-4]
        champion = details["champion"]
        posistion = details["posistion"]
        kills = int(details["kills"])
        deaths = int(details["deaths"])
        assists = int(details["assists"])
        kda = f"{str(kills)}/{str(deaths)}/{str(assists)}"
        cs = int(details["minions_killed"])
        gold_earned = int(details["gold_earned"])
        damage_to_champions = int(details["damage_to_champions"])
        if deaths == 0:
            kda_value = kills + assists
        else:
            kda_value = round((kills + deaths) / deaths, 2)
        if gold_earned == 0:
            damage_per_gold = damage_to_champions
        else:
            damage_per_gold = round(damage_to_champions / gold_earned, 2)

        result += f"""Game {str(index)}, {win_lose}
End time: {end_time}
Champion: {champion}
Posistion: {posistion}
KDA: {kda}, {str(kda_value)}
CS: {str(cs)}
Gold earned: {str(gold_earned)}
Damage to champtions: {str(damage_to_champions)}
Damage per gold: {str(damage_per_gold)}

"""
        index += 1

        ## Store data for summary
        # Posistion played
        if posistion in summary_dict:
            summary_dict[posistion] += 1
        else:
            summary_dict[posistion] = 1

        # Posistion win
        posistion_win = posistion + "_win"
        if posistion_win in summary_dict:
            if details["win"]:
                summary_dict[posistion_win] += 1
        else:
            if details["win"]:
                summary_dict[posistion_win] = 1
            else:
                summary_dict[posistion_win] = 0

        # Posistion kda
        posistion_k = posistion + "_k"
        if posistion_k in summary_dict:
            summary_dict[posistion_k] += kills
        else:
            summary_dict[posistion_k] = kills

        posistion_d = posistion + "_d"
        if posistion_d in summary_dict:
            summary_dict[posistion_d] += deaths
        else:
            summary_dict[posistion_d] = deaths

        posistion_a = posistion + "_a"
        if posistion_a in summary_dict:
            summary_dict[posistion_a] += assists
        else:
            summary_dict[posistion_a] = assists

        # Champion played
        if champion in summary_dict:
            summary_dict[champion] += 1
        else:
            summary_dict[champion] = 1

        # Champion win
        champion_win = champion + "_win"
        if champion_win in summary_dict:
            if details["win"]:
                summary_dict[champion_win] += 1
        else:
            if details["win"]:
                summary_dict[champion_win] = 1
            else:
                summary_dict[champion_win] = 0

        # Champion kda
        champion_k = champion + "_k"
        if champion_k in summary_dict:
            summary_dict[champion_k] += kills
        else:
            summary_dict[champion_k] = kills

        champion_d = champion + "_d"
        if champion_d in summary_dict:
            summary_dict[champion_d] += deaths
        else:
            summary_dict[champion_d] = deaths

        champion_a = champion + "_a"
        if champion_a in summary_dict:
            summary_dict[champion_a] += assists
        else:
            summary_dict[champion_a] = assists

        # Total kda
        if "kills" in summary_dict:
            summary_dict["kills"] += kills
        else:
            summary_dict["kills"] = kills

        if "deaths" in summary_dict:
            summary_dict["deaths"] += deaths
        else:
            summary_dict["deaths"] = deaths

        if "assists" in summary_dict:
            summary_dict["assists"] += assists
        else:
            summary_dict["assists"] = assists

        summary_dict["posistion_played"].add(posistion)
        summary_dict["champion_played"].add(champion)

    # Calculate sumnmary
    # Posistion played, posistion win rate, posistion kda,
    # champion played, champion win rate, champion kda,
    # total kda
    result += "***Posistion Data***\n"

    for pos in summary_dict["posistion_played"]:
        posistion_wins = int(summary_dict[pos + "_win"])
        posistion_loses = int(summary_dict[pos]) - posistion_wins
        posistion_win_rate = (
            round(summary_dict[pos + "_win"] / summary_dict[pos], 2) * 100
        )
        posistion_kill = int(summary_dict[pos + "_k"])
        posistion_death = int(summary_dict[pos + "_d"])
        posistion_assists = int(summary_dict[pos + "_a"])
        if posistion_death == 0:
            posistion_kda_value = posistion_kill + posistion_assists
        else:
            posistion_kda_value = round(
                (posistion_kill + posistion_assists) / posistion_death, 2
            )
        result += f"""{pos}
Number of games: {str(summary_dict[pos])}
Win rate: {str(posistion_wins)}/{str(posistion_loses)}, {str(posistion_win_rate)}%
KDA: {str(posistion_kill)}/{str(posistion_death)}/{str(posistion_assists)}, {str(posistion_kda_value)}

"""

    result += "\n***Champion Data***\n"

    for champ in summary_dict["champion_played"]:
        champion_wins = int(summary_dict[champ + "_win"])
        champion_loses = int(summary_dict[champ]) - champion_wins
        champion_win_rate = round(champion_wins / summary_dict[champ], 2) * 100
        champion_kill = int(summary_dict[champ + "_k"])
        champion_death = int(summary_dict[champ + "_d"])
        champion_assists = int(summary_dict[champ + "_a"])
        if champion_death == 0:
            champion_kda_value = champion_kill + champion_assists
        else:
            champion_kda_value = round(
                (champion_kill + champion_assists) / champion_death, 2
            )
        result += f"""{champ}
Number of games: {str(summary_dict[champ])}
Win rate: {str(champion_wins)}/{str(champion_loses)}, {str(champion_win_rate)}%
KDA: {str(champion_kill)}/{str(champion_death)}/{str(champion_assists)}, {str(champion_kda_value)}

"""

    result += "\n***Total Data***\n"

    total_kills = int(summary_dict["kills"])
    total_deaths = int(summary_dict["deaths"])
    total_assists = int(summary_dict["assists"])
    if total_deaths == 0:
        total_kda_value = total_kills + total_assists
    else:
        total_kda_value = round((total_kills + total_assists) / total_deaths, 2)

    result += f"""Number of games: {str(index-1)}
KDA: {str(total_kills)}/{str(total_deaths)}/{str(total_assists)}, {str(total_kda_value)}"""

    return result


def split_string(text: str, max_length: int) -> List[str]:
    """Divide string into substrings to avoid them exceed 2000 character (Discrod limit)"""
    output = []
    lines = text.split("\n")
    current_line = ""

    for line in lines:
        if len(current_line + line) > max_length:
            output.append(current_line)
            current_line = ""
        current_line += line + "\n"

    output.append(current_line)
    return output
