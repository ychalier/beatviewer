import http.server
import os
import socketserver
import threading
import time
import webbrowser

from .socket import Socket


class AsyncWebServer(threading.Thread):

    def __init__(self, port, document_root, base_url, delay, socket_uri):
        self.port = port
        self.document_root = os.path.realpath(document_root)
        self.base_url = base_url
        self.delay = delay
        self.socket_uri = socket_uri
        threading.Thread.__init__(self, daemon=True)
    
    def run(self):
        directory = self.document_root
        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=directory, **kwargs)
        time.sleep(self.delay)
        with socketserver.TCPServer(("", self.port), Handler) as httpd:
            url = f"http://localhost:{self.port}{self.base_url}?uri={self.socket_uri}"
            webbrowser.open(url, new=2)
            print(f"Web server is starting. Browser should open automatically. If not, you may access it here:\n\t{url}")
            httpd.serve_forever()


class WebHandler(Socket):

    NAME = None
    SOCKET_HOST = "localhost"
    SOCKET_PORT = 8765
    WEB_PORT = 8123
    DOCUMENT_ROOT = os.path.join(os.path.dirname(__file__), "..", "web")
    URL = "/"

    def __init__(
            self,
            pipe, 
            mute_beats=False, 
            mute_onsets=False, 
            mute_bpm=False):
        Socket.__init__(
            self,
            pipe,
            host=self.SOCKET_HOST,
            port=self.SOCKET_PORT,
            web=True,
            mute_beats=mute_beats,
            mute_onsets=mute_onsets,
            mute_bpm=mute_bpm)
        self.web_server = None
        
    @staticmethod
    def add_arguments(parser):
        parser.add_argument("--mute-beats", action="store_true", help="Do not handle beats")
        parser.add_argument("--mute-onsets", action="store_true", help="Do not handle onsets")
        parser.add_argument("--mute-bpm", action="store_true", help="Do not handle BPM")
    
    @classmethod
    def from_args(cls, pipe, args):
        return cls.from_keys(pipe, args, [], ["mute_beats", "mute_onsets", "mute_bpm"])
    
    def setup(self):
        self.web_server = AsyncWebServer(
            self.WEB_PORT,
            self.DOCUMENT_ROOT,
            self.URL,
            1,
            f"ws://{self.SOCKET_HOST}:{self.SOCKET_PORT}"
        )
        self.web_server.start()
        Socket.setup(self)


class Fireworks(WebHandler):

    NAME = "fireworks"
    URL = "/fireworks.html"


class Fluid(WebHandler):

    NAME = "fluid"
    URL = "/fluid.html"
