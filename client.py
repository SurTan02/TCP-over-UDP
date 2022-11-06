from lib.connection import Connection
from lib.segment import Segment, SegmentHeader
from typing import Tuple, List, Dict


class Client:
    connection: Connection
    addr: Tuple[str, int]
    headers: List[SegmentHeader]
    payloads: bytes

    def __init__(self, ip: str, port: int):
        self.connection = Connection(ip, port)
        self.headers = []
        self.addr = None

    def listen(self):
        seg, addr = self.connection.listen()
        is_valid = seg.valid_checksum()

        if is_valid:
            self._handle_connection(seg, addr)
        else:  # Gatau mo ngapain ini, seharusnya buang aja
            print("Invalid checksum from", addr)

    def _handle_connection(self, seg: Segment, addr: Tuple[str, int]):
        if self.addr is None or addr != self.addr:
            self.addr = addr
            self.headers = []
            self.payloads = b""

        header = seg.header

        # Handle Three Way Handshake
        # If client connections is empty, check if it's a SYN packet
        if len(self.headers) == 0:
            if header['flag'] == "SYN":
                self.headers.append(header)
                self.connection.send(Segment.SYN_ACK(), addr)

            if header['flag'] == "SYN-ACK":
                self.headers.append(header)
                self.connection.send(Segment.ACK(), addr)
                print("Connection established with", addr)

        # If client connections has 1 packet, check if it's a ACK packet
        elif len(self.headers) == 1:
            if header['flag'] == "ACK":
                self.headers.append(header)
                print("Connection established with", addr)

    def _is_connected(self, ip: str, port: int) -> bool:
        if self.addr or len(self.headers) < 2:
            return False

        # Check if three way handshake is done
        return (self.headers[0]['flag'] == "SYN" and self.headers[(ip, port)[1]['flag'] == "ACK"]) or \
            self.headers[0]['flag'] == "SYN-ACK"

    def connect(self, ip: str, port: int):
        self.connection.send(Segment.SYN(), (ip, port))
        self.listen()


if __name__ == '__main__':
    main = Client("127.0.0.1", 7001)
    main.connect("127.0.0.1", 7000)
    print(main.headers)
