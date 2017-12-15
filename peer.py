import gevent
from gevent import socket, Greenlet
from gevent import monkey; monkey.patch_all()
monkey.patch_all()

import select
import Queue
import sys
import traceback
import json
from uuid import uuid4
import time
import threading
from functools import partial

def busy_wait(dt):   
    current_time = time.time()
    while (time.time() < current_time+dt):
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
			"in":[self.socket],
			"out":[]
		}
	def tpeername(self):
		return (self.address, self.port)
	def speername(self):
		return self.address + ":"+ str(self.port)

	def on(self, key):
		def decorator(f):
			self.routes[key] = partial(f, self)
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
				readable, writable, exceptional = select.select(self.connected["in"], self.connected["out"], self.connected["in"], 30)
				for s in readable:
					if s is self.socket:
						# A "readable" server socket is ready to accept a connection
						connection, client_address = s.accept()
						connection.setblocking(0)

						self.connected["in"].append(connection)

						# Give the connection a queue for data we want to send
						self.connected[connection] = {
							"in":Queue.Queue(),
							"out":Queue.Queue()
						}
					else:
						try:
							data = s.recv(self.buffer_size)
						except Exception as e:
							data = None

						if data:
							# A readable client socket has data
							print >>sys.stderr, 'received "%s" from %s to %s' % (data, s.getpeername(), self.speername())
							self.connected[s]["in"].put(data)
							# Add output channel for response
							if s not in self.connected["out"]:
								self.connected["out"].append(s)
						else:
							# Interpret empty result as closed connection
							print >>sys.stderr, 'closing', client_address, 'after reading no data'
							# Stop listening for input on the connection

							self.connected["in"].remove(s)
							if s in self.connected["out"]:
								self.connected["out"].remove(s)
							s.close()

							# Remove message queue
							del self.connected[s]

		 		for s in writable:
					try:
						'''
						if not s in self.has_thread:
							t = threading.Thread(target=self.work, args=(s,))
							t.start()
							self.has_thread.append(s)
						'''
						input = self.connected[s]["in"].get_nowait()
						try:
							msg = json.loads(input)
						except ValueError:
							pass

						if "key" in msg:
							if msg["key"] in self.routes:
								output = json.dumps(self.serve(msg["key"], msg))
								self.connected[s]["out"].put(output)
								print output

						output = self.connected[s]["out"].get_nowait()
					except Queue.Empty:
						# No messages waiting so stop checking for writability.
						print >>sys.stderr, 'output queue for', s.getpeername(), 'is empty'
						self.connected["out"].remove(s)
					else:
						print >>sys.stderr, 'sending "%s" to %s from %s' % (output, s.getpeername(),  self.speername())
						s.send(output)

				for s in exceptional:
					print >>sys.stderr, 'handling exceptional condition for', s.getpeername()
					# Stop listening for input on the connection
					self.connected["in"].remove(s)
					if s in self.connected["out"]:
					    self.connected["out"].remove(s)
					s.close()

					# Remove message queue
					del self.connected[s]

				if not (readable or writable or exceptional):
					print >>sys.stderr, '  timed out, do some other work here'
					continue

			except Exception as e:
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
			"id":str(uuid4()),
			"key":key,
			"body":data
		}
		s.send(json.dumps(msg))
		data = s.recv(1024)
		try:
			msg = json.loads(data)
		except ValueError:
			pass

		if "key" in msg:
			if msg["key"] in self.routes:
				output = json.dumps(self.serve(msg["key"], msg))
				
		return output
		'''
		totalsent = 0
		while totalsent < len(msg):
			sent = self.socket.send(msg[totalsent:])
			if sent == 0:
			    raise RuntimeError("socket connection broken")
			totalsent = totalsent + sent
		'''


#peer1.ping(peer2.tpeername())

#gevent.joinall([g, g2])

'''peer2 = Peer("127.0.0.1", 002)
peer2.create()

print peer1.socket
peer1.connect(peer2.address, peer2.port)
'''
'''
peer.broadcast("key",{
	
})

def onKey():
	pass

peer.on("key", function)
'''