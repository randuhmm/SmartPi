import SimpleHTTPServer
import SocketServer

PORT = 8080


class MyHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):

    def do_SUBSCRIBE(self):
        import pdb; pdb.set_trace()

Handler = MyHandler
Handler.extensions_map['.json'] = 'application/json'

httpd = SocketServer.TCPServer(("", PORT), Handler)

print "serving at port", PORT
httpd.serve_forever()
