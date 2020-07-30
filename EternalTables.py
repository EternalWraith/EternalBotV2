import os

DATABASE_URL = os.environ['DATABASE_URL']


def SetupConfigTable(cursor, conn, delete=False):

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
    -- Lang VARCHAR(255)
)
""")
    conn.commit()

    if (delete):
        print("Table created")


def SetupLobbyTable(cursor, conn, delete=False):

    if (delete):
        cursor.execute("""
DROP TABLE IF EXISTS Lobbies;
""")
        conn.commit()
        print("Table dropped")

    cursor.execute("""
CREATE TABLE IF NOT EXISTS Lobbies (
    ID SERIAL PRIMARY KEY,
    ServerID VARCHAR(255),
    VCID VARCHAR(255),
    OwnerID VARCHAR(255)
)
""")
    conn.commit()

    if (delete):
        print("Table created")


def SetupTicketTable(cursor, conn, delete=False):

    if (delete):
        cursor.execute("""
DROP TABLE IF EXISTS Tickets;
""")
        conn.commit()
        print("Table dropped")

    cursor.execute("""
CREATE TABLE IF NOT EXISTS Tickets (
    ID SERIAL PRIMARY KEY,
    ServerID VARCHAR(255),
    OwnerID VARCHAR(255),
    ChannelID VARCHAR(255),
    EndingID VARCHAR(255)
)
""")
    conn.commit()

    if (delete):
        print("Table created")


def SetupLevelTable(cursor, conn, delete=False):

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

    if (delete):
        print("Table created")
