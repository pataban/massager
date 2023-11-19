import json
import threading

from utils import *
from constants import *


class ConnectionHandler(threading.Thread):
    def __init__(self, sock, maping, threadLock):
        threading.Thread.__init__(self)
        self.sock = sock
        self.maping = maping
        self.threadLock = threadLock

        self.daemon = True
        self.active = True

    def run(self):
        while self.active:
            msg = self.recieveMsg()
            if DEBUG:
                print("recieved:", msg, "\n")

            if msg is not None:
                payload = json.loads(msg, object_hook=datetimeDeserializer)
                with self.threadLock:
                    if payload[KEY_ACTION] in self.maping:
                        self.maping[payload[KEY_ACTION]](
                            self, payload[KEY_DATA])

        if HOOK_ON_CLOSE in self.maping:
            self.maping[HOOK_ON_CLOSE](self)

    def recieveMsg(self):
        # Read message length and unpack it into an integer
        rawMsgLen = self.recieveBytes(4)
        if rawMsgLen is None:
            return None
        msgLen = int.from_bytes(rawMsgLen, "big")

        # Read the message data
        msg = self.recieveBytes(msgLen)
        if msg is None:
            return None
        return msg.decode(encoding="utf-8")

    def recieveBytes(self, n):
        # Helper function to recieve n bytes or return None if EOF is hit
        data = bytearray()
        while len(data) < n:
            try:
                packet = self.sock.recv(n - len(data))
            except ConnectionResetError:
                if HOOK_ON_COLLAPSE in self.maping:
                    self.maping[HOOK_ON_COLLAPSE](self)
                return None
            except ConnectionAbortedError:
                return None
            if packet is None:
                return None
            data.extend(packet)
        return data

    def send(self, payload):
        if DEBUG:
            print("sending:", payload, "\n")
        payload = json.dumps(
            payload, default=datetimeSerializer).encode("utf-8")

        # Prefix each message with a 4-byte length (network byte order)
        payload = len(payload).to_bytes(4, "big") + payload
        try:
            self.sock.sendall(payload)
        except ConnectionResetError:
            if HOOK_ON_COLLAPSE in self.maping:
                self.maping[HOOK_ON_COLLAPSE](self)
        except ConnectionAbortedError:
            pass

    def kill(self):
        self.active = False
        self.sock.close()
