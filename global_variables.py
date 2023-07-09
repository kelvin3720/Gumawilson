import os
from sys import platform
from tzlocal import get_localzone

# CONSTANT
if platform == "linux":
    DISCORD_TOKEN = os.environ["GUMAWILSON_DISCORD_TOKEN"]
    RIOT_API_KEY = os.environ["GUMAWILSON_RIOT_API_KEY"]
elif platform == "win32":
    DISCORD_TOKEN = os.getenv("GUMAWILSON_DISCORD_TOKEN")
    RIOT_API_KEY = os.getenv("GUMAWILSON_RIOT_API_KEY")
DEFAULT_PERIOD_LIST = [
    "today",
    "yesterday",
    "last_week",
    "last_month",
    "this_week",
    "this_month",
    "last_n_days",
]
REGION_V4_LIST = [
    "br1",
    "eun1",
    "euw1",
    "jp1",
    "kr",
    "la1",
    "la2",
    "na1",
    "oc1",
    "tr1",
    "ru",
    "ph2",
    "sg2",
    "th2",
    "tw2",
    "vn2",
]
REGION_V5_LIST = ["americas", "asia", "europe", "sea"]


## Global variables

# Summoner name
default_summoner_name = ""
# For SUMMONER-V4 API
region_v4 = "tw2"
# For MATCH-V5 API
region_v5 = "sea"
# In DEFAULT_PERIOD_LIST
default_period = "today"
# Timezone
local_timezone = str(get_localzone())


# For sql
database = "gumawilson"
database_host = "localhost"
if platform == "linux":
    sql_user = os.environ["GUMAWILSON_SQL_AC"]
    sql_password = os.environ["GUMAWILSON_SQL_PW"]
elif platform == "win32":
    sql_user = os.getenv("GUMAWILSON_SQL_AC")
    sql_password = os.getenv("GUMAWILSON_SQL_PW")
