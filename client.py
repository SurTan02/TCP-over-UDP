from lib.connection import SocketConnection, Connection
from lib.segment import Segment, SegmentHeader
from typing import Tuple, List, Dict


class Client:
    socket: SocketConnection
    addr: Tuple[str, int]
    connection: Connection

    def __init__(self, ip: str, port: int):
        self.socket = SocketConnection(ip, port)
        self.connection = None
        self.addr = None

    def listen(self):
        seg, addr = self.socket.listen()
        is_valid = seg.valid_checksum()

        if is_valid:
            self._handle_connection(seg, addr)
        else:  # Gatau mo ngapain ini, seharusnya buang aja
            print("Invalid checksum from", addr)

    def _handle_connection(self, seg: Segment, addr: Tuple[str, int]):
        if self.addr is None:
            self.addr = addr
            self.connection = {
                'addr': addr,
                'headers': [],
                'payloads': b"",
                'state': "LISTEN"
            }

        header = seg.header

        # Connection State
        state = self.connection['state']
        if state == "LISTEN":
            if header['flag'] == "SYN":
                self.connection['headers'].append(header)
                self.socket.send(Segment.ACK(), addr)
                self.connection['state'] = "SYN_SENT"
        elif state == "SYN_RCVD":
            if header['flag'] == "ACK":
                self.connection['headers'].append(header)
                self.connection['state'] = "ESTABLISHED"
                print("SocketConnection established with", addr)
        elif state == "SYN_SENT":
            if header['flag'] == "SYN-ACK":
                self.connection['headers'].append(header)
                self.connection['state'] = "ESTABLISHED"
                print("SocketConnection established with", addr)

        # Tinggal tambahin case aja berdasarkan state sama flag

    def connect(self, ip: str, port: int):
        self.socket.send(Segment.SYN(), (ip, port))
        self.addr = (ip, port)
        self.connection = {
            'addr': self.addr,
            'headers': [],
            'payloads': b"",
            'state': "SYN_SENT"
        }
        self.listen()


if __name__ == '__main__':
    main = Client("127.0.0.1", 7001)
    main.connect("127.0.0.1", 7000)
    print(main.connection)
