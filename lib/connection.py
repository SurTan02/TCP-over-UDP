from socket import socket as Socket, AF_INET, SOCK_DGRAM
from .segment import Segment, SegmentHeader
from typing import Tuple, List, TypedDict, Union
from io import BufferedReader, BufferedWriter
from threading import Lock
import time


# State for connection
class Connection(TypedDict):
    addr: Tuple[str, int]
    seq_num: int
    ack_num: int
    payloads: bytes
    # State is ENUM (LISTEN, SYN_RCVD, SYN_SENT, ESTABLISHED, RCV_META, RCV_FILE, SND_META, SND_FILE, FIN_WAIT_1, FIN_WAIT_2, CLOSE_WAIT, LAST_ACK)
    state: str
    curFile: Union[BufferedReader, BufferedWriter, None]
    curFileName: str
    curFileSize: int  # in bytes


class SocketConnection:
    socket: Socket
    _lock: Lock = Lock()

    def __init__(self, ip: str, port: int):
        self.socket = Socket(AF_INET, SOCK_DGRAM)
        self.socket.settimeout(2)
        self.socket.bind((ip, port))

    def send(self, msg: Segment, dest: Tuple[str, int]):
        self._lock.acquire()
        print(">", dest, msg)
        self.socket.sendto(msg.bytes, dest)
        self._lock.release()
        time.sleep(0.05)

    def listen(self) -> Tuple[Segment, Tuple[str, int]]:
        data, addr = self.socket.recvfrom(32768)
        print("<", addr, Segment(data))
        return Segment(data), addr

    def close_socket(self):
        self.socket.close()
