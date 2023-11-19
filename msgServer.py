import socket
import threading
import sqlalchemy as sqla

from connectionHandler import ConnectionHandler
from constants import *


activeUsers = {}
clientConnections = []
dbMetadata = sqla.MetaData()
usersTable = sqla.Table(
    TABLE_USERS, dbMetadata,
    sqla.Column(COLUMN_USER_ID, sqla.String(USER_ID_LENGTH),
                primary_key=True, nullable=False),
    sqla.Column(COLUMN_PASSWORD, sqla.String(
        USER_PASSWORD_LENGTH), nullable=False),
)
messagesTable = sqla.Table(
    TABLE_MESSAGES, dbMetadata,
    sqla.Column(COLUMN_MESSAGE_ID, sqla.Integer(),
                primary_key=True, nullable=False, autoincrement=True),
    sqla.Column(COLUMN_SRC_ID, sqla.String(USER_ID_LENGTH), nullable=False),
    sqla.Column(COLUMN_DST_ID, sqla.String(USER_ID_LENGTH), nullable=False),
    sqla.Column(COLUMN_MSG, sqla.String(MSG_LENGTH), nullable=False),
    sqla.Column(COLUMN_READ, sqla.Boolean(), default=False),
    sqla.Column(COLUMN_TIMESTAMP, sqla.DateTime(), nullable=False)
)
dbEngine = sqla.create_engine(DB_URL)
dbMetadata.create_all(dbEngine)


def setupTestUser(userId, password):
    condition = usersTable.columns.userId == userId
    query = sqla.select(usersTable).where(condition)
    with dbEngine.connect() as dbConn:
        rows = dbConn.execute(query).fetchall()
        if len(rows) == 0:
            query = sqla.insert(usersTable).values(
                userId=userId, password=password)
            dbConn.execute(query)


def printAllMessages():
    query = sqla.select(messagesTable)
    with dbEngine.connect() as dbConn:
        rows = dbConn.execute(query).fetchall()
        print(rows)


def verifyUser(userId, password):
    if ((userId == "") or (password == "")):
        return False

    rows = []
    condition = usersTable.columns.userId == userId
    query = sqla.select(usersTable).where(condition)
    with dbEngine.connect() as dbConn:
        rows = dbConn.execute(query).fetchall()

    if len(rows) == 0:
        return False

    if (str((rows[0][COLUMN_USER_ID]) == str(userId)) and
            (str(rows[0][COLUMN_PASSWORD]) == str(password))):
        return True

    return False


def apiRegisterUser(serverConn, payload):
    if ((payload[KEY_USER_ID] == "") or (payload[KEY_PASSOWRD] == "")):
        payload = RESPONSE_ERROR_MISSING_LOGIN_DATA
        payload = {KEY_ACTION: ACTION_REGISTER, KEY_DATA: payload}
        serverConn.send(payload)
        return

    success = False
    condition = usersTable.columns.userId == payload[KEY_USER_ID]
    query = sqla.select(usersTable).where(condition)
    with dbEngine.connect() as dbConn:
        rows = dbConn.execute(query).fetchall()

        if len(rows) == 0:
            query = sqla.insert(usersTable).values(
                userId=payload[KEY_USER_ID], password=payload[KEY_PASSOWRD])
            dbConn.execute(query)
            activeUsers[payload[KEY_USER_ID]] = serverConn
            payload = RESPONSE_REGISTER_OK
            payload = {KEY_ACTION: ACTION_REGISTER, KEY_DATA: payload}
            success = True

    if not success:
        payload = RESPONSE_ERROR_ID_UNAVAILABLE
        payload = {KEY_ACTION: ACTION_REGISTER, KEY_DATA: payload}
    serverConn.send(payload)
    if success:
        notify(ACTION_NOTIFY_USERS_UPDATE)


def apiLoginUser(serverConn, payload):
    if ((payload[KEY_USER_ID] == "") or (payload[KEY_PASSOWRD] == "")):
        payload = RESPONSE_ERROR_MISSING_LOGIN_DATA
        payload = {KEY_ACTION: ACTION_LOGIN, KEY_DATA: payload}
        serverConn.send(payload)
        return

    rows = []
    condition = usersTable.columns.userId == payload[KEY_USER_ID]
    query = sqla.select(usersTable).where(condition)
    with dbEngine.connect() as dbConn:
        rows = dbConn.execute(query).fetchall()

    if len(rows) == 0:
        payload = RESPONSE_ERROR_NO_USER
        payload = {KEY_ACTION: ACTION_LOGIN, KEY_DATA: payload}
        serverConn.send(payload)
        return

    if ((rows[0][COLUMN_USER_ID] != payload[KEY_USER_ID]) or
            (rows[0][COLUMN_PASSWORD] != payload[KEY_PASSOWRD])):
        payload = RESPONSE_ERROR_WRONG_ID_PASSWORD
        payload = {KEY_ACTION: ACTION_LOGIN, KEY_DATA: payload}
        serverConn.send(payload)
        return

    activeUsers[payload[KEY_USER_ID]] = serverConn
    payload = RESPONSE_LOGIN_OK
    payload = {KEY_ACTION: ACTION_LOGIN, KEY_DATA: payload}
    serverConn.send(payload)
    notify(ACTION_NOTIFY_USERS_UPDATE)


def apiLogoutUser(serverConn, payload):
    if not verifyUser(payload[KEY_USER_ID], payload[KEY_PASSOWRD]):
        payload = RESPONSE_ERROR_UNKNOWN_USER
        payload = {KEY_ACTION: ACTION_LOGOUT, KEY_DATA: payload}
        serverConn.send(payload)
        return

    activeUsers.pop(payload[KEY_USER_ID])
    payload = RESPONSE_LOGOUT_OK
    payload = {KEY_ACTION: ACTION_LOGOUT, KEY_DATA: payload}
    serverConn.send(payload)
    serverConn.kill()
    notify(ACTION_NOTIFY_USERS_UPDATE)


def clientCollapsed(serverConn):
    uList = list(filter(lambda it: it[1] == serverConn, activeUsers.items()))
    if len(uList) > 0:
        activeUsers.pop(uList[0][0])
    serverConn.kill()
    notify(ACTION_NOTIFY_USERS_UPDATE)


def apiGetUsers(serverConn, payload):
    userList = []
    query = sqla.select(usersTable)
    with dbEngine.connect() as dbConn:
        rows = dbConn.execute(query).fetchall()
        for user in rows:
            condition = sqla.and_(sqla.not_(messagesTable.columns.read),
                                  messagesTable.columns.dstId == payload[KEY_USER_ID],
                                  messagesTable.columns.srcId == user[0])
            query = sqla.select(messagesTable).where(condition)
            count = len(dbConn.execute(query).fetchall())
            userList.append({KEY_CHAT_ID: user[0], KEY_ACTIVE: user[0]
                            in activeUsers, KEY_COUNT: count})
    payload = {KEY_ACTION: ACTION_GET_USERS, KEY_DATA: userList}
    serverConn.send(payload)


def apiUnreadCount(serverConn, payload):
    rows = []
    condition = sqla.and_(sqla.not_(messagesTable.columns.read),
                          messagesTable.columns.dstId == payload[KEY_USER_ID],
                          messagesTable.columns.srcId == payload[KEY_CHAT_ID])
    query = sqla.select(messagesTable).where(condition)
    with dbEngine.connect() as dbConn:
        rows = dbConn.execute(query).fetchall()
    payload = {KEY_ACTION: ACTION_GET_USERS, KEY_DATA: len(rows)}
    serverConn.send(payload)


def apiMessageHistory(serverConn, payload):
    if not verifyUser(payload[KEY_USER_ID], payload[KEY_PASSOWRD]):
        payload = RESPONSE_ERROR_UNKNOWN_USER
        payload = {KEY_ACTION: ACTION_MESSAGE_HISTORY, KEY_DATA: payload}
        serverConn.send(payload)
        return

    rows = []
    if payload[KEY_CHAT_ID] == "":
        condition = messagesTable.columns.dstId == ""
    else:
        condition1 = sqla.and_(messagesTable.columns.read,
                               messagesTable.columns.dstId == payload[KEY_USER_ID],
                               messagesTable.columns.srcId == payload[KEY_CHAT_ID])
        condition2 = sqla.and_(messagesTable.columns.dstId == payload[KEY_CHAT_ID],
                               messagesTable.columns.srcId == payload[KEY_USER_ID])
        condition = sqla.or_(condition1, condition2)
    query = sqla.select(messagesTable).where(condition)
    with dbEngine.connect() as dbConn:
        rows = dbConn.execute(query).fetchall()

    messageList = [{KEY_MESSAGE_ID: message[0], KEY_SRC_ID: message[1],
                    KEY_CHAT_ID: payload[KEY_CHAT_ID], KEY_MSG: message[3],
                    KEY_READ: message[4], KEY_TIMESTAMP: message[5]}
                   for message in rows]
    payload = {KEY_ACTION: ACTION_RECIEVE,
               KEY_DATA: messageList[-payload[KEY_COUNT]:]}
    serverConn.send(payload)


def apiRecieveMessages(serverConn, payload):
    if not verifyUser(payload[KEY_USER_ID], payload[KEY_PASSOWRD]):
        payload = RESPONSE_ERROR_UNKNOWN_USER
        payload = {KEY_ACTION: ACTION_RECIEVE, KEY_DATA: payload}
        serverConn.send(payload)
        return

    rows = []
    condition = sqla.and_(sqla.not_(messagesTable.columns.read),
                          messagesTable.columns.dstId == payload[KEY_USER_ID],
                          messagesTable.columns.srcId == payload[KEY_CHAT_ID])
    query = sqla.select(messagesTable).where(condition)
    with dbEngine.connect() as dbConn:
        rows = dbConn.execute(query).fetchall()

    messageList = [{KEY_MESSAGE_ID: message[0], KEY_SRC_ID: message[1],
                    KEY_CHAT_ID: payload[KEY_CHAT_ID], KEY_MSG: message[3],
                    KEY_READ: message[4], KEY_TIMESTAMP: message[5]}
                   for message in rows]
    payload = {KEY_ACTION: ACTION_RECIEVE, KEY_DATA: messageList}
    serverConn.send(payload)


def apiMarkRead(serverConn, payload):
    if not verifyUser(payload[KEY_USER_ID], payload[KEY_PASSOWRD]):
        payload = RESPONSE_ERROR_UNKNOWN_USER
        payload = {KEY_ACTION: ACTION_MARK_READ, KEY_DATA: payload}
        serverConn.send(payload)
        return

    condition = sqla.and_(messagesTable.columns.messageId == payload[KEY_MESSAGE_ID],
                          messagesTable.columns.srcId == payload[KEY_CHAT_ID],
                          messagesTable.columns.dstId == payload[KEY_USER_ID])
    query = sqla.update(messagesTable).values(read=True).where(condition)
    with dbEngine.connect() as dbConn:
        dbConn.execute(query)

    target = payload[KEY_CHAT_ID]
    payload = {KEY_CHAT_ID: payload[KEY_USER_ID],
               KEY_MESSAGE_ID: payload[KEY_MESSAGE_ID]}
    notify(ACTION_NOTIFY_MARK_READ, target=target, payload=payload)

    payload = RESPONSE_MARK_READ_OK
    payload = {KEY_ACTION: ACTION_MARK_READ, KEY_DATA: payload}
    serverConn.send(payload)


def apiSend(serverConn, payload):
    if not verifyUser(payload[KEY_USER_ID], payload[KEY_PASSOWRD]):
        payload = RESPONSE_ERROR_UNKNOWN_USER
        payload = {KEY_ACTION: ACTION_SEND, KEY_DATA: payload}
        serverConn.send(payload)
        return

    query = sqla.insert(messagesTable).values(
        srcId=payload[KEY_USER_ID],
        dstId=payload[KEY_CHAT_ID],
        msg=payload[KEY_MSG],
        read=payload[KEY_CHAT_ID] == payload[KEY_USER_ID],
        timestamp=payload[KEY_TIMESTAMP]
    )
    with dbEngine.connect() as dbConn:
        dbConn.execute(query)

    if payload[KEY_CHAT_ID] != payload[KEY_USER_ID]:
        target = payload[KEY_CHAT_ID]
        payload = {KEY_CHAT_ID: payload[KEY_USER_ID]}
        notify(ACTION_NOTIFY_NEW_MESSAGE, target=target, payload=payload)

    payload = RESPONSE_SEND_OK
    payload = {KEY_ACTION: ACTION_SEND, KEY_DATA: payload}
    serverConn.send(payload)


def apiSendEveryone(serverConn, payload):
    if not verifyUser(payload[KEY_USER_ID], payload[KEY_PASSOWRD]):
        payload = RESPONSE_ERROR_UNKNOWN_USER
        payload = {KEY_ACTION: ACTION_SEND_EVERYONE, KEY_DATA: payload}
        serverConn.send(payload)
        return

    query = sqla.insert(messagesTable).values(srcId=payload[KEY_USER_ID],
                                              dstId="",
                                              msg=payload[KEY_MSG],
                                              read=True,
                                              timestamp=payload[KEY_TIMESTAMP])
    with dbEngine.connect() as dbConn:
        dbConn.execute(query)

    exclude = payload[KEY_USER_ID]
    payload = {KEY_CHAT_ID: ""}
    notify(ACTION_NOTIFY_NEW_MESSAGE, exclude=exclude, payload=payload)

    payload = RESPONSE_SEND_EVERYONE_OK
    payload = {KEY_ACTION: ACTION_SEND_EVERYONE, KEY_DATA: payload}
    serverConn.send(payload)


def notify(action, target="", exclude=None, payload=None):
    if payload is None:
        payload = {KEY_ACTION: action, KEY_DATA: None}
    else:
        payload = {KEY_ACTION: action, KEY_DATA: payload}
    if target == "":
        for activeUser in list(filter(lambda k: k != exclude, activeUsers.keys())):
            activeUsers[activeUser].send(payload)
    else:
        if target in activeUsers:
            activeUsers[target].send(payload)


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
        ACTION_LOGIN: apiLoginUser,
        ACTION_LOGOUT: apiLogoutUser,
        ACTION_REGISTER: apiRegisterUser,
        ACTION_GET_USERS: apiGetUsers,
        ACTION_UNRED_COUNT: apiUnreadCount,
        ACTION_MESSAGE_HISTORY: apiMessageHistory,
        ACTION_RECIEVE: apiRecieveMessages,
        ACTION_MARK_READ: apiMarkRead,
        ACTION_SEND: apiSend,
        ACTION_SEND_EVERYONE: apiSendEveryone,
        "onClose": lambda clientConnection: (
            threadLock.acquire(),
            unregister(clientConnection),
            threadLock.release()
        ),
        "onCollapse": clientCollapsed
    }

    socketServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    socketServer.bind((HOST_ADRESS, HOST_PORT))
    socketServer.listen(5)

    print("Listening for connections...")
    while True:
        clientSocket = socketServer.accept()[0]
        clientConnections.append(ConnectionHandler(
            clientSocket, maping, threadLock))
        clientConnections[-1].start()
