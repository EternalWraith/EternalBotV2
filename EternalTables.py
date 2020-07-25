import discord, os, psycopg2

from discord.ext import commands
from datetime import datetime, timedelta

DATABASE_URL = os.environ['DATABASE_URL']

def CompileLobbies(data):
    output = []
    for D in data:
        lobby = [D.id, data[D]["Channel"].id, data[D]["UserLimit"]]
        output.append(lobby)
    return output

def CompileWhitelist(data):
    output = []
    for D in data:
        output.append(D.id)
    return output

def CompileUsers(data):
    output = []
    for D in data:
        user = [D.id, data[D]["Prestige"], data[D]["Level"], data[D]["XP"]]
        output.append(user)
    return output

def CompileCooldowns(data):
    output = []
    for D in data:
        user = [str(D.id), str(data[D]["Cooldown"]), str(data[D]["Stay"])]
        output.append(user)
    return output

def CompilePrestige(data):
    print("Compiling Prestige List")
    output = []
    for D in data:
        output.append(D.id)
    return output        

def GetData(bot, server):
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    cursor = conn.cursor()
        
    cursor.execute("SELECT * FROM Config WHERE ServerID='{0}'".format(server.id))
    data = cursor.fetchall()[0]
    return InterpretData(bot, data)

def InterpretLevels(bot, data):
    print("Dictating Level Data")
    output = {}
    output["ID"] = data[0]
    output["Server"] = bot.get_guild(int(data[1]))
    output["Enabled"] = data[2]
    if (output["Enabled"]):
        output["Levels"] = {}
        for i in data[3]:
            u = bot.get_user(int(i[0]))
            output["Levels"][u] = {}
            output["Levels"][u]["Prestige"] = int(i[1])
            output["Levels"][u]["Level"] = int(i[2])
            output["Levels"][u]["XP"] = int(i[3])
        for i in data[7]:
            u = bot.get_user(int(i[0]))
            output["Levels"][u]["Cooldown"] = datetime.strptime(i[1], "%Y-%m-%d %H:%M:%S.%f")
            output["Levels"][u]["Stay"] = datetime.strptime(i[2], "%Y-%m-%d %H:%M:%S.%f")
        output["Prestiges"] = []
        output["Cap"] = {}
        output["Cap"]["Mid"] = data[4][0]
        output["Cap"]["Max"] = data[4][1]
        for i in data[5]:
            output["Prestiges"].append(output["Server"].get_role(int(i)))
    output["Gain"] = {}
    output["Gain"]["Text"] = {}
    output["Gain"]["Text"]["Min"] = data[6][0]
    output["Gain"]["Text"]["Max"] = data[6][1]
    output["Gain"]["Voice"] = data[6][2]
    return output
            

def InterpretVC(bot, data):
    output = {}
    output["ID"] = data[0]
    output["Server"] = bot.get_guild(int(data[1]))
    output["VC"] = bot.get_channel(int(data[2]))
    output["Owner"] = bot.get_user(int(data[3]))
    return output

async def InterpretTicket(bot, data):
    output = {}
    output["ID"] = data[0]
    output["Server"] = bot.get_guild(int(data[1]))
    output["Owner"] = bot.get_user(int(data[2]))
    output["Channel"] = bot.get_channel(int(data[3]))
    if not data[4]:
        output["Ending"] = None
    else:
        output["Ending"] = await output["Channel"].fetch_message(int(data[4]))
    return output

def InterpretData(bot, data):
    output = {}
    output["ID"] = data[0]
    output["Server"] = bot.get_guild(int(data[1]))
    output["Audit"] = None if not data[2] else bot.get_channel(int(data[2]))
    output["Prefix"] = data[3]
    output["Lobbies"] = {}
    for L in data[4]:
        category = bot.get_channel(int(L[0]))
        channel = bot.get_channel(int(L[1]))
        limit = int(L[2])
        output["Lobbies"][category] = {}
        output["Lobbies"][category]["Channel"] = channel
        output["Lobbies"][category]["UserLimit"] = limit
    output["Inbox"] = None if not data[5] else bot.get_channel(int(data[5]))
    output["Tickets"] = data[6]
    output["WhiteList"] = []
    for R in data[7]:
        output["WhiteList"].append(output["Server"].get_role(int(R)))

    return output
    
def SetupConfigTable(delete=False):
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    cursor = conn.cursor()

    if (delete):
        cursor.execute("""
DROP TABLE IF EXISTS Config;
""")
        conn.commit()
        print("Table dropped")

    cursor.execute("""
CREATE TABLE IF NOT EXISTS Config (
    ID SERIAL PRIMARY KEY,
    ServerID VARCHAR(255),
    AuditID VARCHAR(255),
    Prefix VARCHAR(255),
    Lobbies VARCHAR(255)[][4],
    TicketID VARCHAR(255),
    "Tickets" int,
    WhiteList VARCHAR(255)[]
)
""")
    conn.commit()

    cursor.close()
    conn.close()

    if (delete):
        print("Table created")


def SetupLobbyTable(delete=False):
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    cursor = conn.cursor()

    if (delete):
        cursor.execute("""
DROP TABLE IF EXISTS LobbyList;
""")
        conn.commit()
        print("Table dropped")

    cursor.execute("""
CREATE TABLE IF NOT EXISTS LobbyList (
    ID SERIAL PRIMARY KEY,
    ServerID VARCHAR(255),
    VCID VARCHAR(255),
    OwnerID VARCHAR(255)
)
""")
    conn.commit()

    cursor.close()
    conn.close()

    if (delete):
        print("Table created")

def SetupTicketTable(delete=False):
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    cursor = conn.cursor()

    if (delete):
        cursor.execute("""
DROP TABLE IF EXISTS TicketList;
""")
        conn.commit()
        print("Table dropped")

    cursor.execute("""
CREATE TABLE IF NOT EXISTS TicketList (
    ID SERIAL PRIMARY KEY,
    ServerID VARCHAR(255),
    OwnerID VARCHAR(255),
    ChannelID VARCHAR(255),
    EndingID VARCHAR(255)
)
""")
    conn.commit()

    cursor.close()
    conn.close()

    if (delete):
        print("Table created")

def SetupLevelTable(delete=False):
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    cursor = conn.cursor()

    if (delete):
        cursor.execute("""
DROP TABLE IF EXISTS Levels;
""")
        conn.commit()
        print("Table dropped")

    cursor.execute("""
CREATE TABLE IF NOT EXISTS Levels (
    ID SERIAL PRIMARY KEY,
    ServerID VARCHAR(255),
    Enabled boolean,
    Users VARCHAR(255)[][3],
    LevelCap int[2],
    Prestiges VARCHAR(255)[],
    XPGain int[][3],
    Cooldowns VARCHAR(255)[][3]
)
""")
    conn.commit()

    cursor.close()
    conn.close()

    if (delete):
        print("Table created")
