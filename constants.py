

# general
DEBUG = True
TEST_USERS = [("qwe", "rty"), ("asd", "fgh"), ("zxc", "vbn")]
HOST_ADRESS = "127.0.0.1"
HOST_PORT = 5000
TIMESTAMP_FORMAT = "%d.%m.%Y %H:%M:%S"
ALL_CHAT_ID = ""
HOOK_ON_CLOSE = "onClose"
HOOK_ON_COLLAPSE = "onCollapse"
SERVER_STARTUP_NOTICE = "Listening for connections..."

# DB settings
DB_URL = "sqlite:///msgServer.db"
USER_ID_LENGTH = 32
USER_PASSWORD_LENGTH = 32
MSG_LENGTH = 255

# DB artifacts
TABLE_USERS = "users"
TABLE_MESSAGES = "messages"
COLUMN_USER_ID = "userId"
COLUMN_PASSWORD = "password"
COLUMN_MESSAGE_ID = "messageId"
COLUMN_SRC_ID = "srcId"
COLUMN_DST_ID = "dstId"
COLUMN_MSG = "msg"
COLUMN_READ = "read"
COLUMN_TIMESTAMP = "timestamp"

# actions
ACTION_LOGIN = "login"
ACTION_LOGOUT = "logout"
ACTION_REGISTER = "register"
ACTION_GET_USERS = "getUsers"
ACTION_UNRED_COUNT = "unredCount"
ACTION_MESSAGE_HISTORY = "messageHistory"
ACTION_RECIEVE = "recieve"
ACTION_MARK_READ = "markRead"
ACTION_SEND = "send"
ACTION_SEND_EVERYONE = "sendEveryone"
ACTION_NOTIFY_USERS_UPDATE = "notifyUsersUpdate"
ACTION_NOTIFY_NEW_MESSAGE = "notifyNewMessage"
ACTION_NOTIFY_MARK_READ = "notifyMarkRead"

# message keys
KEY_ACTION = "action"
KEY_DATA = "data"
KEY_USER_ID = "userId"
KEY_PASSOWRD = "password"
KEY_TMP_MESSAGE_ID = "tmpMessageId"
KEY_MESSAGE_ID = "messageId"
KEY_SRC_ID = "srcId"
KEY_CHAT_ID = "chatId"
KEY_COUNT = "count"
KEY_TIMESTAMP = "timestamp"
KEY_MSG = "msg"
KEY_READ = "read"
KEY_ACTIVE = "active"

# server responses
RESPONSE_REGISTER_OK = "Registered successfully"
RESPONSE_ERROR_MISSING_LOGIN_DATA = "No id or password provided. Please specify an id and password."
RESPONSE_ERROR_ID_UNAVAILABLE = "Id not available. Please select different ID"
RESPONSE_LOGIN_OK = "Login successfull"
RESPONSE_ERROR_NO_USER = "User does not exist"
RESPONSE_ERROR_WRONG_ID_PASSWORD = "Wrong login or password"
RESPONSE_LOGOUT_OK = "Logout successfull"
RESPONSE_ERROR_UNKNOWN_USER = "User not recognised"
RESPONSE_MARK_READ_OK = "Marked as read"
RESPONSE_SEND_OK = "Message send"
RESPONSE_SEND_EVERYONE_OK = "Message send to everyone"

# GUI layout
GUI_WINDOW_TITLE = "Messager"
GUI_LOGIN_ID_LABEL = "User Id:"
GUI_LOGIN_PASSWORD_LABEL = "Password:"
GUI_LOGIN_BUTTON = "Login"
GUI_REGISTER_BUTTON = "Register"
GUI_MISSING_LOGIN_DATA = "No id or password provided!"
GUI_USER_LABEL = "User Id: "
GUI_LOGOUT_BUTTON = "Logout"
GUI_USER_LIST_WIDTH = 30
GUI_CHAT_LABEL = "Chat with: "
GUI_ALL_CHAT_LABEL = "Everyone"
GUI_ACTIVE_LABEL = "      active"
GUI_PASSIVE_LABEL = "      passive"
GUI_NEW_MESSAGES_LABEL = "new"
GUI_DEFAULT_MESSAGE_COUNT = 10
GUI_MSG_FRAME_PADDING = 10
GUI_MESSAGE_INFO_READ = ", read"
GUI_MESSAGE_INFO_UNREAD = ", unread"
GUI_MESSAGE_INFO_SIZE = 5
GUI_MESSAGE_COLOR = "darkgrey"
GUI_SEND_MESSAGE_COLOR = "grey"
GUI_BUTTON_SEND = "Send"
