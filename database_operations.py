import os
from typing import List, Tuple
import mysql.connector


db = mysql.connector.connect(
    host="localhost",
    user=os.getenv("GUMAWILSON_SQL_AC"),
    password=os.getenv("GUMAWILSON_SQL_PW"),
    database="gumawilson",
)


# Call a stored procedure with no return
def call_stored_procedure_no_return(
    procedure_name: str, params: tuple
) -> None:
    cursor = db.cursor()
    cursor.callproc(procedure_name, params)
    db.commit()
    cursor.close()


# Call a stored procedure with return valie
def call_stored_procedure_with_return(
    procedure_name: str, params: tuple
) -> list | bool:
    cursor = db.cursor()
    result = cursor.callproc(procedure_name, params)
    cursor.close()
    return result


# Add new summoner to summoners table
def add_summoner(summoner_name: str, summoner_id: str, puuid: str) -> None:
    params = (summoner_name, summoner_id, puuid)
    call_stored_procedure_no_return("sp_add_new_summoner", params)


# Check if summoner already exist in summoners table by puuid
def summoner_exists(puuid: str) -> None:
    params = (puuid, 0)
    result = call_stored_procedure_with_return("sp_summoner_exists", params)
    # Return body: (puuid, 1|0)
    return bool(result[1])


# Check if match exists in database
def match_exists(match_id) -> bool:
    params = (match_id, 0)
    result = call_stored_procedure_with_return("sp_match_exists", params)
    # Return body: (puuid, 1|0)
    return bool(result[1])


# Find the match ids which is not in the database
def get_match_ids_not_in_db(id_list: list) -> List[str]:
    not_exist = []
    for id in id_list:
        if not match_exists(id):
            not_exist.append(id)

    return not_exist


# Insert given data to matches table
def insert_to_matches(data_list) -> None:
    params = tuple(data_list)
    call_stored_procedure_no_return("sp_add_new_match", params)


# Insert data to match_players table from API result
def insert_to_match_players(api_result: dict) -> None:
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


# Count the number of wins and losses from match_id_list and puuid
def count_win_lose(match_id_list: List[str], puuid: str) -> Tuple[int, int]:
    wins = 0
    losses = 0

    for id in match_id_list:
        params = (id, puuid, 0)
        if call_stored_procedure_with_return("sp_check_is_win", params)[2]:
            wins += 1
        else:
            losses += 1

    return wins, losses
