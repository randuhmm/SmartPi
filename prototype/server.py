import BaseHTTPServer
import SimpleHTTPServer
import SocketServer
import socket
import gobject
import struct
import sys
from StringIO import StringIO
from threading import Thread
from multiprocessing import Process
import RPi.GPIO as GPIO

LIB_ID = 'urn:Randuhmm:device:hub:1'
UUID = '2fac1234-31f8-11b4-a222-08002b34c003'
USN = 'uuid:{UUID}::{LIB_ID}'.format(UUID=UUID, LIB_ID=LIB_ID)
MCAST_GRP = '239.255.255.250'
MCAST_PORT = 1900
SERVICE_PORT = 8080
SERVICE_IP = '172.28.16.35'

DISCOVERY_MSG = ('M-SEARCH * HTTP/1.1\r\n' +
                 'ST: %(library)s\r\n' +
                 'MX: 2\r\n' +
                 'MAN: "ssdp:discover"\r\n' +
                 'HOST: 239.255.255.250:1900\r\n\r\n')

LOCATION_MSG = ('HTTP/1.1 200 OK\r\n' +
                'CACHE-CONTROL: max-age=100\r\n' +
                'EXT:\r\n' +
                'LOCATION: http://{IP}:{PORT}/device.json\r\n' +
                'SERVER: Linux/1.0 UPnP/1.0 Randuhmm/0.1\r\n' +
                'ST: %(library)s\r\n' +
                'USN: {USN}\r\n').format(USN=USN,
                                         IP=SERVICE_IP,
                                         PORT=SERVICE_PORT)

DEVICE = {
    'device': {
        'deviceName': 'My RanduhmmPi',
        'deviceType': 'urn:Randuhmm:device:hub:1',
        'modelDescription': 'Randuhmm Pi IoT Hub Device',
        'modelName': 'RanduhmmPi',
        'serialNum': '',
        'UDN': 'uuid:2fac1234-31f8-11b4-a222-08002b34c003',
        'children': [
            {
                'name': 'Contact 01',
                'id': 'GPIO13',
                'type': 'RanduhmmContact'
            },
            {
                'name': 'Contact 02',
                'id': 'GPIO14',
                'type': 'RanduhmmContact'
            },
            {
                'name': 'Contact 03',
                'id': 'GPIO15',
                'type': 'RanduhmmContact'
            },
            {
                'name': 'Switch 01',
                'id': 'GPIO17',
                'type': 'RanduhmmSwitch'
            }
        ]
    }
}


class Request(BaseHTTPServer.BaseHTTPRequestHandler):

    def __init__(self, request_text):
        self.rfile = StringIO(request_text)
        self.raw_requestline = self.rfile.readline()
        self.error_code = self.error_message = None
        self.parse_request()

    def send_error(self, code, message):
        self.error_code = code
        self.error_message = message


def ssdp_server(timeout=30):

    socket.setdefaulttimeout(timeout)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 30)
    sock.bind(('', MCAST_PORT))

    mreq = struct.pack('4sl', socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    cond = gobject.IO_IN | gobject.IO_HUP
    gobject.io_add_watch(sock, cond, handle_ssdp_requests)

    mainloop = gobject.MainLoop()
    mainloop.run()


def handle_ssdp_requests(sock, _):
    data, addr = sock.recvfrom(4096)
    request = Request(data)
    if 'ST' in request.headers:
        print request.headers['ST']
    if not request.error_code and \
            request.command == 'M-SEARCH' and \
            request.path == '*' and \
            request.headers['ST'].startswith(LIB_ID) and \
            request.headers['MAN'] == '"ssdp:discover"':
        service = request.headers['ST'].split(':')[-1]

        msg = LOCATION_MSG % dict(service=service, library=LIB_ID)
        print msg, addr
        sock.sendto(msg, addr)
    return True


class RanduhmmHttpHandler(BaseHTTPServer.BaseHTTPRequestHandler):

    def do_SUBSCRIBE(self):
        import pdb; pdb.set_trace()

    def do_GET(self):
        import pdb; pdb.set_trace()


class RanduhmmHttpHandler2(SimpleHTTPServer.SimpleHTTPRequestHandler):

    def do_POST(self):
        # import pdb; pdb.set_trace()
        result = 'false'
        if self.path[:3] == '/on':
            GPIO.output(13, True)
            result = '{"switch": "on"}'
        elif self.path[:4] == '/off':
            GPIO.output(13, False)
            result = '{"switch": "off"}'
        self.send_response(200)
        self.send_header('Device-Id', 'GPIO17')
        self.end_headers()
        self.wfile.write(result)
        self.wfile.close()

    def do_SUBSCRIBE(self):
        print 'SUBSCRIBE CALLED!!'
        import pdb; pdb.set_trace()
        self.send_response(200)
        self.send_header('SID', 'uuid:1234')
        self.end_headers()
        self.wfile.close()

RanduhmmHttpHandler2.extensions_map['.json'] = 'application/json'


def main():

    ssdp_process = Process(target=ssdp_server)
    ssdp_process.daemon = True
    ssdp_process.start()

    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(13, GPIO.OUT)

    httpd = SocketServer.ThreadingTCPServer(('', SERVICE_PORT),
                                            RanduhmmHttpHandler2)

    try:
        httpd.serve_forever()
        # httpd_thread = Thread(target=httpd.serve_forever)
        # httpd_thread.setDaemon(True)
        # httpd_thread.start()
        # httpd_thread.join()
    except KeyboardInterrupt:
        print "Exiting"
        ssdp_process.terminate()
        GPIO.cleanup()

if __name__ == '__main__':
    main()
