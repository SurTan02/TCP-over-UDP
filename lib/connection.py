from socket import socket as Socket, AF_INET, SOCK_DGRAM
from .segment import Segment, SegmentHeader
from typing import Tuple, List, TypedDict
from io import BufferedReader, BufferedWriter


# State for connection
class Connection(TypedDict):
    addr: Tuple[str, int]
    seq_num: int
    ack_num: int
    payloads: bytes
    # State is ENUM (LISTEN, SYN_RCVD, SYN_SENT, ESTABLISHED, RCV_META, RCV_FILE, SND_META, SND_FILE, FIN_WAIT_1, FIN_WAIT_2, CLOSE_WAIT, LAST_ACK)
    state: str
    curFile: BufferedWriter | BufferedReader
    curFileSize: int  # in bytes


class SocketConnection:
    socket: Socket

    def __init__(self, ip: str, port: int):
        self.socket = Socket(AF_INET, SOCK_DGRAM)
        self.socket.settimeout(6)
        self.socket.bind((ip, port))

    def send(self, msg: Segment, dest: Tuple[str, int]):
        self.socket.sendto(msg.bytes, dest)

    def listen(self) -> Tuple[Segment, Tuple[str, int]]:
        data, addr = self.socket.recvfrom(32768)
        return Segment(data), addr

    def close_socket(self):
        self.socket.close()
