import asyncio
import threading
import socket

import websockets

from ..beat_handler_process import BeatHandlerProcess


class WebSocketServer(threading.Thread):

    def __init__(self, host="localhost", port=8765):
        threading.Thread.__init__(self, daemon=True)
        self.host = host
        self.port = port
        self.connections = {}
    
    def broadcast(self, bytes_message):
        for websocket in list(self.connections.values()):
            try:
                async def aux():
                    await websocket.send(bytes_message)
                asyncio.run(aux())
            except Exception as err:
                print(err, flush=True)

    def run(self):
        async def ws_handler(websocket, *args):
            self.connections[websocket.id] = websocket
            print("WebSocket client connected:", websocket.id)
            async for _ in websocket:
                pass
            print("WebSocket client disconnected:", websocket.id)
            del self.connections[websocket.id]
        async def start_server():
            print(f"WebSocket server listening at ws://{ self.host }:{ self.port }")
            async with websockets.serve(ws_handler, self.host, self.port):
                await asyncio.Future()
        asyncio.run(start_server())


class RawSocketServer(threading.Thread):

    def __init__(self, host, port):
        threading.Thread.__init__(self, daemon=True)
        self.host = host
        self.port = port
        self.s = None
        self.messages = []
        self.clients = []
        self.running = True

    def broadcast(self, bytes_message):
        for i, client in enumerate(self.clients):
            try:
                client.send(bytes_message)
            except (ConnectionAbortedError, ConnectionRefusedError, ConnectionResetError):
                print("Socket client disconnected")
                self.clients.pop(i)

    def run(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.bind((self.host, self.port))
        self.s.listen(5)
        print(f"Socket server listening at ws://{ self.host }:{ self.port }")
        while self.running:
            (clientsocket, address) = self.s.accept()
            print("New client:", address)
            self.clients.append(clientsocket)
        self.s.close()


class Socket(BeatHandlerProcess):

    NAME = "socket"

    def __init__(self, pipe, host="localhost", port=8765, web=False,
                 mute_beats=False, mute_onsets=False, mute_bpm=False):
        BeatHandlerProcess.__init__(self, pipe)
        self.server = None
        self.host = host
        self.port = port
        self.web = web
        self.mute_beats = mute_beats
        self.mute_onsets = mute_onsets
        self.mute_bpm = mute_bpm
    
    @staticmethod
    def add_arguments(parser):
        parser.add_argument("--web", action="store_true", help="Use WebSockets protocol")
        parser.add_argument("--host", type=str, default="localhost", help="Server host")
        parser.add_argument("--port", type=int, default=8765, help="Server port")
        parser.add_argument("--mute-beats", action="store_true", help="Do not handle beats")
        parser.add_argument("--mute-onsets", action="store_true", help="Do not handle onsets")
        parser.add_argument("--mute-bpm", action="store_true", help="Do not handle BPM")
    
    @classmethod
    def from_args(cls, pipe, args):
        return cls.from_keys(
            pipe, args, [],
            ["host", "port", "web", "mute_beats", "mute_onsets", "mute_bpm"])
    
    def handle_beat(self):
        if self.server is None or self.mute_beats:
            return
        self.server.broadcast(b"\x00\x00")
    
    def handle_onset(self):
        if self.server is None or self.mute_onsets:
            return
        self.server.broadcast(b"\x00\x01")
    
    def handle_bpm(self, bpm):
        if self.server is None or self.mute_bpm:
            return
        self.server.broadcast(round(bpm).to_bytes(2, "big"))

    def setup(self):
        if self.web:
            self.server = WebSocketServer(self.host, self.port)
        else:
            self.server = RawSocketServer(self.host, self.port)
        self.server.start()
