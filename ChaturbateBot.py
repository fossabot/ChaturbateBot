# -*- coding: utf-8 -*-
import telebot
import requests
import os
import time
import urllib.request
import os.path
import argparse
#import instaLooter as instalooter
from telebot import types
from telebot import util
from bs4 import BeautifulSoup
import MySQLdb
import threading
ap = argparse.ArgumentParser()
ap.add_argument("-k", "--key", required=True,type=str,
        help="Telegram bot key")
ap.add_argument("-ip", required=True,type=str,
        help="Ip address of the database")
ap.add_argument("-l", "--login", required=True,type=str,
        help="login username of the database")
ap.add_argument("-p", "--password", required=False,type=str,default="",
        help="password of the database")
ap.add_argument("-n", "--db-name", required=True,type=str,
        help="name of the database")
ap.add_argument("-f", "--working-folder", required=False,type=str,default=os.getcwd(),
        help="set the bot's working-folder")
args = vars(ap.parse_args())
bot = telebot.TeleBot(args["key"])
user_dict={}
bot_path=args["working_folder"]
db_ip=args["ip"]
db_login=args["login"]
db_password=args["password"]
db_name=args["db_name"]
def risposta(sender, messaggio):
    bot.send_chat_action(sender.chat.id, action="typing")
    bot.send_message(sender.chat.id, messaggio)
def exec_query(query):
 # Open database connection
 db = MySQLdb.connect(db_ip,db_login,db_password,db_name)
 # prepare a cursor object using cursor() method
 cursor = db.cursor()
 # Prepare SQL query to INSERT a record into the database.
 try:
   # Execute the SQL command
   cursor.execute(query)
   # Commit your changes in the database
   db.commit()
 except:
   # Rollback in case there is any error
   db.rollback()
 # disconnect from server
 db.close()
#inizializzatione tabella se non esiste
exec_query("""CREATE TABLE CHATURBATE (
        USERNAME  CHAR(60) NOT NULL,
        CHAT_ID  CHAR(100),
        ONLINE CHAR(1))""")

def check_online_status():
    while(1):
        username_list=[]
        chatid_list=[]
        online_list=[]
        db = MySQLdb.connect(db_ip,db_login,db_password,db_name)
        cursor = db.cursor()
        sql = "SELECT * FROM CHATURBATE"
        try:
            cursor.execute(sql)
            results = cursor.fetchall()
            for row in results:
                username_list.append(row[0])
                chatid_list.append(row[1])
                online_list.append(row[2])
        except Exception as e:
                print (e)
        finally:
                db.close()
        for x in range(0,len(username_list)):
            target="http://it.chaturbate.com/"+username_list[x]
            req = urllib.request.Request(target, headers={'User-Agent': 'Mozilla/5.0'})
            html = urllib.request.urlopen(req).read()
            if (b"al momento offline</strong>" in html):
                exec_query("UPDATE CHATURBATE \
                 SET ONLINE=%s\
                  WHERE USERNAME=%s AND CHAT_ID=%s"%("F",username_list[x],chatid_list[x]))
                if online_list[x]=="T":
                     risposta(chatid_list[x], username_list[x]+" is now offline")
            elif online_list[x]=="F":
                risposta(chatid_list[x], username_list[x]+" is now online! You can watch the live here: "+target.replace("it","en",1)) #the 1 is to replace only the 1st occurrence, otherwise the username in the target may get overwritten
                exec_query("UPDATE CHATURBATE \
                 SET ONLINE=%s\
                  WHERE USERNAME=%s AND CHAT_ID=%s"%("T",username_list[x],chatid_list[x]))
        time.sleep(10)
def obtain_usernames():
 @bot.message_handler(commands=['start', 'help'])
 def handle_start_help(message):
    risposta(message,"/add username to add an username to check \n/remove username to remove an username \n/list to see which users you are currently following")
 @bot.message_handler(commands=['add'])
 def handle_add(message):
    print("add")
    try:
        username=message.text.split(" ")[1]
    except Exception as e:
        print(e)
        username="" #set username to a blank string
    chatid=message.chat.id
    target="http://it.chaturbate.com/"+username
    req = urllib.request.Request(target, headers={'User-Agent': 'Mozilla/5.0'})
    try:
     html = urllib.request.urlopen(req).read()
     if (b"Access Denied. This room has been banned.</span>" in html or username==""):
          risposta(message, username+" was not added because it doesn't exist or it has been banned.\nIf you are sure it exists, you may want to try the command again")
     else:
          username_list_add=[]
          db_add = MySQLdb.connect(db_ip,db_login,db_password,db_name)
          cursor_add = db_add.cursor()
          sql = "SELECT * FROM CHATURBATE \
          WHERE CHAT_ID=%s"%(chatid)
          try:
           cursor_add.execute(sql)
           results_add = cursor_add.fetchall()
           for row in results_add:
             username_list_add.append(row[0])
          except Exception as e:
             print(e)
          finally:
             db_add.close()
          if username not in username_list_add:
           exec_query("INSERT INTO CHATURBATE \
           VALUES (%s, %s, %c)" %(username, chatid, "F"))
           risposta(message,username+" has been added")
          else:
           risposta(message, username+" has already been added")
    except Exception as e:
        print(e)
        risposta(message, username+" was not added because it doesn't exist or it has been banned")
 @bot.message_handler(commands=['remove'])
 def handle_remove(message):
    print("remove")
    try:
        username=message.text.split(" ")[1]
    except Exception as e:
        print(e)
        username="" #set username to a blank string
    chatid=message.chat.id
    exec_query("DELETE FROM CHATURBATE \
     WHERE USERNAME=%s AND CHAT_ID=%s"%(username, chatid))
    risposta(message,username+" has been removed")
 @bot.message_handler(commands=['list'])
 def handle_list(message):
   chatid=message.chat.id
   username_list_list=[]
   followed_users=""
   db_list = MySQLdb.connect(db_ip,db_login,db_password,db_name)
   cursor_list = db_list.cursor()
   sql = "SELECT * FROM CHATURBATE \
   WHERE CHAT_ID=%s" %(chatid)
   try:
       cursor_list.execute(sql)
       results_list = cursor_list.fetchall()
       for row in results_list:
           username_list_list.append(row[0])
   except Exception as e:
           print (e)
   finally:
           db_list.close()
           for x in range(0,len(username_list_list)):
               followed_users+=username_list_list[x]+","
           followed_users=followed_users[:-1]
           risposta(message,"These are the users you are currently following: "+followed_users)
 bot.polling(none_stop=False)
threads = []
t = threading.Thread(target=check_online_status)
e = threading.Thread(target=obtain_usernames)
threads.append(t)
threads.append(e)
t.start()
e.start()
