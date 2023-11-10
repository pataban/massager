import socket
import threading
import time
import json
import struct

host="127.0.0.1"
port=5000


def send_msg(sock, msg):
        # Prefix each message with a 4-byte length (network byte order)
        msg = struct.pack('>I', len(msg)) + msg
        sock.sendall(msg)

def recv_msg(sock):
    # Read message length and unpack it into an integer
    raw_msglen = recvall(sock, 4)
    if not raw_msglen:
        return None
    msglen = struct.unpack('>I', raw_msglen)[0]
    # Read the message data
    return recvall(sock, msglen)

def recvall(sock, n):
    # Helper function to recv n bytes or return None if EOF is hit
    data = bytearray()
    while len(data) < n:
        packet = sock.recv(n - len(data))
        if not packet:
            return None
        data.extend(packet)
    return data

class ClientHandler(threading.Thread):
    def __init__(self, gui,tLock):
        threading.Thread.__init__(self)
        self.gui=gui
        self.tLock=tLock
        self.sc = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.sc.connect((host,port))
        self.active=True

    def run(self):
        while self.active:
            msg = recv_msg(self.sc)
            msg=msg.decode()
            print("recieved:",msg)
            self.tLock.acquire()

            self.msgHandler(msg)

            self.tLock.release()
        self.sc.close()

    def msgHandler(self,data):
        count=0
        i=0
        for j in range(0,len(data)):
            if(data[j]=="{"): count+=1
            if(data[j]=="}"): count-=1
            if(count==0):
                object=json.loads(data[i:j+1])
                #print(object)
                action=object["action"]
                object=object["data"]

                if(action=="login"):
                    self.gui.loginUser(object)
                if(action=="logout"):
                    self.gui.logoutUser(object)
                if(action=="register"):
                    self.gui.registerUser(object)
                if(action=="getUsers"):
                    self.gui.updateUserList(object)
                if(action=="recieve"):
                    self.gui.recieveMessage(object)
                """if(action=="send"):
                    self.gui.api_send(self,object)
                if(action=="sendEveryone"):
                    self.gui.api_send_everyone(self,object)"""

                i=j+1

    
    def send(self,data):
        data=bytes(json.dumps(data),"utf-8")
        print("sending:",data)
        send_msg(self.sc,data)

    def kill(self):
        lock=threading.Lock()
        lock.acquire()
        self.active=False
        lock.release()
