import os
import mysql.connector
from mysql.connector import errorcode

def connect_to_db():
    try:
        cnx = mysql.connector.connect(user=os.getenv("MYSQL_USER"),
                                      password=os.getenv("MYSQL_PASSWORD"),
                                      host=os.getenv("MYSQL_HOST"),
                                      database=os.getenv("MYSQL_DATABASE"),
                                      connection_timeout=300)
        if cnx.is_connected():
            print("Connected to MySQL database")
            return cnx
    except Exception as err:
        print(f"Error: '{err}'")
        return None

def close_db(cnx):
    if cnx.is_connected():
        print("Closing connection to MySql")
        cnx.close()
        cnx = None


def start_game_session(user_id, username, game_name):
    try:
        cnx = connect_to_db()
        if cnx is None:
            return

        cursor = cnx.cursor()
        cursor.execute(
            """
            INSERT INTO GameSessions (user_id, username, game_name)
            VALUES (%s, %s, %s);
        """, (user_id, username, game_name))
        cnx.commit()
        print(f"Started session for {username} playing {game_name}")
    except Exception as err:
        print(f"❌ Database Error: {err}")
    finally:
        cursor.close()
        close_db(cnx)


def end_game_session(user_id, game_name):
    try:
        cnx = connect_to_db()
        if cnx is None:
            return
        cursor = cnx.cursor()
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
        close_db(cnx)

async def get_rankings(days: int):
    """
    Queries the database for rankings for the past `days` days.
    Returns a formatted string with the rankings.
    """
    try:
        cnx = connect_to_db()
        if cnx is None:
            return "Database connection error."
    
        rank_message = f"**🏆 Rankings for the past {days} day(s) 🏆**\n\n"
        cursor = cnx.cursor()
        # Use the days parameter in the SQL query.
        query = f"""
            SELECT user_id, username, game_name, SUM(duration) AS total_playtime
            FROM GameSessions
            WHERE end_time >= NOW() - INTERVAL {days} DAY
            GROUP BY user_id, username, game_name
            ORDER BY total_playtime DESC
            LIMIT 3;
        """
        cursor.execute(query)
        top_players = cursor.fetchall()
        if not top_players:
            rank_message += "No rankings available."
        else:
            for rank, (user_id, username, game_name, total_playtime) in enumerate(top_players, start=1):
                rank_message += f"**{rank}.** **{username}** played *{game_name}* for `{total_playtime} minutes`\n"
        return rank_message
    except Exception as err:
        return f"Error fetching rankings: {err}"
    finally:
        cursor.close()
        close_db(cnx)

async def get_top_3_players(general_channel):
    rank_message = "**🏆 Weekly Top Players 🏆**\n\n"
    try:
        cnx = connect_to_db()
        if cnx is None:
            return
        cursor = cnx.cursor()
        cursor.execute("""
            SELECT user_id, username, game_name, SUM(duration) AS total_playtime
            FROM GameSessions
            WHERE end_time >= NOW() - INTERVAL 7 DAY
            GROUP BY user_id, username, game_name
            ORDER BY total_playtime DESC
            LIMIT 3;
        """)

        top_players = cursor.fetchall()
        for rank, (user_id, username, game_name, total_playtime) in enumerate(top_players, start=1):
            rank_message += f"**{rank}.** **{username}** played *{game_name}* for `{total_playtime} minutes`\n"
        await general_channel.send(rank_message)
    except mysql.connector.Error as err:
        print(f"❌ Database Error: {err}")
    finally:
        cursor.close()
        close_db(cnx)
