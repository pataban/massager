import requests as req
import tkinter as tk
import time
import datetime as dt
import tkinter.font as font
import asyncio
import websockets
import socket
import json
from flask import jsonify
from ClientHandler import ClientHandler
import threading

def getTime():
    return dt.datetime.now().strftime("%d.%m.%Y %H:%M:%S")



class msgPane(tk.Frame):
    def __init__(self, master, msg, time, row, column):
        super().__init__(master)
        self.msg=tk.Button(self,text=msg, state="disabled",fg="black")
        self.msg.pack(side="bottom")

        timeFont=font.Font(size=7)
        self.time=tk.Label(self,text=time,font=timeFont,fg="grey")
        self.time.pack(side="top")
        self.grid(row=row,column=column)


class Gui(tk.Frame):
    def __init__(self, master=tk.Tk()):
        super().__init__(master)
        master.title("message server client")
        self.pack()
        self.dstUserId=""
        self.registrationFrame=None
        self.userFrame=None
        self.chatFrame=None
        self.userListFrame=None
        self.createRegistrationLayout()
        self.tLock=threading.Lock()
        self.conn=ClientHandler(self,self.tLock)
        self.conn.start()

    def createRegistrationLayout(self):
        if(self.userFrame!=None):   
            self.userFrame.pack_forget()
            self.pack()
        if(self.registrationFrame!=None):
            self.registrationFrame.pack(side="top") 
            self.pack()   
            return
        self.registrationFrame=tk.Frame(self)
        self.registrationFrame.pack(side="top")

        idLabel=tk.Label(self.registrationFrame,text="User Id:")
        idLabel.grid(row=0,column=0)
        self.idInput=tk.Entry(self.registrationFrame)
        self.idInput.grid(row=0,column=1)
        
        passLabel=tk.Label(self.registrationFrame,text="Password:")
        passLabel.grid(row=1,column=0)
        self.passInput=tk.Entry(self.registrationFrame)
        self.passInput.grid(row=1,column=1)

        self.loginButton=tk.Button(self.registrationFrame,text="login",command=self.sendLoginUser)
        self.loginButton.grid(row=2,column=0)
        self.registerButton=tk.Button(self.registrationFrame,text="register",command=self.sendRegisterUser)
        self.registerButton.grid(row=2,column=1)
        
        self.loginResult=tk.Label(self.registrationFrame,text="")
        self.loginResult.grid(row=3,column=0)
        
    def createUserLayout(self):
        if(self.registrationFrame!=None):   
            self.registrationFrame.pack_forget()
            self.pack()
        if(self.userFrame!=None):   
            self.chatFrame.pack_forget()
            self.userFrame.pack(side="top")
            self.sendUpdateUserList()
            self.userIdLabel["text"]=self.userId
            self.pack()
            return
        self.userFrame=tk.Frame(self)
        self.userFrame.pack(side="top")

        self.userMenuFrame=tk.Frame(self.userFrame)
        self.userMenuFrame.pack(side="top")
        self.userIdLabel=tk.Label(self.userMenuFrame,text="User Id: "+self.userId)
        self.userIdLabel.grid(row=0,column=0)
        logoutButton=tk.Button(self.userMenuFrame,text="Logout",command=self.sendLogoutUser)
        logoutButton.grid(row=0,column=1)

        self.createUserList()


    def createUserList(self):
        if(self.userListFrame!=None):
            self.userListFrame.pack(side="left") 
            self.sendUpdateUserList()
            self.pack()
            return
        self.userListFrame=tk.Frame(self.userFrame)
        self.userListFrame.pack(side="left")

        self.selectUserListbox=tk.Listbox(self.userListFrame,width=30, selectmode="single")
        self.selectUserListbox.pack(side="top")
        
        selectUserButton=tk.Button(self.userListFrame,text="Select chat",command=self.chatSelected)
        selectUserButton.pack(side="bottom")
        return self.sendUpdateUserList()


    def chatSelected(self):
        sel=self.selectUserListbox.curselection()
        if(len(sel)==0):
            return
        if(sel[0]==0):
            self.dstUserId=""   
        else:
            self.dstUserId=self.userList[sel[0]-1][0]
        return self.createChatroom()


    def createChatroom(self):
        if(self.chatFrame!=None):   
            self.chatFrame.pack(side="right")
            self.chatInfoLabel["text"]="Chat with: "+self.dstUserId
            if(self.dstUserId==''):
                self.chatInfoLabel["text"]+="everyone"
            self.msgFrame.grid_forget()
            self.msgFrame=tk.Frame(self.chatFrame)
            self.msgFrame.grid(row=1)
            self.msgPanes=[]
            self.pack()
            self.update()
            self.sendGetMessageHistory()
            self.sendRecieve()
            return

        self.chatFrame=tk.Frame(self.userFrame)
        self.chatFrame.pack(side="right")
        
        self.chatInfoLabel=tk.Label(self.chatFrame,text="Chat with: "+self.dstUserId)
        if(self.dstUserId==''):
            self.chatInfoLabel["text"]+="everyone"
        self.chatInfoLabel.grid(row=0)

        self.msgFrame=tk.Frame(self.chatFrame)
        self.msgFrame.grid(row=1)
        self.msgPanes=[]
        
        self.msgEntryFrame=tk.Frame(self.chatFrame)
        self.msgEntryFrame.grid(row=2)
        self.msgEntry=tk.Entry(self.msgEntryFrame)
        self.msgEntry.grid(row=0,column=0)
        self.msgEntry.bind("<Return>",self.sendMessage)
        self.msgEntryButton=tk.Button(self.msgEntryFrame,text="Send",command=self.sendMessage)
        self.msgEntryButton.grid(row=0,column=1)

        self.sendGetMessageHistory()
        self.sendRecieve()


    def sendUpdateUserList(self):
        data={"userId":self.userId,"password":self.userPass}
        data={"action":"getUsers","data":data}
        self.conn.send(data)


    def updateUserList(self,res):
        self.selectUserListbox.delete(0,tk.END)
        self.selectUserListbox.insert(1,"everyone ")
        res.append(None)
        i=0
        self.userList=[]
        while(res[i]!=None):
            self.userList.append((res[i]["userId"],res[i]["active"],res[i]["count"]))
            status="      passive"
            if(self.userList[-1][1]):
                status="      \tactive"
            unred=" "
            if(self.userList[-1][2]>0):
                unred=f"      ({self.userList[-1][2]} new)"
            user=self.userList[-1][0]+status+unred
            self.selectUserListbox.insert(i+2,user)
            i+=1
        self.userListFrame.update()


    def sendRegisterUser(self):
        if((self.idInput.get()=="")or(self.passInput.get()=="")):
            self.loginResult["text"]="no id or password provided"
            self.update()
            return
        data={"userId":self.idInput.get(),"password":self.passInput.get()}
        data={"action":"register","data":data}
        self.conn.send(data)
        

    def registerUser(self,res):
        if(res=="Registered successfully"):
            self.userId=self.idInput.get()
            self.idInput.delete(0,1000)
            self.userPass=self.passInput.get()
            self.passInput.delete(0,1000)
            self.loginResult["text"]=""
            return self.createUserLayout()
        else:
            self.loginResult["text"]="Id alredy taken"
            self.update()
            return
            

    def sendLoginUser(self):
        if((self.idInput.get()=="")or(self.passInput.get()=="")):
            self.loginResult["text"]="no id or password provided"
            self.update()
            return
        data={"userId":self.idInput.get(),"password":self.passInput.get()}
        data={"action":"login","data":data}
        self.conn.send(data)
        

    def loginUser(self,res):
        if(res=="Login successfull"):
            self.userId=self.idInput.get()
            self.idInput.delete(0,1000)
            self.userPass=self.passInput.get()
            self.passInput.delete(0,1000)  
            self.loginResult["text"]=""         
            return self.createUserLayout()
        else:
            self.loginResult["text"]="wrong id or password"
            self.update()
            return
    

    def sendLogoutUser(self):
        data={"userId":self.userId,"password":self.userPass}
        data={"action":"logout","data":data}
        self.conn.send(data)


    def logoutUser(self,res):
        if(res=="Logout successfull"):
            return self.createRegistrationLayout()
        return
    

    def sendGetMessageHistory(self):
        data={"userId":self.userId,"password":self.userPass
            ,"chatId":self.dstUserId,"count":8}
        data={"action":"messageHistory","data":data}
        self.conn.send(data)


    def sendRecieve(self):
        data={"userId":self.userId,"password":self.userPass
            ,"srcId":self.dstUserId}
        data={"action":"recieve","data":data}
        self.conn.send(data)


    def recieveMessage(self,res):
        res.append(None)
        j=0
        while(res[j]!=None):
            if(res[j]["dstId"]==self.dstUserId or res[j]["srcId"]==self.dstUserId or res[j]["red"]):
                column=0
                if(res[j]["srcId"]==self.userId):
                    column=1
                timestamp=res[j]["time"]+", red"
                self.addMsg(res[j]["msg"],timestamp,column)
                if((not res[j]["red"]) and (res[j]["dstId"]==self.userId) ):        #oznacza wszystko jako odczytane przy zmianie chatu
                    data={"userId":self.userId,"password":self.userPass
                        ,"srcId":self.dstUserId,"dstId":self.userId,"time":res[j]["time"]}
                    data={"action":"markRed","data":data}
                    self.conn.send(data)
            j+=1
        self.msgFrame.update()
    

    def sendMessage(self,event=None):
        if(self.dstUserId==""):
            data={"userId":self.userId,"password":self.userPass
                ,"msg":self.msgEntry.get(),"time":getTime()}
            data={"action":"sendEveryone","data":data}
            self.conn.send(data)
        else:
            data={"userId":self.userId,"password":self.userPass
            ,"dstUserId":self.dstUserId,"msg":self.msgEntry.get()
            ,"time":getTime()}
            data={"action":"send","data":data}
            self.conn.send(data)
        timestamp=getTime()+", unred"
        self.addMsg(self.msgEntry.get(),timestamp,1)
        self.msgEntry.delete(0,1000)
        self.msgEntry.update()


    def addMsg(self,msg,time,column):
        msg=msgPane(self.msgFrame,msg=msg,time=time,row=len(self.msgPanes),column=column)
        self.msgPanes.append(msg)
        if(len(self.msgPanes)>10):
            self.msgPanes[-11].grid_forget()
    

gui=Gui()
gui.mainloop()
gui.conn.kill()

