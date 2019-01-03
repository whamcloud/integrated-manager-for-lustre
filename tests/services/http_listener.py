from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
import threading


class HttpListener(threading.Thread):
    def __init__(self, port):
        super(HttpListener, self).__init__()

        self._server = HTTPServer(("127.0.0.1", port), HttpListenerHandler)
        self._server.listener = self
        self.requests = []

    def run(self):
        self._server.serve_forever()

    def log_request(self, handler):
        self.requests.append(handler)

    @property
    def last_request(self):
        return self.requests[-1]

    def shutdown(self):
        self._server.shutdown()
        self.join()
        self._server.socket.close()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()


class HttpListenerHandler(BaseHTTPRequestHandler):
    def accept_and_log(self):
        self.server.listener.log_request(self)
        self.send_response(200)
        self.end_headers()
        self.wfile.flush()

    def do_GET(self):
        self.accept_and_log()

    def do_POST(self):
        length = int(self.headers.getheader("content-length"))
        self.post_data = self.rfile.read(length)

        self.accept_and_log()
