import os
import mysql.connector
from mysql.connector import errorcode

cnx = None


def connect_to_db():
    global cnx
    try:
        cnx = mysql.connector.connect(user=os.getenv("MYSQL_USER"),
                                      password=os.getenv("MYSQL_PASSWORD"),
                                      host=os.getenv("MYSQL_HOST"),
                                      database=os.getenv("MYSQL_DATABASE"),
                                      connection_timeout=300)
        if cnx.is_connected():
            print("Connected to MySQL database")
            return cnx
    except mysql.connector.Error as err:
        print(f"Error: '{err}'")
        return None


def ensure_connection():
    """Ensure the database connection is active, and reconnect if needed."""
    global cnx
    if cnx is None or not cnx.is_connected():
        print("🔄 Reconnecting to MySQL...")
        cnx = connect_to_db()
        if cnx is None:
            print("❌ Failed to reconnect to MySQL")
            return None
    return cnx


def close_db():
    global cnx
    if cnx and cnx.is_connected():
        print("Closing connection to MySql")
        cnx.close()
        cnx = None


def start_game_session(user_id, username, game_name):
    global cnx
    cnx = connect_to_db()
    if cnx is None:
        return

    cursor = cnx.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO GameSessions (user_id, username, game_name)
            VALUES (%s, %s, %s);
        """, (user_id, username, game_name))
        cnx.commit()
        print(f"Started session for {username} playing {game_name}")
    except mysql.connector.Error as err:
        print(f"❌ Database Error: {err}")
    finally:
        cursor.close()
        close_db()


def end_game_session(user_id, game_name):
    cnx = connect_to_db()
    if cnx is None:
        return

    cursor = cnx.cursor()
    try:
        cursor.execute(
            """
            UPDATE GameSessions
            SET end_time = NOW(), 
                duration = TIMESTAMPDIFF(MINUTE, start_time, NOW())
            WHERE user_id = %s AND game_name = %s AND end_time IS NULL
            order by start_time desc
            LIMIT 1;
        """, (user_id, game_name))
        cnx.commit()
        print(f"✅ Ended session for {user_id} playing {game_name}")
    except mysql.connector.Error as err:
        print(f"❌ Database Error: {err}")
    finally:
        cursor.close()
        close_db()


def get_top_3_players(game_name):
    cnx = ensure_connection()
    if cnx is None:
        return

    cursor = cnx.cursor()
    try:
        cursor.execute(
            """
            SELECT username, SUM(duration) AS total_playtime
            FROM GameSessions
            WHERE game_name = %s
            AND end_time >= NOW() - INTERVAL 7 DAY
            GROUP BY user_id
            ORDER BY total_playtime DESC
            LIMIT 3;
        """, (game_name, ))

        top_players = cursor.fetchall()
        for rank, (username, playtime) in enumerate(top_players, start=1):
            print(f"{rank}. {username} - {playtime} seconds")
    except mysql.connector.Error as err:
        print(f"❌ Database Error: {err}")
    finally:
        cursor.close()
