import threading
import tkinter as tk
import tkinter.font as font
from datetime import datetime

from ClientHandler import ClientHandler
from constants import *


class MsgPane(tk.Frame):
    def __init__(self, master, msg, timestamp, read, side):
        super().__init__(master)
        self.side = side
        self.showInfo = False

        msgInfo = timestamp.strftime(TIMESTAMP_FORMAT)
        msgInfo += (CLIENT_MESSAGE_INFO_READ if read else CLIENT_MESSAGE_INFO_UNREAD)
        msgInfoFont = font.Font(size=7)
        self.msgInfo = tk.Label(self, text=msgInfo, font=msgInfoFont)

        self.msg = tk.Button(
            self, text=msg, background="grey", command=self.toggleInfo)
        self.msg.grid(row=1, column=0, sticky="n"+self.side)

    def toggleInfo(self):
        if not self.showInfo:
            self.msgInfo.grid(row=0, column=0, sticky="s"+self.side)
        else:
            self.msgInfo.grid_forget()
        self.showInfo = not self.showInfo


class Gui(tk.Frame):
    def __init__(self, master=tk.Tk()):
        super().__init__(master)
        master.title(CLIENT_WINDOW_TITLE)
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

        self.tLock = threading.Lock()
        self.clientHandler = ClientHandler(self, self.tLock)
        self.clientHandler.start()

    def createLoginLayout(self):
        if self.userMainFrame is not None:
            self.userMainFrame.pack_forget()
        if self.loginFrame is None:
            self.loginFrame = tk.Frame(self)

            idLabel = tk.Label(self.loginFrame, text="User Id:")
            idLabel.grid(row=0, column=0)
            self.userIdEntry = tk.Entry(self.loginFrame)
            self.userIdEntry.grid(row=0, column=1)

            passLabel = tk.Label(self.loginFrame, text="Password:")
            passLabel.grid(row=1, column=0)
            self.userPasswordEntry = tk.Entry(self.loginFrame)
            self.userPasswordEntry.grid(row=1, column=1)

            loginButton = tk.Button(
                self.loginFrame, text="login", command=lambda: self.sendRegisterLoginUser("login"))
            loginButton.grid(row=2, column=0)
            registerButton = tk.Button(
                self.loginFrame, text="register",
                command=lambda: self.sendRegisterLoginUser("register"))
            registerButton.grid(row=2, column=1)

            self.loginResultLabel = tk.Label(self.loginFrame, text="")
            self.loginResultLabel.grid(row=3, column=0, columnspan=2)
        self.loginFrame.pack()

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
                userMenuFrame, text="Logout", command=self.sendLogoutUser)
            logoutButton.grid(row=0, column=1)

            self.userListbox = tk.Listbox(
                self.userMainFrame, width=CLIENT_USER_LIST_WIDTH, selectmode="single")
            self.userListbox.pack(side="left")

            self.userListbox.bind("<<ListboxSelect>>",
                                  lambda _: self.chatSelected())
        self.userMainFrame.pack()
        self.userIdLabel["text"] = "User Id: "+self.userId
        if self.chatFrame is not None:
            self.chatFrame.pack_forget()
        self.sendUpdateUserList()

    def createChatLayout(self):
        if self.chatFrame is None:
            self.chatFrame = tk.Frame(self.userMainFrame)

            self.chatInfoLabel = tk.Label(self.chatFrame, text="")
            self.chatInfoLabel.grid(row=0)

            self.msgFrame = tk.Frame(self.chatFrame)
            self.msgFrame.grid(row=1)

            msgEntryFrame = tk.Frame(self.chatFrame)
            msgEntryFrame.grid(row=2)
            self.msgEntry = tk.Entry(msgEntryFrame)
            self.msgEntry.pack(side="left")
            self.msgEntry.bind("<Return>", self.sendMessage)
            msgEntryButton = tk.Button(
                msgEntryFrame, text="Send", command=self.sendMessage)
            msgEntryButton.pack(side="right")
        self.chatFrame.pack(side="right")
        self.chatInfoLabel["text"] = "Chat with: "+self.selectedChatId
        if self.selectedChatId == '':
            self.chatInfoLabel["text"] += "everyone"
        for mp in self.msgPanes:
            mp.grid_forget()
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
        if actionType not in ("register", "login"):
            return
        if ((self.userIdEntry.get() == "") or (self.userPasswordEntry.get() == "")):
            self.loginResultLabel["text"] = MISSING_LOGIN_DATA_LABEL
            self.update()
            return
        self.userId = self.userIdEntry.get()
        self.userPassword = self.userPasswordEntry.get()
        payload = {"userId": self.userIdEntry.get(
        ), "password": self.userPasswordEntry.get()}
        payload = {"action": actionType, "data": payload}
        self.clientHandler.send(payload)

    def recieveRegisterLoginUser(self, result):
        if result == REGISTER_OK or result == LOGIN_OK:
            self.userIdEntry.delete(0, tk.END)
            self.userPasswordEntry.delete(0, tk.END)
            self.loginResultLabel["text"] = ""
            return self.createUserMainLayout()
        self.loginResultLabel["text"] = result
        self.update()

    def sendUpdateUserList(self):
        payload = {"userId": self.userId, "password": self.userPassword}
        payload = {"action": "getUsers", "data": payload}
        self.clientHandler.send(payload)

    def recieveUpdateUserList(self, result):
        self.userListbox.delete(0, tk.END)
        self.userList = []
        self.userListbox.insert(1, "everyone ")  # TODO random space
        self.userList.append("")
        for user in result:
            self.userList.append(
                (user["userId"], user["active"], user["count"]))
            status = " \tactive" if user["active"] else " \tpassive"
            unred = ""
            if user["count"] > 0:
                unred = f" \t({user['count']} new)"
            self.userListbox.insert(tk.END, user["userId"]+status+unred)
        self.userListbox.update()

    def sendLogoutUser(self):
        payload = {"userId": self.userId, "password": self.userPassword}
        payload = {"action": "logout", "data": payload}
        self.clientHandler.send(payload)

    def recievelogoutUser(self, result):
        if result == LOGOUT_OK:
            return self.createLoginLayout()

    def sendGetMessageHistory(self):
        payload = {"userId": self.userId, "password": self.userPassword,
                   "chatId": self.selectedChatId, "count": DEFAULT_CHAT_HISTORY_SIZE}
        payload = {"action": "messageHistory", "data": payload}
        self.clientHandler.send(payload)

    def sendGetNewMessages(self):
        payload = {"userId": self.userId, "password": self.userPassword,
                   "srcId": self.selectedChatId}  # TODO here srcId and in history chatId why?
        payload = {"action": "recieve", "data": payload}
        self.clientHandler.send(payload)

    def recieveMessage(self, result):
        for message in result:
            if self.selectedChatId in (message["srcId"], message["dstId"]):
                self.addMsg(message["msg"], message["time"], message["read"],
                            side="e" if message["srcId"] == self.userId else "w")
                # oznacza wszystko jako odczytane przy zmianie chatu
                # TODO all-chat-broken (what if dstId is "")
                if ((not message["read"]) and (message["dstId"] == self.userId)):
                    payload = {"userId": self.userId, "password": self.userPassword,
                               "srcId": self.selectedChatId, "dstId": self.userId,
                               "time": message["time"]}
                    payload = {"action": "markRed", "data": payload}
                    self.clientHandler.send(payload)
        if self.recieveMessagesAppendGetNew:
            self.recieveMessagesAppendGetNew = False
            self.sendGetNewMessages()

    def addMsg(self, msg, timestamp, read, side):
        msgPane = MsgPane(self.msgFrame, msg=msg,
                          timestamp=timestamp, read=read, side=side)
        msgPane.grid(row=len(self.msgPanes), column=0, sticky=side)
        self.msgPanes.append(msgPane)
        if len(self.msgPanes) > DEFAULT_CHAT_HISTORY_SIZE:
            self.msgPanes[0].grid_forget()
            self.msgPanes.pop(0)

    def sendMessage(self, _=None):
        if self.selectedChatId == "":
            payload = {"userId": self.userId, "password": self.userPassword,
                       "msg": self.msgEntry.get(), "time": datetime.now()}
            payload = {"action": "sendEveryone", "data": payload}
        else:
            payload = {"userId": self.userId, "password": self.userPassword,
                       "dstUserId": self.selectedChatId, "msg": self.msgEntry.get(),
                       "time": datetime.now()}
            payload = {"action": "send", "data": payload}
        self.clientHandler.send(payload)
        self.addMsg(payload["data"]["msg"],
                    payload["data"]["time"], False, "e")
        self.msgEntry.delete(0, tk.END)


if __name__ == "__main__":
    gui = Gui()
    gui.mainloop()
    gui.clientHandler.kill()
