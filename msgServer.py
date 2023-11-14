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
    sqla.Column(COLUMN_USER_ID, sqla.String(USER_ID_LENGTH), nullable=False),
    sqla.Column(COLUMN_PASSWORD, sqla.String(
        USER_PASSWORD_LENGTH), nullable=False),
)
messagesTable = sqla.Table(
    TABLE_MESSAGES, dbMetadata,
    sqla.Column(COLUMN_SRC_ID, sqla.String(USER_ID_LENGTH), nullable=False),
    sqla.Column(COLUMN_DST_ID, sqla.String(USER_ID_LENGTH), nullable=False),
    sqla.Column(COLUMN_MSG, sqla.String(MSG_LENGTH), nullable=False),
    sqla.Column(COLUMN_READ, sqla.Boolean(), default=False),
    sqla.Column(COLUMN_TIMESTAMP, sqla.DateTime(), nullable=False)
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

    if (str((resultSet[0][COLUMN_USER_ID]) == str(uId)) and
            (str(resultSet[0][COLUMN_PASSWORD]) == str(password))):
        return True

    return False


def apiRegisterUser(serverConn, payload):
    if ((payload[KEY_USER_ID] == "") or (payload[KEY_PASSOWRD] == "")):
        payload = RESPONSE_ERROR_MISSING_LOGIN_DATA
        payload = {KEY_ACTION: ACTION_REGISTER, KEY_DATA: payload}
        serverConn.send(payload)
        return

    connection = dbEngine.connect()
    query = sqla.select([usersTable]).where(
        usersTable.columns.id == payload[KEY_USER_ID])
    resultProxy = connection.execute(query)
    resultSet = resultProxy.fetchall()

    if len(resultSet) > 0:
        payload = RESPONSE_ERROR_ID_UNAVAILABLE
        payload = {KEY_ACTION: ACTION_REGISTER, KEY_DATA: payload}
        serverConn.send(payload)
    else:
        query = sqla.insert(usersTable).values(
            id=payload[KEY_USER_ID], password=payload[KEY_PASSOWRD])
        resultProxy = connection.execute(query)
        activeUsers[payload[KEY_USER_ID]] = serverConn
        payload = RESPONSE_REGISTER_OK
        payload = {KEY_ACTION: ACTION_REGISTER, KEY_DATA: payload}
        serverConn.send(payload)
        activeUsersForceUpdateUserList()


def apiLoginUser(serverConn, payload):
    if ((payload[KEY_USER_ID] == "") or (payload[KEY_PASSOWRD] == "")):
        payload = RESPONSE_ERROR_MISSING_LOGIN_DATA
        payload = {KEY_ACTION: ACTION_LOGIN, KEY_DATA: payload}
        serverConn.send(payload)
        return

    connection = dbEngine.connect()
    query = sqla.select([usersTable]).where(
        usersTable.columns.id == payload[KEY_USER_ID])
    resultProxy = connection.execute(query)
    resultSet = resultProxy.fetchall()

    if len(resultSet) == 0:
        payload = RESPONSE_ERROR_NO_USER
        payload = {KEY_ACTION: ACTION_LOGIN, KEY_DATA: payload}
        serverConn.send(payload)
        return

    if ((resultSet[0][COLUMN_USER_ID] != payload[KEY_USER_ID]) or
            (resultSet[0][COLUMN_PASSWORD] != payload[KEY_PASSOWRD])):
        payload = RESPONSE_ERROR_WRONG_ID_PASSWORD
        payload = {KEY_ACTION: ACTION_LOGIN, KEY_DATA: payload}
        serverConn.send(payload)
        return

    activeUsers[payload[KEY_USER_ID]] = serverConn
    payload = RESPONSE_LOGIN_OK
    payload = {KEY_ACTION: ACTION_LOGIN, KEY_DATA: payload}
    serverConn.send(payload)
    activeUsersForceUpdateUserList()


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
            messagesTable.columns.dstId == payload[KEY_USER_ID], messagesTable.columns.srcId == u[0])))
        resultProxy = connection.execute(query)
        count = len(resultProxy.fetchall())
        res.append({KEY_CHAT_ID: u[0], KEY_ACTIVE: u[0]
                    in activeUsers, KEY_COUNT: count})
    payload = {KEY_ACTION: ACTION_GET_USERS, KEY_DATA: res}
    serverConn.send(payload)


def apiUnredCount(serverConn, payload):
    connection = dbEngine.connect()
    condition = sqla.and_(messagesTable.columns.dstId == payload[KEY_USER_ID],
                          messagesTable.columns.srcId == payload[KEY_CHAT_ID])
    condition = sqla.and_(messagesTable.columns.read == False, condition)
    query = sqla.select([messagesTable]).where(condition)
    resultProxy = connection.execute(query)
    resultSet = resultProxy.fetchall()
    res = len(resultSet)
    payload = {KEY_ACTION: ACTION_GET_USERS, KEY_DATA: res}
    serverConn.send(payload)


def apiMessageHistory(serverConn, payload):
    if not verifyUser(payload[KEY_USER_ID], payload[KEY_PASSOWRD]):
        payload = RESPONSE_ERROR_UNKNOWN_USER
        payload = {KEY_ACTION: ACTION_MESSAGE_HISTORY, KEY_DATA: payload}
        serverConn.send(payload)
        return

    connection = dbEngine.connect()
    if payload[KEY_CHAT_ID] == "":
        condition = messagesTable.columns.dstId == ""
    else:
        condition1 = sqla.and_(messagesTable.columns.read == True,
                               messagesTable.columns.dstId == payload[KEY_USER_ID],
                               messagesTable.columns.srcId == payload[KEY_CHAT_ID])
        condition2 = sqla.and_(messagesTable.columns.dstId == payload[KEY_CHAT_ID],
                               messagesTable.columns.srcId == payload[KEY_USER_ID])
        condition = sqla.or_(condition1, condition2)
    query = sqla.select([messagesTable]).where(condition)
    resultProxy = connection.execute(query)
    resultSet = resultProxy.fetchall()

    res = []
    for message in resultSet:
        res.append({KEY_SRC_ID: message[0], KEY_CHAT_ID: payload[KEY_CHAT_ID],
                    KEY_MSG: message[2], KEY_READ: message[3], KEY_TIMESTAMP: message[4]})
    payload = {KEY_ACTION: ACTION_RECIEVE, KEY_DATA: res[-payload[KEY_COUNT]:]}
    serverConn.send(payload)


def apiRecieveMessages(serverConn, payload):
    if not verifyUser(payload[KEY_USER_ID], payload[KEY_PASSOWRD]):
        payload = RESPONSE_ERROR_UNKNOWN_USER
        payload = {KEY_ACTION: ACTION_RECIEVE, KEY_DATA: payload}
        serverConn.send(payload)
        return

    connection = dbEngine.connect()
    condition = sqla.and_(messagesTable.columns.read == False,
                          messagesTable.columns.dstId == payload[KEY_USER_ID],
                          messagesTable.columns.srcId == payload[KEY_CHAT_ID])
    query = sqla.select([messagesTable]).where(condition)
    resultProxy = connection.execute(query)
    resultSet = resultProxy.fetchall()

    res = []
    for message in resultSet:
        res.append({KEY_SRC_ID: message[0], KEY_CHAT_ID: payload[KEY_CHAT_ID],
                    KEY_MSG: message[2], KEY_READ: message[3], KEY_TIMESTAMP: message[4]})
    payload = {KEY_ACTION: ACTION_RECIEVE, KEY_DATA: res}
    serverConn.send(payload)


def apiMarkRead(serverConn, payload):
    if not verifyUser(payload[KEY_USER_ID], payload[KEY_PASSOWRD]):
        payload = RESPONSE_ERROR_UNKNOWN_USER
        payload = {KEY_ACTION: ACTION_MARK_READ, KEY_DATA: payload}
        serverConn.send(payload)
        return

    connection = dbEngine.connect()
    condition = sqla.and_(messagesTable.columns.dstId == payload[KEY_USER_ID],
                          messagesTable.columns.timestamp == payload[KEY_TIMESTAMP])
    condition = sqla.and_(messagesTable.columns.srcId == payload[KEY_CHAT_ID],
                          condition)
    query = sqla.update(messagesTable).values(read=True).where(condition)
    # TODO LMAO using time as message id
    connection.execute(query)

    payload = RESPONSE_MARK_READ_OK
    payload = {KEY_ACTION: ACTION_MARK_READ, KEY_DATA: payload}
    serverConn.send(payload)
    activeUsersForceUpdateUserList()


def apiSend(serverConn, payload):
    if not verifyUser(payload[KEY_USER_ID], payload[KEY_PASSOWRD]):
        payload = RESPONSE_ERROR_UNKNOWN_USER
        payload = {KEY_ACTION: ACTION_SEND, KEY_DATA: payload}
        serverConn.send(payload)
        return

    connection = dbEngine.connect()
    query = sqla.insert(messagesTable).values(srcId=payload[KEY_USER_ID],
                                              dstId=payload[KEY_CHAT_ID],
                                              msg=payload[KEY_MSG],
                                              timestamp=payload[KEY_TIMESTAMP])
    connection.execute(query)

    targetUser = payload[KEY_CHAT_ID]
    if targetUser in activeUsers:  # TODO replace with notify
        payload = {KEY_SRC_ID: payload[KEY_USER_ID],
                   KEY_CHAT_ID: payload[KEY_USER_ID],
                   KEY_MSG: payload[KEY_MSG],
                   KEY_READ: False,
                   KEY_TIMESTAMP: payload[KEY_TIMESTAMP]}
        payload = {KEY_ACTION: ACTION_RECIEVE, KEY_DATA: [payload]}
        activeUsers[targetUser].send(payload)

    payload = RESPONSE_SEND_OK
    payload = {KEY_ACTION: ACTION_SEND, KEY_DATA: payload}
    serverConn.send(payload)
    activeUsersForceUpdateUserList()


def apiSendEveryone(serverConn, payload):
    if not verifyUser(payload[KEY_USER_ID], payload[KEY_PASSOWRD]):
        payload = RESPONSE_ERROR_UNKNOWN_USER
        payload = {KEY_ACTION: ACTION_SEND_EVERYONE, KEY_DATA: payload}
        serverConn.send(payload)
        return

    connection = dbEngine.connect()
    query = sqla.insert(messagesTable).values(srcId=payload[KEY_USER_ID],
                                              dstId="",
                                              msg=payload[KEY_MSG],
                                              read=True,
                                              timestamp=payload[KEY_TIMESTAMP])
    connection.execute(query)

    payload = {KEY_SRC_ID: payload[KEY_USER_ID],  # TODO replace with notify
               KEY_CHAT_ID: "",
               KEY_MSG: payload[KEY_MSG],
               KEY_READ: True,
               KEY_TIMESTAMP: payload[KEY_TIMESTAMP]}
    payload = {KEY_ACTION: ACTION_RECIEVE, KEY_DATA: [payload]}
    for user in activeUsers.values():
        if user != serverConn:
            user.send(payload)

    payload = RESPONSE_SEND_EVERYONE_OK
    payload = {KEY_ACTION: ACTION_SEND_EVERYONE, KEY_DATA: payload}
    serverConn.send(payload)
    activeUsersForceUpdateUserList()


def activeUsersForceUpdateUserList():   # TODO replace with notify
    for uId, serverConn in activeUsers.items():
        apiGetUsers(serverConn, {KEY_USER_ID: uId})


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
        ACTION_UNRED_COUNT: apiUnredCount,
        ACTION_MESSAGE_HISTORY: apiMessageHistory,
        ACTION_RECIEVE: apiRecieveMessages,
        ACTION_MARK_READ: apiMarkRead,
        ACTION_SEND: apiSend,
        ACTION_SEND_EVERYONE: apiSendEveryone,
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
