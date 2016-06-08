import socket
import struct
import sys
from httplib import HTTPResponse
from BaseHTTPServer import BaseHTTPRequestHandler
from StringIO import StringIO

import gtk
import gobject

LIB_ID = 'urn:Randuhmm:device:hub:1'
UUID = '2fac1234-31f8-11b4-a222-08002b34c003'
USN = 'uuid:{UUID}::{LIB_ID}'.format(UUID=UUID, LIB_ID=LIB_ID)
MCAST_GRP = '239.255.255.250'
MCAST_PORT = 1900
SERVICE_LOCS = {'1': '127.0.0.1:7766'}

DISCOVERY_MSG = ('M-SEARCH * HTTP/1.1\r\n' +
                 'ST: %(library)s\r\n' +
                 'MX: 2\r\n' +
                 'MAN: "ssdp:discover"\r\n' +
                 'HOST: 239.255.255.250:1900\r\n\r\n')

'''
LOCATION_MSG = ('HTTP/1.1 200 OK\r\n' +
                'EXT:\r\n'
                'ST: %(library)s\r\n'
                'USN: {USN}\r\n'
                'LOCATION: %(loc)s\r\n'
                'SERVER: Linux/1.0 UPnP/1.1 Randuhmm/0.1\r\n'
                'BOOTID.UPNP.ORG: 1234\r\n'
                'CACHE-CONTROL: max-age=0\r\n\r\n').format(USN=USN)
'''

LOCATION_MSG = ('HTTP/1.1 200 OK\r\n' +
                'CACHE-CONTROL: max-age=100\r\n' +
                'EXT:\r\n' +
                'LOCATION: http://172.28.16.27:80/device.json\r\n' +
                'SERVER: Linux/1.0 UPnP/1.0 Randuhmm/0.1\r\n' +
                'ST: %(library)s\r\n' +
                'USN: {USN}\r\n').format(USN=USN)


class Request(BaseHTTPRequestHandler):
    def __init__(self, request_text):
        self.rfile = StringIO(request_text)
        self.raw_requestline = self.rfile.readline()
        self.error_code = self.error_message = None
        self.parse_request()

    def send_error(self, code, message):
        self.error_code = code
        self.error_message = message


class Response(HTTPResponse):
    def __init__(self, response_text):
        self.fp = StringIO(response_text)
        self.debuglevel = 0
        self.strict = 0
        self.msg = None
        self._method = None
        self.begin()


def interface_addresses(family=socket.AF_INET):
    for fam, _, _, _, sockaddr in socket.getaddrinfo('', None):
        if family == fam:
            yield sockaddr[0]


def client(timeout=1, retries=5):
    socket.setdefaulttimeout(timeout)

    for _ in xrange(retries):
        for addr in interface_addresses():
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
            sock.bind((addr, 0))

            msg = DISCOVERY_MSG % dict(service='1', library=LIB_ID)
            #import pdb; pdb.set_trace()
            for _ in xrange(2):
                # sending it more than once will
                # decrease the probability of a timeout
                sock.sendto(msg, (MCAST_GRP, MCAST_PORT))

            try:
                data = sock.recv(1024)
            except socket.timeout:
                pass
            else:
                response = Response(data)
                print response.getheader('Location')
                import pdb; pdb.set_trace()
                return


def server(timeout=30):

    socket.setdefaulttimeout(timeout)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 30)
    sock.bind(('', MCAST_PORT))

    mreq = struct.pack('4sl', socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    cond = gobject.IO_IN | gobject.IO_HUP
    gobject.io_add_watch(sock, cond, handle_requests)

    gtk.main()


def handle_requests(sock, _):
    data, addr = sock.recvfrom(4096)
    request = Request(data)
    if 'ST' in request.headers:
        print request.headers['ST']

    if not request.error_code and \
            request.command == 'M-SEARCH' and \
            request.path == '*' and \
            request.headers['ST'].startswith(LIB_ID) and \
            request.headers['MAN'] == '"ssdp:discover"':

        print request.headers.keys()
        service = request.headers['ST'].split(':')[-1]
        if service in SERVICE_LOCS:
            loc = SERVICE_LOCS[service]
            msg = LOCATION_MSG % dict(service=service, loc=loc, library=LIB_ID)
            print msg, addr
            sock.sendto(msg, addr)

    return True


if __name__ == '__main__':
    if len(sys.argv) > 1 and 'client' in sys.argv[1]:
        client()
    else:
        server()
