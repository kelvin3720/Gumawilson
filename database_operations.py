from sys import platform
from typing import List, Tuple
import mysql.connector
import global_variables as gv


def call_stored_procedure_no_return(procedure_name: str, params: tuple) -> None:
    """Call a stored procedure with no return"""
    db = mysql.connector.connect(
        host=gv.database_host,
        user=gv.sql_user,
        password=gv.sql_password,
        database=gv.database,
    )
    cursor = db.cursor()
    cursor.callproc(procedure_name, params)
    db.commit()
    cursor.close()
    db.close()


def call_stored_procedure_with_return(procedure_name: str, params: tuple) -> list:
    """Call a stored procedure with return value"""
    db = mysql.connector.connect(
        host=gv.database_host,
        user=gv.sql_user,
        password=gv.sql_password,
        database=gv.database,
    )
    cursor = db.cursor()
    result = cursor.callproc(procedure_name, params)
    cursor.close()
    db.close()
    return result


def add_summoner(summoner_name: str, summoner_id: str, puuid: str) -> None:
    """Add new summoner to summoners table"""
    params = (summoner_name, summoner_id, puuid)
    call_stored_procedure_no_return("sp_add_new_summoner", params)


def summoner_exists(puuid: str) -> None:
    """Check if summoner already exist in summoners table by puuid"""
    params = (puuid, 0)
    result = call_stored_procedure_with_return("sp_summoner_exists", params)
    # Return body: (puuid, 1|0)
    return bool(result[1])


def match_exists(match_id) -> bool:
    """Check if match exists in database"""
    params = (match_id, 0)
    result = call_stored_procedure_with_return("sp_match_exists", params)
    # Return body: (puuid, 1|0)
    return bool(result[1])


def get_match_ids_not_in_db(id_list: list) -> List[str]:
    """Find the match ids which is not in the database"""
    not_exist = []
    for id in id_list:
        if not match_exists(id):
            not_exist.append(id)

    return not_exist


def insert_to_matches(data_list) -> None:
    """Insert given data to matches table"""
    params = tuple(data_list)
    call_stored_procedure_no_return("sp_add_new_match", params)


def insert_to_match_players(api_result: dict) -> None:
    """Insert data to match_players table from API result"""

    # Get reuquired values from the api result
    # Common column
    match_id = api_result["metadata"]["matchId"]

    for player_data in api_result["info"]["participants"]:
        param_list = []
        param_list.append(player_data["puuid"])
        param_list.append(match_id)
        param_list.append(player_data["kills"])
        param_list.append(player_data["deaths"])
        param_list.append(player_data["assists"])
        param_list.append(player_data["championName"])
        param_list.append(player_data["goldEarned"])
        param_list.append(player_data["individualPosition"])
        param_list.append(player_data["totalDamageDealtToChampions"])
        param_list.append(player_data["totalMinionsKilled"])
        param_list.append(player_data["win"])

        # Insert to match_players table
        params = tuple(param_list)
        call_stored_procedure_no_return("sp_add_new_match_players_record", params)


def count_win_lose(match_id_list: List[str], puuid: str) -> Tuple[int, int]:
    """Count the number of wins and losses from match_id_list and puuid"""
    wins = 0
    losses = 0

    for id in match_id_list:
        params = (id, puuid, 0)
        # 1: win, 0: lose, -1: remake
        match_result = call_stored_procedure_with_return("sp_check_is_win", params)[2]
        if match_result == 1:
            wins += 1
        elif match_result == 0:
            losses += 1

    return wins, losses


def get_details(match_id: str, puuid: str) -> dict:
    """Get the detailed string from puuid and match_id"""
    params = (match_id, puuid, 0, 0, 0, "", "", 0, 0, 0, None, 0)
    result = call_stored_procedure_with_return("sp_match_player_detail", params)
    return dict(
        kills=result[2],
        deaths=result[3],
        assists=result[4],
        champion=result[5],
        posistion=result[6],
        minions_killed=result[7],
        gold_earned=result[8],
        damage_to_champions=result[9],
        game_end=result[10],
        win=result[11],
    )
