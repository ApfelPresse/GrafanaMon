import os

from twisted.application import internet, service
from twisted.protocols.portforward import ProxyFactory

SRC_PORT = int(os.environ["SRC_PORT"])
DST_PORT = int(os.environ["DST_PORT"])

application = service.Application("Proxy")
ps = internet.TCPServer(SRC_PORT,
                        ProxyFactory(os.environ["DST_IP"], DST_PORT),
                        50,
                        os.environ["SRC_IP"])
ps.setServiceParent(application)
