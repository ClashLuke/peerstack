from peer import Peer
import threading
from uuid import uuid4
peer1 = Peer("127.0.0.1", 123)
peer2 = Peer("127.0.0.1", 456)

@peer1.on("pong")
def Hello(peer, msg):
	print "PONG"
	return msg

@peer2.on("ping")
@peer1.on("ping")
#@peer1.periodic("ping", 1)
def ping(peer, msg):
	msg["key"] = "pong"
	msg["body"]["id"] = str(uuid4())
	return msg

t1 = threading.Thread(target=peer1.listen)
t1.start()
t2 = threading.Thread(target=peer2.listen)
t2.start()

peer1.send(peer2, "ping", {})
