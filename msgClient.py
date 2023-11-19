import socket
import threading
import tkinter as tk
from tkinter import font
from time import time_ns
from datetime import datetime

from connectionHandler import ConnectionHandler
from constants import *


class MsgPane(tk.Frame):
    def __init__(self, master, message, side):
        super().__init__(master)
        self.message = message
        self.side = side
        self.showInfo = True

        msgInfoFont = font.Font(size=GUI_MESSAGE_INFO_SIZE)
        self.msgInfo = tk.Label(self, font=msgInfoFont)
        self.msgSrc = tk.Label(
            self, text=self.message[KEY_SRC_ID], font=msgInfoFont)

        self.msg = tk.Button(self, text=self.message[KEY_MSG],
                             background=GUI_SEND_MESSAGE_COLOR if self.side == "right"
                             else GUI_MESSAGE_COLOR, command=self.toggleInfo)

        self.updateMsgInfo()
        self.toggleInfo()

    def toggleInfo(self):
        if not self.showInfo:
            self.msgInfo.pack(side="top")
        else:
            self.msgInfo.pack_forget()

        self.msg.pack_forget()
        self.msg.pack(side=self.side)

        if not self.showInfo:
            self.msgSrc.pack(side=self.side)
        else:
            self.msgSrc.pack_forget()

        self.showInfo = not self.showInfo

    def updateMsgInfo(self):
        msgInfo = self.message[KEY_TIMESTAMP].strftime(TIMESTAMP_FORMAT)
        msgInfo += (GUI_MESSAGE_INFO_READ if self.message[KEY_READ]
                    else GUI_MESSAGE_INFO_UNREAD)
        self.msgInfo["text"] = msgInfo
        self.update()


class Gui(tk.Frame):
    def __init__(self, master=tk.Tk()):
        super().__init__(master)
        self.master = master
        self.master.title(GUI_WINDOW_TITLE)
        self.master.protocol("WM_DELETE_WINDOW", self.onClose)
        self.userId = ""
        self.userPassword = ""
        self.userList = []
        self.selectedChatId = ""
        self.recieveMessagesAppendGetNew = False

        self.loginFrame = None
        self.userIdEntry = None
        self.userPasswordEntry = None
        self.loginResultLabel = None

        self.userMainFrame = None
        self.userIdLabel = None
        self.userListbox = None
        self.chatFrame = None
        self.chatInfoLabel = None
        self.msgFrame = None
        self.msgPanes = []
        self.msgEntry = None

        self.createLoginLayout()
        self.pack()

        self.threadLock = threading.Lock()
        self.connectionHandler = None

    def createLoginLayout(self):
        if self.userMainFrame is not None:
            self.userMainFrame.pack_forget()
        if self.loginFrame is None:
            self.loginFrame = tk.Frame(self)

            idLabel = tk.Label(self.loginFrame, text=GUI_LOGIN_ID_LABEL)
            idLabel.grid(row=0, column=0)
            self.userIdEntry = tk.Entry(self.loginFrame)
            self.userIdEntry.grid(row=0, column=1)

            passLabel = tk.Label(
                self.loginFrame, text=GUI_LOGIN_PASSWORD_LABEL)
            passLabel.grid(row=1, column=0)
            self.userPasswordEntry = tk.Entry(self.loginFrame)
            self.userPasswordEntry.grid(row=1, column=1)

            loginButton = tk.Button(
                self.loginFrame, text=GUI_LOGIN_BUTTON,
                command=lambda: self.sendRegisterLoginUser(ACTION_LOGIN))
            loginButton.grid(row=2, column=0)
            registerButton = tk.Button(
                self.loginFrame, text=GUI_REGISTER_BUTTON,
                command=lambda: self.sendRegisterLoginUser(ACTION_REGISTER))
            registerButton.grid(row=2, column=1)

            self.loginResultLabel = tk.Label(self.loginFrame, text="")
            self.loginResultLabel.grid(row=3, column=0, columnspan=2)
        self.loginFrame.pack()
        self.userIdEntry.focus_set()

    def createUserMainLayout(self):
        if self.loginFrame is not None:
            self.loginFrame.pack_forget()
        if self.userMainFrame is None:
            self.userMainFrame = tk.Frame(self)

            userMenuFrame = tk.Frame(self.userMainFrame)
            userMenuFrame.pack(side="top", fill="y")
            self.userIdLabel = tk.Label(userMenuFrame, text="")
            self.userIdLabel.grid(row=0, column=0)
            logoutButton = tk.Button(
                userMenuFrame, text=GUI_LOGOUT_BUTTON, command=self.sendLogoutUser)
            logoutButton.grid(row=0, column=1)

            self.userListbox = tk.Listbox(
                self.userMainFrame, width=GUI_USER_LIST_WIDTH, selectmode="single")
            self.userListbox.pack(side="left")

            self.userListbox.bind("<<ListboxSelect>>",
                                  lambda _: self.chatSelected())
        self.userMainFrame.pack()
        self.userIdLabel["text"] = GUI_USER_LABEL+self.userId
        if self.chatFrame is not None:
            self.chatFrame.pack_forget()
        self.sendUpdateUserList()

    def createChatLayout(self):
        if self.chatFrame is None:
            self.chatFrame = tk.Frame(self.userMainFrame)

            self.chatInfoLabel = tk.Label(self.chatFrame, text="")
            self.chatInfoLabel.pack(side="top", fill="x")

            self.msgFrame = tk.Frame(self.chatFrame)
            self.msgFrame.pack(side="top", fill="x",
                               padx=GUI_MSG_FRAME_PADDING,
                               pady=GUI_MSG_FRAME_PADDING)

            msgEntryFrame = tk.Frame(self.chatFrame)
            msgEntryFrame.pack(side="bottom", fill="x")
            self.msgEntry = tk.Entry(msgEntryFrame)
            self.msgEntry.pack(side="left")
            self.msgEntry.bind("<Return>", self.sendMessage)
            msgEntryButton = tk.Button(
                msgEntryFrame, text=GUI_BUTTON_SEND, command=self.sendMessage)
            msgEntryButton.pack(side="right")
        self.chatFrame.pack(side="right")
        self.chatInfoLabel["text"] = GUI_CHAT_LABEL+self.selectedChatId
        if self.selectedChatId == ALL_CHAT_ID:
            self.chatInfoLabel["text"] += GUI_ALL_CHAT_LABEL
        for mp in self.msgPanes:
            mp.pack_forget()
        self.msgPanes = []
        self.recieveMessagesAppendGetNew = True
        self.sendGetMessageHistory()

    def chatSelected(self):
        selection = self.userListbox.curselection()
        if len(selection) == 0:
            return
        self.selectedChatId = self.userList[selection[0]][0]
        self.createChatLayout()

    def sendRegisterLoginUser(self, actionType):
        if self.connectionHandler is None:
            maping = {
                ACTION_LOGIN: lambda _, res: self.recieveRegisterLoginUser(res),
                ACTION_LOGOUT: lambda _, res: self.recieveLogoutUser(res),
                ACTION_REGISTER: lambda _, res: self.recieveRegisterLoginUser(res),
                ACTION_GET_USERS: lambda _, res: self.recieveUpdateUserList(res),
                ACTION_RECIEVE: lambda _, res: self.recieveMessage(res),
                ACTION_SEND: lambda _, res: self.sendMessageResponse(res),
                ACTION_SEND_EVERYONE: lambda _, res: self.sendMessageResponse(res),
                ACTION_NOTIFY_USERS_UPDATE: lambda _, data: self.recieveNotifyUsersUpdate(data),
                ACTION_NOTIFY_NEW_MESSAGE: lambda _, data: self.recieveNotifyNewMessage(data),
                ACTION_NOTIFY_MARK_READ: lambda _, data: self.recieveNotifyMarkRead(data),
                HOOK_ON_COLLAPSE: lambda _: self.recieveLogoutUser(
                    RESPONSE_LOGOUT_OK)
            }
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.connect((HOST_ADRESS, HOST_PORT))
            except ConnectionRefusedError:
                return
            self.connectionHandler = ConnectionHandler(
                sock,  maping, self.threadLock)
            self.connectionHandler.start()
        if actionType not in (ACTION_REGISTER, ACTION_LOGIN):
            return
        if ((self.userIdEntry.get() == "") or (self.userPasswordEntry.get() == "")):
            self.loginResultLabel["text"] = GUI_MISSING_LOGIN_DATA
            self.update()
            return
        self.userId = self.userIdEntry.get()
        self.userPassword = self.userPasswordEntry.get()
        payload = {KEY_USER_ID: self.userIdEntry.get(
        ), KEY_PASSOWRD: self.userPasswordEntry.get()}
        payload = {KEY_ACTION: actionType, KEY_DATA: payload}
        self.connectionHandler.send(payload)

    def recieveRegisterLoginUser(self, result):
        if result == RESPONSE_REGISTER_OK or result == RESPONSE_LOGIN_OK:
            self.userIdEntry.delete(0, tk.END)
            self.userPasswordEntry.delete(0, tk.END)
            self.loginResultLabel["text"] = ""
            return self.createUserMainLayout()
        self.loginResultLabel["text"] = result
        self.update()

    def sendUpdateUserList(self):
        payload = {KEY_USER_ID: self.userId, KEY_PASSOWRD: self.userPassword}
        payload = {KEY_ACTION: ACTION_GET_USERS, KEY_DATA: payload}
        self.connectionHandler.send(payload)

    def recieveUpdateUserList(self, result):
        self.userListbox.delete(0, tk.END)
        self.userList = []
        self.userListbox.insert(1, GUI_ALL_CHAT_LABEL)
        self.userList.append((ALL_CHAT_ID, True, float("inf")))
        for user in result:
            self.userList.append(
                (user[KEY_CHAT_ID], user[KEY_ACTIVE], user[KEY_COUNT]))
            status = GUI_ACTIVE_LABEL if user[KEY_ACTIVE] else GUI_PASSIVE_LABEL
            unred = ""
            if user[KEY_COUNT] > 0:
                unred = f" \t({user[KEY_COUNT]} {GUI_NEW_MESSAGES_LABEL})"
            self.userListbox.insert(tk.END, user[KEY_CHAT_ID]+status+unred)
        self.userListbox.update()

    def sendLogoutUser(self):
        payload = {KEY_USER_ID: self.userId, KEY_PASSOWRD: self.userPassword}
        payload = {KEY_ACTION: ACTION_LOGOUT, KEY_DATA: payload}
        self.connectionHandler.send(payload)

    def recieveLogoutUser(self, result):
        if result == RESPONSE_LOGOUT_OK:
            self.userId = ""
            self.userPassword = ""
            self.connectionHandler.kill()
            self.connectionHandler = None
            self.createLoginLayout()

    def sendGetMessageHistory(self):
        payload = {KEY_USER_ID: self.userId, KEY_PASSOWRD: self.userPassword,
                   KEY_CHAT_ID: self.selectedChatId, KEY_COUNT: GUI_DEFAULT_MESSAGE_COUNT}
        payload = {KEY_ACTION: ACTION_MESSAGE_HISTORY, KEY_DATA: payload}
        self.connectionHandler.send(payload)

    def sendGetNewMessages(self):
        payload = {KEY_USER_ID: self.userId, KEY_PASSOWRD: self.userPassword,
                   KEY_CHAT_ID: self.selectedChatId}
        payload = {KEY_ACTION: ACTION_RECIEVE, KEY_DATA: payload}
        self.connectionHandler.send(payload)

    def recieveMessage(self, result):
        updateUserlist = False
        for message in result:
            if self.selectedChatId in (message[KEY_SRC_ID], message[KEY_CHAT_ID]):
                if ((not message[KEY_READ]) and
                    (message[KEY_SRC_ID] != self.userId) and
                        (message[KEY_CHAT_ID] == self.selectedChatId)):
                    payload = {KEY_USER_ID: self.userId, KEY_PASSOWRD: self.userPassword,
                               KEY_MESSAGE_ID: message[KEY_MESSAGE_ID],
                               KEY_SRC_ID: message[KEY_SRC_ID], KEY_CHAT_ID: message[KEY_CHAT_ID],
                               KEY_TIMESTAMP: message[KEY_TIMESTAMP]}
                    payload = {KEY_ACTION: ACTION_MARK_READ, KEY_DATA: payload}
                    self.connectionHandler.send(payload)
                    message[KEY_READ] = True

                self.addMsg(
                    message, side="right" if message[KEY_SRC_ID] == self.userId else "left")
                updateUserlist = True
        if updateUserlist:
            self.sendUpdateUserList()
        if self.recieveMessagesAppendGetNew:
            self.recieveMessagesAppendGetNew = False
            self.sendGetNewMessages()

    def addMsg(self, message, side):
        if len(self.msgPanes) >= GUI_DEFAULT_MESSAGE_COUNT:
            self.msgPanes[0].pack_forget()
            self.msgPanes.pop(0)
        msgPane = MsgPane(self.msgFrame, message=message, side=side)
        msgPane.pack(side="top", fill="x")
        self.msgPanes.append(msgPane)

    def sendMessage(self, _=None):
        if self.selectedChatId == ALL_CHAT_ID:
            payload = {KEY_USER_ID: self.userId, KEY_PASSOWRD: self.userPassword,
                       KEY_TMP_MESSAGE_ID: time_ns(), KEY_SRC_ID: self.userId,
                       KEY_MSG: self.msgEntry.get(), KEY_TIMESTAMP: datetime.now()}
            payload = {KEY_ACTION: ACTION_SEND_EVERYONE, KEY_DATA: payload}
        else:
            payload = {KEY_USER_ID: self.userId, KEY_PASSOWRD: self.userPassword,
                       KEY_TMP_MESSAGE_ID: time_ns(), KEY_CHAT_ID: self.selectedChatId,
                       KEY_SRC_ID: self.userId, KEY_MSG: self.msgEntry.get(),
                       KEY_TIMESTAMP: datetime.now()}
            payload = {KEY_ACTION: ACTION_SEND, KEY_DATA: payload}
        self.connectionHandler.send(payload)
        payload[KEY_DATA][KEY_READ] = False
        self.addMsg(payload[KEY_DATA], side="right")
        self.msgEntry.delete(0, tk.END)

    def sendMessageResponse(self, payload):
        if payload[KEY_CHAT_ID] == self.selectedChatId:
            for msgPane in self.msgPanes:
                if (KEY_TMP_MESSAGE_ID in msgPane.message and
                        msgPane.message[KEY_TMP_MESSAGE_ID] == payload[KEY_TMP_MESSAGE_ID]):
                    msgPane.message[KEY_MESSAGE_ID] = payload[KEY_MESSAGE_ID]

    def recieveNotifyUsersUpdate(self, _):
        self.sendUpdateUserList()

    def recieveNotifyNewMessage(self, payload):
        if payload[KEY_CHAT_ID] == self.selectedChatId:
            self.sendGetNewMessages()
        else:
            self.sendUpdateUserList()

    def recieveNotifyMarkRead(self, payload):
        if payload[KEY_CHAT_ID] == self.selectedChatId:
            for msgPane in self.msgPanes:
                if (KEY_MESSAGE_ID in msgPane.message and
                        msgPane.message[KEY_MESSAGE_ID] == payload[KEY_MESSAGE_ID]):
                    msgPane.message[KEY_READ] = True
                    msgPane.updateMsgInfo()

    def onClose(self):
        if self.connectionHandler is not None:
            if self.userId != "":
                self.sendLogoutUser()
            self.connectionHandler.kill()
        self.master.destroy()


if __name__ == "__main__":
    gui = Gui()
    gui.mainloop()
