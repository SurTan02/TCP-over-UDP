from lib.segment import Segment, SegmentHeader
from lib.connection import Connection
from typing import Tuple, List, Dict


class Server:
    connection: Connection
    headers: Dict[Tuple[str, int], List[SegmentHeader]]
    payloads: Dict[Tuple[str, int], bytes]

    def __init__(self, ip: str, port: int):
        self.connection = Connection(ip, port)
        self.headers = {}
        self.payloads = {}

    def listen(self):
        seg, addr = self.connection.listen()
        is_valid = seg.valid_checksum()
        if is_valid:
            self._handle_connection(seg, addr)
        else:  # Gatau mo ngapain ini, seharusnya buang aja
            print("Invalid checksum from", addr)

    def _handle_connection(self, seg: Segment, addr: Tuple[str, int]):
        if addr not in self.headers or addr not in self.payloads:
            self.headers[addr] = []
            self.payloads[addr] = b""

        header = seg.header

        # Handle Three Way Handshake
        # If client connections is empty, check if it's a SYN packet
        if len(self.headers[addr]) == 0:
            if header['flag'] == "SYN":
                self.headers[addr].append(header)
                self.connection.send(Segment.SYN_ACK(), addr)

            if header['flag'] == "SYN-ACK":
                self.headers[addr].append(header)
                self.connection.send(Segment.ACK(), addr)
                print("Connection established with", addr)

        # If client connections has 1 packet, check if it's a ACK packet
        elif len(self.headers[addr]) == 1:
            if header['flag'] == "ACK":
                self.headers[addr].append(header)
                print("Connection established with", addr)

        # Handle FIN packet
        if header['flag'] == "FIN":
            self.headers[addr] = []
            self.payloads[addr] = b""
            return

        # TODO: Go Back N-ARQ

    def _is_connected(self, ip: str, port: int) -> bool:
        if not (ip, port) in self.headers or len(self.headers[(ip, port)]) < 2:
            return False

        # Check if three way handshake is done
        return (self.headers[(ip, port)][0]['flag'] == "SYN" and self.headers[(ip, port)[1]['flag'] == "ACK"]) or \
            self.headers[(ip, port)][0]['flag'] == "SYN-ACK"


if __name__ == '__main__':
    server = Server("127.0.0.1", 7000)
    while True:
        server.listen()
        print(server.headers)
