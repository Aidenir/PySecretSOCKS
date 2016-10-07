#!/usr/bin/env python
from __future__ import division, absolute_import, print_function, unicode_literals
import base64
import secretsocks
import struct
import traceback
import time
import socket
import threading
import sys
PY3 = False
if sys.version_info[0] == 3:
    import queue as Queue
    PY3 = True
else:
    import Queue
    range = xrange


# The client class which connects out to a server over TCP/IP
class Client(secretsocks.Client):
    # Initialize our data channel
    def __init__(self, ip, port):
        secretsocks.Client.__init__(self)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((ip, port))
        s.settimeout(2)
        self.data_channel = s
        self.alive = True
        self.start()

    # Receive data from our data channel and push it to the receive queue
    def recv(self):
        while self.alive:
            try:
                string = ""
                while len(string) == 0 or string[0] != ',' or string.count(',') %3 != 0:
                    data = self.data_channel.recv(4092)
                    string = string + data.decode('utf-8')
                print("###################CLIENT###################")
                noMessages = int(string.count(',') / 3)
                print(str(noMessages) + " messages should be processed")
                index = 0
                for i in range(0,noMessages):
                    print("Process message")
                    stringMessage = string[index:]
                    firstindex = string.index(',')
                    secondindex = string.index(',', firstindex + 1)
                    thirdindex = string.index(',', secondindex + 1)
                    size = string[firstindex + 1: secondindex]
                    msg = string[secondindex + 1 :thirdindex]
                    if sys.getsizeof(msg) != int(size):
                        print("Wrong size, message is corrupt, header says: " + size + " but size is " + str(sys.getsizeof(msg)))
                    #print("Recieved message: " + msg)

                    data = base64.b64decode(msg)
                    bytes = struct.unpack('<HH',data[:4])
                    print("id: " + str(bytes[0]) + " size: " + str(bytes[1]))
                    body = data[4: 4 + int(bytes[1])]
                    print(body)


                    index = thirdindex
                    self.recvbuf.put(data)
                    print("Message " + str(i) + " of " + str(noMessages) + " processed")
                print("Finished")
            except socket.timeout:
                continue
            except:
                print("Exception " + traceback.format_exc())
                self.alive = False
                self.data_channel.close()

    # Take data from the write queue and send it over our data channel
    def write(self):
        while self.alive:
            try:
                data = self.writebuf.get(timeout=10)
            except Queue.Empty:
                continue
            base = base64.b64encode(data)
            strBase = base.decode('utf-8')
            size = sys.getsizeof(strBase)
            if size > 4092:
                messages = int(size / 4092)
                print("Message should be sent in " + str(messages) + " chunks")
            msg = ","+str(size)+","+strBase+","
            #print("Send to server: " + msg)
            print("Send c->s message size: " + str(size))

            self.data_channel.sendall(str.encode(msg))


class Server(secretsocks.Server):
    # Initialize our data channel
    def __init__(self, ip, port):
        secretsocks.Server.__init__(self)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((ip, port))
        s.listen(1)
        self.data_channel, nill = s.accept()
        self.data_channel.settimeout(2)
        self.alive = True
        self.start()

    # Receive data from our data channel and push it to the receive queue
    def recv(self):
        while self.alive:
            try:
                string = ""
                while len(string) == 0 or string[0] != ',' or string.count(',') %3 != 0:
                    data = self.data_channel.recv(4092)
                    string = string + data.decode('utf-8')
                print("###################SERVER###################")
                noMessages = string.count(',') / 3
                #print(str(noMessages) + " messages should be processed")
                firstindex = string.index(',')
                secondindex = string.index(',', firstindex + 1)
                thirdindex = string.index(',', secondindex + 1)
                size = string[firstindex + 1: secondindex]
                msg = string[secondindex + 1 :thirdindex]
                if sys.getsizeof(msg) != int(size):
                    print("Wrong size, message is corrupt, header says: " + size + " but size is " + str(sys.getsizeof(msg)))
                #print("Recieved message: " + msg)
                data = base64.b64decode(msg)
                self.recvbuf.put(data)
            except socket.timeout:
                continue
            except:
                print("close" + str(sys.exc_info()[0]))
                self.alive = False
                self.data_channel.close()

    # Take data from the write queue and send it over our data channel
    def write(self):
        while self.alive:
            try:
                data = self.writebuf.get(timeout=10)
            except Queue.Empty:
                continue
            base = base64.b64encode(data)
            strBase = base.decode('utf-8')
            size = sys.getsizeof(strBase)
            if size > 4092:
                messages = size / 4092
                print("Message should be sent in " + str(messages) + " chunks")
            msg = ","+str(size)+","+strBase+","
            #print("Send to client: " + msg)
            print("Send s->c message size: " + str(size))

            self.data_channel.sendall(str.encode(msg))

def start_fake_remote():
    Server('127.0.0.1', 9991)

if __name__ == '__main__':
    # Set secretsocks into debug mode
    secretsocks.set_debug(False)

    # Create a server object in its own thread
    print('Starting the fake remote server...')
    t = threading.Thread(target=start_fake_remote)
    t.daemon = True
    t.start()

    # Create the client object
    print('Creating a the client...')
    time.sleep(2)
    client = Client('127.0.0.1', 9991)

    # Start the standard listener with our client
    print('Starting socks server...')
    listener = secretsocks.Listener(client, host='0.0.0.0', port=9998)
    listener.wait()
