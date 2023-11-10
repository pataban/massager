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

class ServerConnection(threading.Thread):
    def __init__(self, server, client, tLock):
        threading.Thread.__init__(self)
        self.server=server
        self.client=client
        self.tLock=tLock
        
    def run(self):
        while True:
            msg = recv_msg(self.client)
            msg=msg.decode()
            print("recieved:",msg)
            self.tLock.acquire()

            self.msgHandler(msg)
            
            self.tLock.release()
        self.client.close()

    def msgHandler(self,data):
        count=0
        i=0
        for j in range(0,len(data)):
            if(data[j]=="{"): count+=1
            if(data[j]=="}"): count-=1
            if(count==0):
                print(data[i:j+1])
                object=json.loads(data[i:j+1])
                #print(object)
                action=object["action"]
                object=object["data"]

                if(action=="login"):
                    self.server.api_login_user(self,object)
                if(action=="logout"):
                    self.server.api_logout_user(self,object)
                if(action=="register"):
                    self.server.api_register_user(self,object)
                if(action=="getUsers"):
                    self.server.api_get_users(self,object)
                if(action=="unredCount"):
                    self.server.api_unred_count(self,object)
                if(action=="messageHistory"):
                    self.server.api_message_history(self,object)
                if(action=="recieve"):
                    self.server.api_recieve(self,object)
                if(action=="markRed"):
                    self.server.api_mark_red(self,object)
                if(action=="send"):
                    self.server.api_send(self,object)
                if(action=="sendEveryone"):
                    self.server.api_send_everyone(self,object)
                
                i=j+1


    def send(self,data):
        data=bytes(json.dumps(data),"utf-8")
        print("sending:",data)
        send_msg(self.client,data)

    