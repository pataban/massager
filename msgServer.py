import socket
import threading
import sqlalchemy as sqla

from connectionHandler import ConnectionHandler
from constants import *


activeUsers = {}
clientConnections = []
dbMetadata = sqla.MetaData()
usersTable = sqla.Table(
    "users", dbMetadata,
    sqla.Column("id", sqla.String(USER_ID_LENGTH), nullable=False),
    sqla.Column("password", sqla.String(USER_PASSWORD_LENGTH), nullable=False),
)
messagesTable = sqla.Table(
    "messages", dbMetadata,
    sqla.Column("srcId", sqla.String(USER_ID_LENGTH), nullable=False),
    sqla.Column("dstId", sqla.String(USER_ID_LENGTH), nullable=False),
    sqla.Column("msg", sqla.String(255), nullable=False),
    sqla.Column("read", sqla.Boolean(), default=False),
    sqla.Column("time", sqla.DateTime(), nullable=False)
)
dbEngine = sqla.create_engine(DB_URL)
dbMetadata.create_all(dbEngine)


def setupTestUser(uId, password):
    connection = dbEngine.connect()
    query = sqla.select([usersTable]).where(usersTable.columns.id == uId)
    resultProxy = connection.execute(query)
    resultSet = resultProxy.fetchall()
    if len(resultSet) == 0:
        query = sqla.insert(usersTable).values(id=uId, password=password)
        resultProxy = connection.execute(query)


def printAllMessages():
    connection = dbEngine.connect()
    query = sqla.select([messagesTable])
    resultProxy = connection.execute(query)
    resultSet = resultProxy.fetchall()
    print(resultSet)


def verifyUser(uId, password):
    if ((uId == "") or (password == "")):
        return False

    connection = dbEngine.connect()
    query = sqla.select([usersTable]).where(usersTable.columns.id == uId)
    resultProxy = connection.execute(query)
    resultSet = resultProxy.fetchall()

    if len(resultSet) == 0:
        return False

    if (str((resultSet[0]["id"]) == str(uId)) and (str(resultSet[0]["password"]) == str(password))):
        return True

    return False


def apiRegisterUser(serverConn, payload):
    if ((payload["userId"] == "") or (payload["password"] == "")):
        payload = "Error: No id or password provided. Please specify an id and password."
        payload = {"action": "register", "data": payload}
        serverConn.send(payload)
        return

    connection = dbEngine.connect()
    query = sqla.select([usersTable]).where(
        usersTable.columns.id == payload["userId"])
    resultProxy = connection.execute(query)
    resultSet = resultProxy.fetchall()

    if len(resultSet) > 0:
        payload = "Id not available. Please select different ID"
        payload = {"action": "register", "data": payload}
        serverConn.send(payload)
    else:
        query = sqla.insert(usersTable).values(
            id=payload["userId"], password=payload["password"])
        resultProxy = connection.execute(query)
        activeUsers[payload["userId"]] = serverConn
        payload = REGISTER_OK
        payload = {"action": "register", "data": payload}
        serverConn.send(payload)
        activeUsersForceUpdateUserList()


def apiLoginUser(serverConn, payload):
    if ((payload["userId"] == "") or (payload["password"] == "")):
        payload = "Error: No id or password provided. Please specify an id and password."
        payload = {"action": "login", "data": payload}
        serverConn.send(payload)
        return

    connection = dbEngine.connect()
    query = sqla.select([usersTable]).where(
        usersTable.columns.id == payload["userId"])
    resultProxy = connection.execute(query)
    resultSet = resultProxy.fetchall()

    if len(resultSet) == 0:
        payload = "User does not exist"
        payload = {"action": "login", "data": payload}
        serverConn.send(payload)
        return

    if ((resultSet[0]["id"] != payload["userId"]) or
            (resultSet[0]["password"] != payload["password"])):
        payload = "wrong login or password"
        payload = {"action": "login", "data": payload}
        serverConn.send(payload)
        return

    activeUsers[payload["userId"]] = serverConn
    payload = LOGIN_OK
    payload = {"action": "login", "data": payload}
    serverConn.send(payload)
    activeUsersForceUpdateUserList()


def apiLogoutUser(serverConn, payload):
    if not verifyUser(payload["userId"], payload["password"]):
        payload = "User not recognised"
        payload = {"action": "logout", "data": payload}
        serverConn.send(payload)
        return

    activeUsers.pop(payload["userId"])
    payload = LOGOUT_OK
    payload = {"action": "logout", "data": payload}
    serverConn.send(payload)
    serverConn.kill()
    activeUsersForceUpdateUserList()


def apiGetUsers(serverConn, payload):
    connection = dbEngine.connect()
    query = sqla.select([usersTable])
    resultProxy = connection.execute(query)
    resultSet = resultProxy.fetchall()
    res = []
    for u in resultSet:
        query = sqla.select([messagesTable])
        query = query.where(sqla.and_(messagesTable.columns.read == False, sqla.and_(
            messagesTable.columns.dstId == payload["userId"], messagesTable.columns.srcId == u[0])))
        resultProxy = connection.execute(query)
        count = len(resultProxy.fetchall())
        res.append({"userId": u[0], "active": u[0]
                    in activeUsers, "count": count})
    payload = {"action": "getUsers", "data": res}
    serverConn.send(payload)


def apiUnredCount(serverConn, payload):
    connection = dbEngine.connect()
    condition = sqla.and_(messagesTable.columns.dstId == payload["userId"],
                          messagesTable.columns.srcId == payload["srcId"])
    condition = sqla.and_(messagesTable.columns.read == False, condition)
    query = sqla.select([messagesTable]).where(condition)
    resultProxy = connection.execute(query)
    resultSet = resultProxy.fetchall()
    res = len(resultSet)
    payload = {"action": "getUsers", "data": res}
    serverConn.send(payload)


def apiMessageHistory(serverConn, payload):
    if not verifyUser(payload["userId"], payload["password"]):
        payload = "User not valid"
        payload = {"action": "messageHistory", "data": payload}
        serverConn.send(payload)
        return

    connection = dbEngine.connect()
    condition1 = sqla.and_(messagesTable.columns.read == True,
                           messagesTable.columns.dstId == payload["userId"],
                           messagesTable.columns.srcId == payload["chatId"])
    condition2 = sqla.and_(messagesTable.columns.dstId == payload["chatId"],
                           messagesTable.columns.srcId == payload["userId"])
    condition = sqla.or_(condition1, condition2)
    query = sqla.select([messagesTable]).where(condition)
    resultProxy = connection.execute(query)
    resultSet = resultProxy.fetchall()

    res = []
    for message in resultSet:
        res.append({"srcId": message[0], "dstId": message[1],
                    "msg": message[2], "read": message[3], "time": message[4]})
    payload = {"action": "recieve", "data": res[-payload["count"]:]}
    serverConn.send(payload)


def apiRecieveMessages(serverConn, payload):
    if not verifyUser(payload["userId"], payload["password"]):
        payload = "User not valid"
        payload = {"action": "recieve", "data": payload}
        serverConn.send(payload)
        return

    connection = dbEngine.connect()
    condition = sqla.and_(messagesTable.columns.read == False,
                          messagesTable.columns.dstId == payload["userId"],
                          messagesTable.columns.srcId == payload["srcId"])
    query = sqla.select([messagesTable]).where(condition)
    resultProxy = connection.execute(query)
    resultSet = resultProxy.fetchall()

    res = []
    for message in resultSet:
        res.append({"srcId": message[0], "dstId": message[1],
                    "msg": message[2], "read": message[3], "time": message[4]})
    payload = {"action": "recieve", "data": res}
    serverConn.send(payload)


def apiMarkRead(serverConn, payload):
    if not verifyUser(payload["userId"], payload["password"]):
        payload = "User not valid"
        payload = {"action": "markRed", "data": payload}
        serverConn.send(payload)
        return

    connection = dbEngine.connect()
    condition = sqla.and_(messagesTable.columns.dstId == payload["dstId"],
                          messagesTable.columns.time == payload["time"])
    condition = sqla.and_(messagesTable.columns.srcId == payload["srcId"],
                          condition)
    query = sqla.update(messagesTable).values(read=True).where(condition)
    # TODO LMAO using time as message id
    connection.execute(query)

    payload = "marked as red"
    payload = {"action": "markRed", "data": payload}
    serverConn.send(payload)
    activeUsersForceUpdateUserList()


def apiSend(serverConn, payload):
    if not verifyUser(payload["userId"], payload["password"]):
        payload = "User not valid"
        payload = {"action": "send", "data": payload}
        serverConn.send(payload)
        return

    connection = dbEngine.connect()
    query = sqla.insert(messagesTable).values(srcId=payload["userId"],
                                              dstId=payload["dstUserId"],
                                              msg=payload["msg"],
                                              time=payload["time"])
    connection.execute(query)

    if payload["dstUserId"] in activeUsers:
        payload = {"srcId": payload["userId"], "dstId": payload["dstUserId"],
                   "msg": payload["msg"], "read": False, "time": payload["time"]}
        payload = {"action": "recieve", "data": [payload]}
        activeUsers[payload["data"][0]["dstId"]].send(payload)

    payload = "message send"
    payload = {"action": "send", "data": payload}
    serverConn.send(payload)
    activeUsersForceUpdateUserList()


def apiSendEveryone(serverConn, payload):
    if not verifyUser(payload["userId"], payload["password"]):
        payload = "User not valid"
        payload = {"action": "sendEveryone", "data": payload}
        serverConn.send(payload)
        return

    connection = dbEngine.connect()
    query = sqla.select([usersTable])
    resultProxy = connection.execute(query)
    resultSet = resultProxy.fetchall()
    messageList = []
    for u in resultSet:
        if u[0] != payload["userId"]:
            messageList.append(
                {"srcId": payload["userId"], "dstId": u[0], "msg": payload["msg"]})
    query = sqla.insert(messagesTable)
    connection.execute(query, messageList)
    payload = "messages send"
    payload = {"action": "sendEveryone", "data": payload}
    serverConn.send(payload)
    activeUsersForceUpdateUserList()


def activeUsersForceUpdateUserList():
    for uId, serverConn in activeUsers.items():
        apiGetUsers(serverConn, {"userId": uId})


def unregister(clientConnection):
    clientConnections.remove(clientConnection)


if __name__ == "__main__":
    if DEBUG:
        setupTestUser("qwe", "rty")
        setupTestUser("asd", "fgh")
        setupTestUser("zxc", "vbn")

    # printAllMessages()

    threadLock = threading.Lock()
    maping = {
        "login": apiLoginUser,
        "logout": apiLogoutUser,
        "register": apiRegisterUser,
        "getUsers": apiGetUsers,
        "unredCount": apiUnredCount,
        "messageHistory": apiMessageHistory,
        "recieve": apiRecieveMessages,
        "markRed": apiMarkRead,
        "send": apiSend,
        "sendEveryone": apiSendEveryone,
        "onClose": lambda clientConnection: (
            threadLock.acquire(),
            unregister(clientConnection),
            threadLock.release()
        )
    }

    socketServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socketServer.bind((HOST_ADRESS, HOST_PORT))
    socketServer.listen(5)

    while True:
        clientSocket = socketServer.accept()[0]
        clientConnections.append(ConnectionHandler(
            clientSocket, maping, threadLock))
        clientConnections[-1].start()
