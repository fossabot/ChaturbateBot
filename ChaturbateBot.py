# -*- coding: utf-8 -*-
import telebot
import os
import time
import urllib.request
import os.path
import argparse
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
from requests_futures.sessions import FuturesSession
ap = argparse.ArgumentParser()
ap.add_argument("-k", "--key", required=True,type=str,
        help="Telegram bot key")
ap.add_argument("-f", "--working-folder", required=False,type=str,default=os.getcwd(),
        help="set the bot's working-folder")
ap.add_argument("-t", "--time", required=False,type=int,default=10,
        help="time wait between every end of the check_online_status thread")
ap.add_argument("-raven",required=False,type=str,default="",help="Raven client key")
args = vars(ap.parse_args())
bot = telebot.AsyncTeleBot(args["key"])
bot_path=args["working_folder"]
wait_time=args["time"]
raven_key=args["raven"]
if raven_key!="":
    from raven import Client
    client = Client(raven_key)
    def handle_exception(e):
        client.captureException()
else:
    def handle_exception(e):
        print(str(e))
def risposta(sender, messaggio):
    try:
     bot.send_chat_action(sender, action="typing")
     bot.send_message(sender, messaggio)
    except Exception as e:
        handle_exception(e)
def exec_query(query):
 # Open database connection
 db = sqlite3.connect(bot_path+'/database.db')
 # prepare a cursor object using cursor() method
 cursor = db.cursor()
 # Prepare SQL query to INSERT a record into the database.
 try:
   # Execute the SQL command
   cursor.execute(query)
   # Commit your changes in the database
   db.commit()
 except Exception as e:
   # Rollback in case there is any error
   handle_exception(e)
   db.rollback()
 # disconnect from server
 db.close()
 #default table creation
exec_query("""CREATE TABLE IF NOT EXISTS CHATURBATE (
        USERNAME  CHAR(60) NOT NULL,
        CHAT_ID  CHAR(100),
        ONLINE CHAR(1))""")
def check_online_status():
    while(1):
        username_list=[]
        chatid_list=[]
        online_list=[]
        response_list=[]
        sql = "SELECT * FROM CHATURBATE"
        try:
            db = sqlite3.connect(bot_path+'/database.db')
            cursor = db.cursor()
            cursor.execute(sql)
            results = cursor.fetchall()
            for row in results:
                username_list.append(row[0])
                chatid_list.append(row[1])
                online_list.append(row[2])
        except Exception as e:
                handle_exception(e)
        finally:
                db.close()
        session = FuturesSession(executor=ThreadPoolExecutor(max_workers=int(len(username_list))))
        for x in range(0,len(username_list)):
            try:
             response = ((session.get("https://it.chaturbate.com/api/chatvideocontext/"+username_list[x])).result()).content
            except Exception as e:
              handle_exception(e)
              response="error"
            response_list.append(response)
        for x in range(0,len(response_list)):
            try:
             if (b"offline" in response_list[x]):
                if online_list[x]=="T":
                    exec_query("UPDATE CHATURBATE \
                    SET ONLINE='{}'\
                    WHERE USERNAME='{}' AND CHAT_ID='{}'".format("F",username_list[x],chatid_list[x]))
                    risposta(chatid_list[x], username_list[x]+" is now offline")
             elif online_list[x]=="F":
                risposta(chatid_list[x], username_list[x]+" is now online! You can watch the live here: http://en.chaturbate.com/"+username_list[x]) #the 1 is to replace only the 1st occurrence, otherwise the username in the target may get overwritten
                exec_query("UPDATE CHATURBATE \
                SET ONLINE='{}'\
                WHERE USERNAME='{}' AND CHAT_ID='{}'".format("T",username_list[x],chatid_list[x]))
            except Exception as e:
                handle_exception(e)
        time.sleep(wait_time)
def telegram_bot():
 @bot.message_handler(commands=['start', 'help'])
 def handle_start_help(message):
     risposta(message.chat.id,"/add username to add an username to check \n/remove username to remove an username \n/list to see which users you are currently following")
 @bot.message_handler(commands=['add'])
 def handle_add(message):
    print("add")
    try:
        if len(message.text.split(" "))<2:
            risposta(message.chat.id, "You may have made a mistake, check your input and try again")
            return
        username=message.text.split(" ")[1]
    except Exception as e:
        handle_exception(e)
        username="" #set username to a blank string
    try:
     chatid=message.chat.id
     target="http://it.chaturbate.com/"+username
     req = urllib.request.Request(target, headers={'User-Agent': 'Mozilla/5.0'})
     html = urllib.request.urlopen(req).read()
     if (b"Access Denied. This room has been banned.</span>" in html or username==""):
          risposta(message.chat.id, username+" was not added because it doesn't exist or it has been banned.\nIf you are sure it exists, you may want to try the command again")
     else:
          username_list=[]
          db = sqlite3.connect(bot_path+'/database.db')
          cursor = db.cursor()
          sql = "SELECT * FROM CHATURBATE \
          WHERE CHAT_ID='{}'".format(chatid)
          try:
           cursor.execute(sql)
           results = cursor.fetchall()
           for row in results:
             username_list.append(row[0])
          except Exception as e:
             handle_exception(e)
          finally:
             db.close()
          if username not in username_list:
           exec_query("INSERT INTO CHATURBATE \
           VALUES ('{}', '{}', '{}')".format(username, chatid, "F"))
           risposta(message.chat.id,username+" has been added")
          else:
           risposta(message.chat.id, username+" has already been added")
    except Exception as e:
        handle_exception(e)
        risposta(message.chat.id, username+" was not added because it doesn't exist or it has been banned")
 @bot.message_handler(commands=['remove'])
 def handle_remove(message):
    print("remove")
    try:
        chatid=message.chat.id
        if len(message.text.split(" "))<2:
            risposta(message.chat.id, "You may have made a mistake, check your input and try again")
            return
        username=message.text.split(" ")[1]
    except Exception as e:
        handle_exception(e)
        username="" #set username to a blank string
        chatid="" #set chatid to a blank string
    exec_query("DELETE FROM CHATURBATE \
     WHERE USERNAME='{}' AND CHAT_ID='{}'".format(username, chatid))
    if username=="":
        risposta(message.chat.id, "The username you tried to remove doesn't exist or there has been an error")
    else:
        risposta(message.chat.id,username+" has been removed")
 @bot.message_handler(commands=['list'])
 def handle_list(message):
   chatid=message.chat.id
   username_list=[]
   online_list=[]
   followed_users=""
   db = sqlite3.connect(bot_path+'/database.db')
   cursor = db.cursor()
   sql = "SELECT * FROM CHATURBATE \
   WHERE CHAT_ID='{}'".format(chatid)
   try:
       cursor.execute(sql)
       results = cursor.fetchall()
       for row in results:
           username_list.append(row[0])
           online_list.append(row[2])
   except Exception as e:
           handle_exception(e)
   else: #else means that the code will get executed if an exception doesn't happen
    for x in range(0,len(username_list)):
       followed_users+=username_list[x]+": "
       if online_list[x]=="T":
           followed_users+="online\n"
       else:
           followed_users+="offline\n"
   finally:
       db.close()
   if followed_users=="":
       risposta(message.chat.id,"You aren't following any user")
   else:
       risposta(message.chat.id,"These are the users you are currently following:\n"+followed_users)
 while True:
     try:
         bot.polling(none_stop=True)
     except Exception as e:
         handle_exception(e)
threads = []
check_online_status_thread = threading.Thread(target=check_online_status)
telegram_bot_thread = threading.Thread(target=telegram_bot)
threads.append(check_online_status_thread)
threads.append(telegram_bot_thread)
check_online_status_thread.start()
telegram_bot_thread.start()
