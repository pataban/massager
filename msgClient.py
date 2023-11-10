import requests as req
import tkinter as tk
import time

class Gui(tk.Frame):
    def __init__(self, master=tk.Tk()):
        super().__init__(master)
        master.title("message server client")
        self.pack()
        self.dstUserId=""
        self.registrationFrame=None
        self.chatFrame=None
        self.userListFrame=None
        self.createRegistrationLayout()
    
    def createRegistrationLayout(self):
        if(self.chatFrame!=None):   
            self.chatFrame.pack_forget()
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

        self.loginButton=tk.Button(self.registrationFrame,text="login",command=self.loginUser)
        self.loginButton.grid(row=2,column=0)
        self.registerButton=tk.Button(self.registrationFrame,text="register",command=self.registerUser)
        self.registerButton.grid(row=2,column=1)
        
        self.loginResult=tk.Label(self.registrationFrame,text="")
        self.loginResult.grid(row=3,column=0)
        
    def createChatroomLayout(self):
        if(self.registrationFrame!=None):   
            self.registrationFrame.pack_forget()
            self.pack()
        if(self.chatFrame!=None):   
            self.chatFrame.pack(side="top")
            self.chatIdLabel["text"]="Chat with: "+self.dstUserId
            if(self.chatIdLabel["text"][-1]==' '):
                self.chatIdLabel["text"]+="everyone"
            self.pack()
            return
        self.chatFrame=tk.Frame(self)
        self.chatFrame.pack(side="top")

        self.chatInfoFrame=tk.Frame(self.chatFrame)
        self.chatInfoFrame.grid(row=0)
        userIdLabel=tk.Label(self.chatInfoFrame,text="User Id: "+self.userId)
        userIdLabel.grid(row=0,column=0)
        self.chatIdLabel=tk.Label(self.chatInfoFrame,text="Chat with: "+self.dstUserId)
        if(self.chatIdLabel["text"][-1]==' '):
            self.chatIdLabel["text"]+="everyone"
        self.chatIdLabel.grid(row=0,column=1)
        showUsersButton=tk.Button(self.chatInfoFrame,text="Show users",command=self.createUserList)
        showUsersButton.grid(row=0,column=2)
        logoutButton=tk.Button(self.chatInfoFrame,text="Logout",command=self.logoutUser)
        logoutButton.grid(row=0,column=3)


        self.messagesFrame=tk.Frame(self.chatFrame)
        self.messagesFrame.grid(row=1)
        self.messageLabels=[]
        for i in range(1,10):
            self.messageLabels.append(tk.Label(self.messagesFrame,text=""))
            self.messageLabels[-1].grid(row=i-1,column=0)
        
        self.messagingFrame=tk.Frame(self.chatFrame)
        self.messagingFrame.grid(row=2)
        self.messageEntry=tk.Entry(self.messagingFrame)
        self.messageEntry.grid(row=0,column=0)
        self.messageEntry.bind("<Return>",self.sendMessage)
        self.messageEntryButton=tk.Button(self.messagingFrame,text="Send",command=self.sendMessage)
        self.messageEntryButton.grid(row=0,column=1)

        self.waitForMessages()


    def registerUser(self):
        if((self.idInput.get()=="")or(self.passInput.get()=="")):
            self.loginResult["text"]="no id or password provided"
            self.update()
            return
        res=req.post("http://127.0.0.1:5000/api/users/register"
            ,data={"userId":self.idInput.get(),"password":self.passInput.get()})
        if(res.text=="Registered successfully"):
            self.userId=self.idInput.get()
            self.idInput.delete(0,1000)
            self.userPass=self.passInput.get()
            self.passInput.delete(0,1000)
            return self.createChatroomLayout()
        else:
            self.loginResult["text"]="Id alredy taken"
            self.update()
            return
            

    def loginUser(self):
        if((self.idInput.get()=="")or(self.passInput.get()=="")):
            self.loginResult["text"]="no id or password provided"
            self.update()
            return
        res=req.post("http://127.0.0.1:5000/api/users/login"
            ,data={"userId":self.idInput.get(),"password":self.passInput.get()})
        if(res.text=="Login successfull"):
            self.userId=self.idInput.get()
            self.idInput.delete(0,1000)
            self.userPass=self.passInput.get()
            self.passInput.delete(0,1000)           
            return self.createChatroomLayout()
        else:
            self.loginResult["text"]="wrong id or password"
            self.update()
            return
    
    def logoutUser(self):
        res=req.post("http://127.0.0.1:5000/api/users/logout"
            ,data={"userId":self.userId,"password":self.userPass})
        print(res.text)
        if(res.text=="Logout successfull"):
            return self.createRegistrationLayout()
        return
    

    def waitForMessages(self):
        while(True):
            res_raw=req.get("http://127.0.0.1:5000/api/users"
                ,data={"userId":self.userId,"password":self.userPass})
            #print(res_raw.text)
            res=res_raw.json()
            res.reverse()
            res.append(None)
            j=0
            while(res[j]!=None):
                i=0
                while(i+1<len(self.messageLabels)):
                    self.messageLabels[i]["text"]=self.messageLabels[i+1]["text"]
                    i+=1
                self.messageLabels[-1]["text"]=res[j]["srcId"]+":\n"+res[j]["msg"]
                j+=1
            self.messagesFrame.update()
            time.sleep(1)
    
    def sendMessage(self,event=None):
        if(self.dstUserId==""):
            res=req.post("http://127.0.0.1:5000/api/send/all"
                ,{"userId":self.userId,"password":self.userPass,"msg":self.messageEntry.get()})
        else:
            res=req.post("http://127.0.0.1:5000/api/send",{"userId":self.userId,
                "password":self.userPass,"dstUserId":self.dstUserId,"msg":self.messageEntry.get()})
        i=0
        while(i+1<len(self.messageLabels)):
            self.messageLabels[i]["text"]=self.messageLabels[i+1]["text"]
            i+=1
        self.messageLabels[-1]["text"]=self.userId+":\n"+self.messageEntry.get()
        self.messageEntry.delete(0,1000)
        self.messagesFrame.update()

    def createUserList(self):
        if(self.chatFrame!=None):   
            self.chatFrame.pack_forget()
            self.pack()
        if(self.registrationFrame!=None):   
            self.registrationFrame.pack_forget()
            self.pack()
        if(self.userListFrame!=None):
            self.userListFrame.pack(side="top") 
            self.updateUserList()
            self.pack()   
            self.userListFrame.update()
            return
        self.userListFrame=tk.Frame(self)
        self.userListFrame.pack(side="top")

        self.selectUserListbox=tk.Listbox(self.userListFrame,width=50,height=15)
        self.selectUserListbox.pack(side="top")
        #self.selectUserListbox.grid(row=0)
        
        selectUserButton=tk.Button(self.userListFrame,text="Enter",command=self.chatSelected)
        selectUserButton.pack(side="bottom")
        #selectUserButton.grid(row=1)
        return self.updateUserList()


    def updateUserList(self):
        res_raw=req.get("http://127.0.0.1:5000/api/users/all"
            ,data={"userId":self.userId,"password":self.userPass})
        #print(res_raw.text)
        res=res_raw.json()
        #print(res)
        self.selectUserListbox.delete(0,tk.END)
        self.selectUserListbox.insert(1,"everyone ")
        res.append(None)
        i=0
        while(res[i]!=None):
            text=res[i]["userId"]
            if(res[i]["active"]==True):
                text+="\t(active)"
            else:
                text+="\t(pasive)"
            self.selectUserListbox.insert(i+2,text)
            i+=1


    def chatSelected(self):
        sel=self.selectUserListbox.curselection()
        if(len(sel)==0):
            return
        self.dstUserId=self.selectUserListbox.get(sel)[:-9]
        self.userListFrame.pack_forget()
        self.pack()
        return self.createChatroomLayout()

Gui().mainloop()



"""
data={"recieverId":"qwe","msg":"hihi"}
res=req.post("http://127.0.0.1:5000/api/send?id=asd",data)
print(res.text)
data2={"msg":"nooooo"}
res=req.post("http://127.0.0.1:5000/api/send/all?id=asd",data2)
print(res.text)
"""