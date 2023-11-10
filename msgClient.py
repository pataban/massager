import requests as req
import tkinter as tk
import time

class Gui(tk.Frame):
    def __init__(self, master=tk.Tk()):
        super().__init__(master)
        master.title("message server client")
        self.pack()
        self.createWidgets()
    
    def createWidgets(self):
        self.registrationFrame=tk.Frame()
        self.registrationFrame.pack(side="top")
        self.idInput=tk.Entry(self.registrationFrame)
        #self.idInput.pack(side="top")
        self.idInput.grid(row=0)
        self.idInputButton=tk.Button(self.registrationFrame,text="join",command=self.joinChatroom)
        #self.idInputButton.pack(side="bottom")
        self.idInputButton.grid(row=1)
        self.idInputResult=tk.Label(self.registrationFrame,text="")
        #self.idInputResult.pack(side="right")
        self.idInputResult.grid(row=3)
        
    def createChatroomLayout(self):
        self.registrationFrame.pack_forget()
        self.pack()
        self.chatFrame=tk.Frame(self)
        self.chatFrame.pack(side="top")
        self.userIdLabel=tk.Label(self.chatFrame,text="userId: "+self.userId)
        self.userIdLabel.pack(side="top")
        self.messagingFrame=tk.Frame(self.chatFrame)
        self.messagingFrame.pack(side="bottom")
        self.messageBox=tk.Frame(self.messagingFrame)
        self.messageBox.pack(side="top")
        self.messageLabels=[]
        for i in range(1,10):
            self.messageLabels.append(tk.Label(self.messageBox,text=""))
            self.messageLabels[-1].grid(row=i-1,column=0)
        self.messageEntry=tk.Entry(self.messagingFrame)
        self.messageEntry.pack(side="bottom")
        self.messageEntry.bind("<Return>",self.sendMessage)
        self.waitForMessages()


    def joinChatroom(self):
        if(self.idInput.get()==""):
            self.idInputResult["text"]="no id provided"
            self.update()
            return
        res=req.post("http://127.0.0.1:5000/api/users/register?id="+self.idInput.get())
        if(res.text=="Registered successfully"):
            self.userId=self.idInput.get()
            return self.createChatroomLayout()
        else:
            self.idInputResult["text"]="Id alredy taken"
            self.update()
            return
            """self.userId=self.idInput.get()
            return self.createChatroomLayout()"""

    def waitForMessages(self):
        while(True):
            res=req.get("http://127.0.0.1:5000/api/users?id="+self.userId).json()
            res.reverse()
            res.append(None)
            j=0
            while(res[j]!=None):
                i=0
                while(i+1<len(self.messageLabels)):
                    self.messageLabels[i]["text"]=self.messageLabels[i+1]["text"]
                    i+=1
                self.messageLabels[-1]["text"]=res[j]["senderId"]+":\n"+res[j]["msg"]
                j+=1
            self.messageBox.update()
            time.sleep(0.5)
    
    def sendMessage(self,event):
        res=req.post("http://127.0.0.1:5000/api/send/all?id="+self.userId,{"msg":self.messageEntry.get()})
        self.messageEntry.delete(0,1000)
        self.messageBox.update()

Gui().mainloop()



"""
data={"recieverId":"qwe","msg":"hihi"}
res=req.post("http://127.0.0.1:5000/api/send?id=asd",data)
print(res.text)

data2={"msg":"nooooo"}
res=req.post("http://127.0.0.1:5000/api/send/all?id=asd",data2)
print(res.text)
"""