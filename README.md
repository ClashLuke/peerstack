# peerstack
Python Peer-to-Peer Framework

# Project Status
This project is very early mad science still heavily under research and development.

# Examples

```python
from peer import Peer
import threading
from uuid import uuid4
peer1 = Peer("127.0.0.1", 123)
peer2 = Peer("127.0.0.1", 456)

@peer1.on("pong")
def Pong(peer, msg):
	print "PONG"
	return msg

@peer2.on("ping")
def ping(peer, msg):
	msg["key"] = "pong"
	return msg

t1 = threading.Thread(target=peer1.listen)
t1.start()
t2 = threading.Thread(target=peer2.listen)
t2.start()

peer1.send(peer2, "ping", {})
```
