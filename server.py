from lib.segment import Segment, SegmentHeader
from lib.connection import SocketConnection, Connection
from typing import Tuple, List, Dict


class Server:
    socket: SocketConnection
    connections: Dict[Tuple[str, int], Connection]

    def __init__(self, ip: str, port: int):
        self.socket = SocketConnection(ip, port)
        self.connections = {}

    def listen(self):
        seg, addr = self.socket.listen()
        is_valid = seg.valid_checksum()
        if is_valid:
            self._handle_connection(seg, addr)
        else:  # Gatau mo ngapain ini, seharusnya buang aja
            print("Invalid checksum from", addr)

    def _handle_connection(self, seg: Segment, addr: Tuple[str, int]):
        if addr not in self.connections.keys():
            self.connections[addr] = {
                'addr': addr,
                'headers': [],
                'payloads': b"",
                'state': "LISTEN"
            }

        header = seg.header

        # Connection State
        state = self.connections[addr]['state']
        if state == "LISTEN":
            if header['flag'] == "SYN":
                self.connections[addr]['headers'].append(header)
                self.socket.send(Segment.SYN_ACK(), addr)
                self.connections[addr]['state'] = "SYN_RCVD"
        elif state == "SYN_RCVD":
            if header['flag'] == "ACK":
                self.connections[addr]['headers'].append(header)
                self.connections[addr]['state'] = "ESTABLISHED"
                print("SocketConnection established with", addr)
        elif state == "SYN_SENT":
            if header['flag'] == "SYN-ACK":
                self.connections[addr]['headers'].append(header)
                self.socket.send(Segment.ACK(), addr)
                self.connections[addr]['state'] = "ESTABLISHED"
                print("SocketConnection established with", addr)

        # Tinggal tambahin case aja berdasarkan state sama flag


if __name__ == '__main__':
    server = Server("127.0.0.1", 7000)
    while True:
        server.listen()
        print(server.connections)
