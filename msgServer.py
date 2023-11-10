
import flask
from flask import request, jsonify
import sqlalchemy as db
import pandas as pd

engine = db.create_engine('sqlite:///msgServer.db')
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
              db.Column('send', db.Boolean(), default=False)
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


app = flask.Flask(__name__)
app.config["DEBUG"] = True

@app.route('/', methods=['GET','post'])
def home():
    return '''<h1>Messenge server</h1>
<p>hello</p>'''


@app.route('/api/users/all', methods=['GET'])
def api_users_all():
    connection = engine.connect()
    query=db.select([users])
    resultProxy = connection.execute(query)
    resultSet = resultProxy.fetchall()
    res=[]
    for u in resultSet:
        res.append({"userId":u[0],"active":u[2]})
    return jsonify(res)


@app.route('/api/users/register', methods=['POST'])
def api_register_user():
    data=request.form
    id=data["userId"]
    password=data["password"]
    if((id=="") or (password=="")):
        return "Error: No id or password provided. Please specify an id and password."

    connection = engine.connect()
    query=db.select([users]).where(users.columns.id == id)
    resultProxy = connection.execute(query)
    resultSet = resultProxy.fetchall()
    
    if (len(resultSet)>0):
        return "Id not available. Please select different ID"
    else:
        query = db.insert(users).values(id=id, password=password, active=True)
        resultProxy = connection.execute(query)
        return "Registered successfully"


@app.route('/api/users/login', methods=['POST'])
def api_login_user():
    data=request.form
    id=data["userId"]
    password=data["password"]
    if((id=="") or (password=="")):
        return "Error: No id or password provided. Please specify an id and password."

    connection = engine.connect()
    query=db.select([users]).where(users.columns.id == id)
    resultProxy = connection.execute(query)
    resultSet = resultProxy.fetchall()
    
    if (len(resultSet)==0):
        return "User does not exist"
    
    if((resultSet[0]["id"]!=id) or (resultSet[0]["password"]!=password)):
        return "wrong login or password"
    
    query=db.update(users).values(active = True).where(users.columns.id==id)
    resultProxy = connection.execute(query)
    return "Login successfull"


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


@app.route('/api/users/logout', methods=['POST'])
def api_logout_user():
    data=request.form
    id=data["userId"]
    if(not verifyUser(id,data["password"])):
        return "User not recognised"

    connection = engine.connect()
    query=db.update(users).values(active = False).where(users.columns.id==id)
    resultProxy = connection.execute(query)
    return "Logout successfull"


@app.route('/api/users', methods=['GET'])
def api_user_recieve():
    data=request.form
    if(not verifyUser(data["userId"], data["password"])):
        return "User not valid"

    connection = engine.connect()
    query=db.select([messages])
    query=query.where(db.and_(messages.columns.send == False
        , messages.columns.dstId == data["userId"]))
    resultProxy = connection.execute(query)
    resultSet = resultProxy.fetchall()

    query=db.update(messages).values(send = True).where(db.and_(messages.columns.send == False
        , messages.columns.dstId == data["userId"]))
    resultProxy = connection.execute(query)

    print(resultSet)
    res=[]
    for msg in resultSet:
        res.append({"srcId":msg[0],"dstId":msg[1],"msg":msg[2]})
    return jsonify(res)


@app.route('/api/send', methods=['POST'])
def api_user_send():
    data=request.form
    if(not verifyUser(data["userId"], data["password"])):
        return "User not valid"

    connection = engine.connect()
    query = db.insert(messages).values(srcId=data["userId"], dstId=data["dstUserId"],msg=data["msg"])
    resultProxy = connection.execute(query)
    
    return "message send"


@app.route('/api/send/all', methods=['POST'])
def api_user_send_everone():
    data=request.form
    if(not verifyUser(data["userId"], data["password"])):
        return "User not valid"

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
    return "messages send"


""" 
    for book in books:
        if book['id'] == id:
            results.append(book)
    return jsonify(results)
"""
app.run()