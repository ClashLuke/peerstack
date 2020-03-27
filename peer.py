import json
import queue
import select
import sys
import time
import traceback
from functools import partial
from uuid import uuid4

from gevent import socket


def busy_wait(dt):
    current_time = time.time()
    while time.time() < (current_time + dt):
        pass


class Peer(object):
    buffer_size = 1024

    def __init__(self, ip, port):
        self.address = ip
        self.port = port
        self.routes = {}
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_lock = None
        self.greenlet = None

        self.connected = {
                "in":  [self.socket],
                "out": []
                }

    def tpeername(self):
        return (self.address, self.port)

    def speername(self):
        return self.address + ":" + str(self.port)

    def add_route(self, key, function):
        self.routes[key] = partial(function, self)

    def add_route_dict(self, routes: dict):
        for key, function in routes.items():
            self.add_route(key, function)

    def on(self, key):
        def decorator(f):
            self.add_route(key, f)
            return f

        return decorator

    def serve(self, key, msg):
        if key in self.routes:
            return self.routes[key](msg)
        return ""

    def listen(self):
        self.socket.setblocking(0)
        self.socket.bind((self.address, self.port))
        self.socket.listen(1)
        while self.connected["in"]:
            try:
                readable, writable, exceptional = select.select(self.connected["in"],
                                                                self.connected["out"],
                                                                self.connected["in"],
                                                                30)
                for s in readable:
                    if s is self.socket:
                        # A "readable" server socket is ready to accept a connection
                        connection, client_address = s.accept()
                        connection.setblocking(0)

                        self.connected["in"].append(connection)
                        # Give the connection a queue for data we want to send
                        self.connected[connection] = {"in":  queue.Queue(),
                                                      "out": queue.Queue()
                                                      }
                    else:
                        try:
                            data = s.recv(self.buffer_size)
                        except Exception as e:
                            data = None

                        if data:
                            # A readable client socket has data
                            self.connected[s]["in"].put(data)
                            # Add output channel for response
                            if s not in self.connected["out"]:
                                self.connected["out"].append(s)
                        else:
                            # Interpret empty result as closed connection
                            # Stop listening for input on the connection

                            self.connected["in"].remove(s)
                            if s in self.connected["out"]:
                                self.connected["out"].remove(s)
                            s.close()

                            # Remove message queue
                            del self.connected[s]

                for s in writable:
                    try:
                        input = self.connected[s]["in"].get_nowait()
                        try:
                            msg = json.loads(input)
                        except ValueError:
                            pass

                        if "key" in msg:
                            if msg["key"] in self.routes:
                                output = json.dumps(self.serve(msg["key"], msg))
                                self.connected[s]["out"].put(output)

                        output = self.connected[s]["out"].get_nowait()
                    except queue.Empty:
                        # No messages waiting so stop checking for writability.
                        self.connected["out"].remove(s)
                    else:
                        s.send(output.encode())

                for s in exceptional:
                    # Stop listening for input on the connection
                    self.connected["in"].remove(s)
                    if s in self.connected["out"]:
                        self.connected["out"].remove(s)
                    s.close()

                    # Remove message queue
                    del self.connected[s]

                if not (readable or writable or exceptional):
                    continue

            except Exception:
                traceback.print_exc(file=sys.stdout)

    def send(self, recipient, key, data):
        address = None
        if type(recipient) is tuple:
            if type(recipient[0]) is str and type(recipient[1]) is int:
                address = recipient

        if type(recipient) is Peer:
            address = (recipient.address, recipient.port)

        if not address:
            raise Exception("Invalid Address")

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(address)
        msg = {
                "id":   str(uuid4()),
                "key":  key,
                "body": data
                }
        s.send(json.dumps(msg).encode())
        data = s.recv(1024)
        try:
            msg = json.loads(data)
        except ValueError:
            pass

        if "key" in msg and msg["key"] in self.routes:
            return json.dumps(self.serve(msg["key"], msg))
