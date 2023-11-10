import flask
from flask import request, jsonify
import sqlalchemy as db
import pandas as pd
import datetime
import asyncio
import websockets
import socket
import time
import threading
import json
import os
from http import HTTPStatus
from flask import Response

from ServerConnection import ServerConnection

host,port ="0.0.0.0", 5000
dbstr=f"mysql+pymysql://{os.environ['DB_USER']}:{os.environ['DB_PASS']}@{os.environ['DB_HOST']}/{os.environ['DB_NAME']}"
print(dbstr)
engine = db.create_engine(dbstr)
connection = engine.connect()
metadata = db.MetaData()

users = db.Table('users', metadata,
              db.Column('id', db.String(255),nullable=False),
              db.Column('password', db.String(255), nullable=False),
              db.Column('active', db.Boolean(), default=False)
              )

messages = db.Table('messages', metadata,
              db.Column('srcId', db.String(255),nullable=False),
              db.Column('dstId', db.String(255), nullable=False),
              db.Column('msg', db.String(255), nullable=False),
              db.Column('send', db.Boolean(), default=False),
              db.Column('red', db.Boolean(), default=False),
              db.Column('time', db.String(255), nullable=False)
              )

metadata.create_all(engine)

query=db.select([users]).where(users.columns.id == "qwe")
resultProxy = connection.execute(query)
resultSet = resultProxy.fetchall()
if (len(resultSet)==0):
    query = db.insert(users).values(id="qwe", password="rty")
    resultProxy = connection.execute(query)

query=db.select([users]).where(users.columns.id == "asd")
resultProxy = connection.execute(query)
resultSet = resultProxy.fetchall()
if (len(resultSet)==0):
    query = db.insert(users).values(id="asd", password="fgh")
    resultProxy = connection.execute(query)

query=db.update(users).values(active = False)
resultProxy = connection.execute(query)

"""query=db.select([messages])
resultProxy = connection.execute(query)
resultSet = resultProxy.fetchall()
print(resultSet)"""



def verifyUser(id,password):
    if((id=="") or (password=="")):
        return False

    connection = engine.connect()
    query=db.select([users]).where(users.columns.id == id)
    resultProxy = connection.execute(query)
    resultSet = resultProxy.fetchall()
    
    if (len(resultSet)==0):
        return False
    
    if(str((resultSet[0]["id"])==str(id)) and (str(resultSet[0]["password"])==str(password))):
        return True


class Server():

    def mainLoop(self):
        threads=[]
        tLock=threading.Lock()
        server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        server.bind((host, port))
        server.listen(5)
        self.connections={}
        while(True):
            client, addr = server.accept()
            threads.append(ServerConnection(self,client,tLock))
            threads[-1].start()

    def api_register_user(self,sc,data):
        id=data["userId"]
        password=data["password"]
        if((id=="") or (password=="")):
            data="Error: No id or password provided. Please specify an id and password."
            data={"action":"register","data":data}
            sc.send(data)
            return

        connection = engine.connect()
        query=db.select([users]).where(users.columns.id == id)
        resultProxy = connection.execute(query)
        resultSet = resultProxy.fetchall()
        
        if (len(resultSet)>0):
            data="Id not available. Please select different ID"
            data={"action":"register","data":data}
            sc.send(data)
        else:
            query = db.insert(users).values(id=id, password=password, active=True)
            resultProxy = connection.execute(query)
            self.connections[data["userId"]]=sc
            data="Registered successfully"
            data={"action":"register","data":data}
            sc.send(data)
            self.connectionsGetUsers()


    def api_login_user(self,sc,data):
        id=data["userId"]
        password=data["password"]
        if((id=="") or (password=="")):
            data="Error: No id or password provided. Please specify an id and password."
            data={"action":"login","data":data}
            sc.send(data)
            return

        connection = engine.connect()
        query=db.select([users]).where(users.columns.id == id)
        resultProxy = connection.execute(query)
        resultSet = resultProxy.fetchall()
        
        if (len(resultSet)==0):
            data="User does not exist"
            data={"action":"login","data":data}
            sc.send(data)
            return
        
        if((resultSet[0]["id"]!=id) or (resultSet[0]["password"]!=password)):
            data="wrong login or password"
            data={"action":"login","data":data}
            sc.send(data)
            return
        
        query=db.update(users).values(active = True).where(users.columns.id==id)
        resultProxy = connection.execute(query)
        self.connections[data["userId"]]=sc
        #print(self.connections.keys())
        data="Login successfull"
        data={"action":"login","data":data}
        sc.send(data)
        self.connectionsGetUsers()

    def api_logout_user(self,sc,data):
        id=data["userId"]
        if(not verifyUser(id,data["password"])):
            data="User not recognised"
            data={"action":"logout","data":data}
            sc.send(data)
            return

        connection = engine.connect()
        query=db.update(users).values(active = False).where(users.columns.id==id)
        resultProxy = connection.execute(query)
        self.connections.pop(data["userId"])
        data="Logout successfull"
        data={"action":"logout","data":data}
        sc.send(data)
        self.connectionsGetUsers()


    def api_get_users(self,sc,data):
        connection = engine.connect()
        query=db.select([users])
        resultProxy = connection.execute(query)
        resultSet = resultProxy.fetchall()
        res=[]
        for u in resultSet:
            query=db.select([messages])
            query=query.where(db.and_(messages.columns.red == False
                , db.and_(messages.columns.dstId == data["userId"],messages.columns.srcId == u[0])))
            resultProxy = connection.execute(query)
            count = len(resultProxy.fetchall())
            res.append({"userId":u[0],"active":u[2],"count":count})
        data={"action":"getUsers","data":res}
        sc.send(data)


    def api_unred_count(self,sc,data):
        connection = engine.connect()
        query=db.select([messages])
        query=query.where(db.and_(messages.columns.red == False
            , db.and_(messages.columns.dstId == data["userId"],messages.columns.srcId == data["srcId"])))
        resultProxy = connection.execute(query)
        resultSet = resultProxy.fetchall()
        res=len(resultSet)
        data={"action":"getUsers","data":res}
        sc.send(data)


    def api_message_history(self,sc,data):
        if(not verifyUser(data["userId"], data["password"])):
            data="User not valid"
            data={"action":"messageHistory","data":data}
            sc.send(data)
            return

        connection = engine.connect()
        query=db.select([messages])
        query=query.where(db.or_(db.and_(messages.columns.red == True
            ,messages.columns.dstId == data["userId"],messages.columns.srcId == data["chatId"])
            ,db.and_(messages.columns.dstId == data["chatId"],messages.columns.srcId == data["userId"])))
        resultProxy = connection.execute(query)
        resultSet = resultProxy.fetchall()

        print(resultSet)
        res=[]
        for msg in resultSet:
            res.append({"srcId":msg[0],"dstId":msg[1],"msg":msg[2],"red":msg[4],"time":msg[5]})
        data={"action":"recieve","data":res[-data["count"]:]}
        sc.send(data)


    def api_recieve(self,sc,data):
        if(not verifyUser(data["userId"], data["password"])):
            data="User not valid"
            data={"action":"recieve","data":data}
            sc.send(data)
            return

        connection = engine.connect()
        query=db.select([messages])
        query=query.where(db.and_(messages.columns.red == False
            , db.and_(messages.columns.dstId == data["userId"],messages.columns.srcId == data["srcId"])))
        resultProxy = connection.execute(query)
        resultSet = resultProxy.fetchall()

        """query=db.update(messages).values(send = True).where(db.and_(messages.columns.send == False
            , messages.columns.dstId == data["userId"]))
        resultProxy = connection.execute(query)"""

        #print(resultSet)
        res=[]
        for msg in resultSet:
            res.append({"srcId":msg[0],"dstId":msg[1],"msg":msg[2],"red":msg[4],"time":msg[5]})
        data={"action":"recieve","data":res}
        sc.send(data)


    def api_mark_red(self,sc,data):
        if(not verifyUser(data["userId"], data["password"])):
            data="User not valid"
            data={"action":"markRed","data":data}
            sc.send(data)
            return

        connection = engine.connect()
        query=db.select([messages])

        query=db.update(messages).values(red = True).where(db.and_(messages.columns.srcId == data["srcId"]
            , db.and_(messages.columns.dstId == data["dstId"],messages.columns.time == data["time"])))
        resultProxy = connection.execute(query)

        #print(resultSet)
        data="marked as red"
        data={"action":"markRed","data":data}
        sc.send(data)
        self.connectionsGetUsers()


    def api_send(self,sc,data):
        if(not verifyUser(data["userId"], data["password"])):
            data="User not valid"
            data={"action":"send","data":data}
            sc.send(data)
            return

        connection = engine.connect()
        query = db.insert(messages).values(srcId=data["userId"]
            ,dstId=data["dstUserId"],msg=data["msg"],time=data["time"])
        resultProxy = connection.execute(query)
        
        if data["dstUserId"] in self.connections:
            data={"srcId":data["userId"],"dstId":data["dstUserId"],"msg":data["msg"],"red":False,"time":data["time"]}
            data={"action":"recieve","data":[data]}
            self.connections[data["data"][0]["dstId"]].send(data)

        data="message send"
        data={"action":"send","data":data}
        sc.send(data)
        self.connectionsGetUsers()


    def api_send_everyone(self,sc,data):
        if(not verifyUser(data["userId"], data["password"])):
            data="User not valid"
            data={"action":"sendEveryone","data":data}
            sc.send(data)
            return

        connection = engine.connect()
        query=db.select([users])
        resultProxy = connection.execute(query)
        resultSet = resultProxy.fetchall()
        msgList=[]
        for u in resultSet:
            if(u[0]!=data["userId"]):
                msgList.append({"srcId":data["userId"],"dstId":u[0],"msg":data["msg"]})
        query = db.insert(messages)
        resultProxy = connection.execute(query,msgList)
        data="messages send"
        data={"action":"sendEveryone","data":data}
        sc.send(data)
        self.connectionsGetUsers()


    def connectionsGetUsers(self):
        connection = engine.connect()
        query=db.select([users])
        resultProxy = connection.execute(query)
        resultSet = resultProxy.fetchall()
        for usrc in self.connections.keys():
            res=[]
            for u in resultSet:
                query=db.select([messages])
                query=query.where(db.and_(messages.columns.red == False
                    , db.and_(messages.columns.dstId == usrc,messages.columns.srcId == u[0])))
                resultProxy = connection.execute(query)
                count = len(resultProxy.fetchall())
                res.append({"userId":u[0],"active":u[2],"count":count})
            data={"action":"getUsers","data":res}
            self.connections[usrc].send(data)

health=True

app = flask.Flask(__name__)
app.config["DEBUG"] = False

@app.route('/', methods=['GET','post'])
def home():
    return '''<h1>Messenge server</h1>
<p>hello</p>'''

@app.route('/chkHealth', methods=['GET'])
def chkHealth():
    print(health)
    if(health):     return ""
    else:   
        print("killed")
        return "",500

@app.route('/kill', methods=['GET','post'])
def killServer():
    #os._exit(1)
    global health
    health=False
    return '''<h1>Killed server</h1>'''
        
def runApi():
    app.run(host="0.0.0.0",port=5002)

threading.Thread(target=runApi).start()

Server().mainLoop()




