import sys
import math
from typing import Dict, List, Tuple
from lib.connection import Connection, SocketConnection
from lib.segment import Segment, SegmentFlag, SegmentHeader

WINDOW_SIZE = 4


class Server:
    socket: SocketConnection
    connections: Dict[Tuple[str, int], Connection]

    def __init__(self, ip: str, port: int):
        self.socket = SocketConnection(ip, port)
        self.connections = {}

    def listen(self):
        try:
            seg, addr = self.socket.listen()

            is_valid = seg.valid_checksum()
            if is_valid:
                self._handle_connection(seg, addr)
            else:  # Gatau mo ngapain ini, seharusnya buang aja
                print("Invalid checksum from", addr)
        except Exception as e:
            # Handle Timeout
            for conn in self.connections.values():
                if conn['state'] == "SND_FILE":
                    self._send_window(conn['addr'], conn['ack_num'])
            print(f"[!] Error: {e}")

    def _handle_connection(self, seg: Segment, addr: Tuple[str, int]):
        if addr not in self.connections.keys():
            self.connections[addr] = {
                'addr': addr,
                'seq_num': 0,
                'ack_num': 0,
                'payloads': b"",
                'state': "LISTEN",
                'curFile': None,
                'curFileSize': 0,
                'buf': [],
            }

        header = seg.header

        # Connection State
        state = self.connections[addr]['state']

        # Three Way Handshake, after this seq_num and ack_num will be equal to 1
        if state == "LISTEN":
            if header['flag'] == "SYN":
                self.socket.send(Segment.SYN_ACK(), addr)
                self.connections[addr]['state'] = "SYN_RCVD"
        elif state == "SYN_RCVD":
            if header['flag'] == "ACK":
                self.connections[addr]['state'] = "ESTABLISHED"
                self.connections[addr]['seq_num'] = 1
                self.connections[addr]['ack_num'] = 1
                print("SocketConnection established with", addr)
        elif state == "SYN_SENT":
            if header['flag'] == "SYN-ACK":
                self.socket.send(Segment.ACK(), addr)
                self.connections[addr]['state'] = "ESTABLISHED"
                self.connections[addr]['seq_num'] = 1
                self.connections[addr]['ack_num'] = 1
                print("SocketConnection established with", addr)

        # Metadata Format: <filename>:<filesize> less than 32 MB
        # Send Metadata File
        elif state == "SND_META":
            if header['flag'] == "ACK":
                self.connections[addr]['seq_num'] = seg.get_header()['ack_num']
                self.connections[addr]['ack_num'] = seg.get_header()[
                    'seq_num']
                self.connections[addr]['state'] = "SND_FILE"

                # Send first window
                self._send_window(addr, 1)

        # Send File with Go-Back-N ARQ
        elif state == "SND_FILE":
            
            segmentCount = math.ceil(self.connections[addr]['curFileSize'] / Segment.SEGMENT_PAYLOAD)
            Sb = self.connections[addr]['ack_num'] + WINDOW_SIZE
            Sm = min(Sb + WINDOW_SIZE, segmentCount)          # Sequence Max / Sliding Window

                    
            if header['flag'] == "ACK":
                # If it's the correct segment
                # Rn = seg.get_header()['seq_num']
                # print(f"Rn = {Rn} | ACK_sesg = {self.connections[addr]['ack_num']} | Sn Client = {self.connections[addr]['seq_num']}")
                if (self.connections[addr]['ack_num']) >= seg.get_header()['seq_num']:
                    # Slide window

                    # # Increase seq number by 1
                    # self.connections[addr]['seq_num'] = header['ack_num']

                    # Increase ack number by 1
                    self.connections[addr]['ack_num'] += 1
                    self._send_seq(addr, self.connections[addr]['ack_num'])
                    print(f"[!] RCV ACK {self.connections[addr]['ack_num']- 1} | Sending segment {self.connections[addr]['ack_num']}")

                else:
                    print(f"[!] ACK number {(self.connections[addr]['ack_num'])} < Sb ({seg.get_header()['seq_num']})")
                    self._send_window(addr, self.connections[addr]['ack_num'])
                
                 # If that is the last ack
                if self.connections[addr]['ack_num'] >= math.ceil(self.connections[addr]['curFileSize'] / Segment.SEGMENT_PAYLOAD) + 1:
                    # Send FIN
                    print(f"[!] RCV LAST ACK {self.connections[addr]['ack_num']}")
                    print(f"[!] Successfully sent file to {addr[0]}:{addr[1]}")
                    self.socket.send(Segment.FIN(), addr)
                    self.connections[addr]['state'] = "FIN_WAIT_1"
                    self.connections[addr]['curFile'].close()
                # If it's not
                # else:
                    # resend the window
            else:
                print(f"[!] Checksum failed")           
        # Double Two Way Handshake
        elif state == "FIN_WAIT_1":
            if header['flag'] == "FIN-ACK":
                self.socket.send(Segment.FIN_ACK(), addr)
                self.connections[addr]['state'] = "FIN_WAIT_2"

        elif state == "FIN_WAIT_2":
            if header['flag'] == "ACK":
                self.socket.send(Segment.ACK(), addr)
                del self.connections[addr]
                print("SocketConnection closed with", addr)

    def _send_seq(self, addr: Tuple[str, int], seq_num: int):
        self.connections[addr]['curFile'].seek(
            (seq_num - 1) * Segment.SEGMENT_PAYLOAD)
        self.connections[addr]['curFile'].seek(
            (seq_num - 1) * Segment.SEGMENT_PAYLOAD)
        seq = Segment(
            header=SegmentHeader(
                seq_num=((seq_num-1)) + 1,
                ack_num=seq_num,
                flag=SegmentFlag(0b0000),
                checksum=None
            ),
            payload=self.connections[addr]['curFile'].read(Segment.SEGMENT_PAYLOAD))

        self.socket.send(seq, addr)

    def _send_window(self, addr: Tuple[str, int], start_seq: int = 1):
        if start_seq + WINDOW_SIZE > math.ceil(self.connections[addr]['curFileSize'] / Segment.SEGMENT_PAYLOAD):
            end_seq = math.ceil(
                self.connections[addr]['curFileSize'] / Segment.SEGMENT_PAYLOAD)
        else:
            end_seq = start_seq + WINDOW_SIZE - 1
        for i in range(end_seq - start_seq + 1):
            self.connections[addr]['curFile'].seek(
                Segment.SEGMENT_PAYLOAD * (start_seq - 1 + i), 0)
            self.connections[addr]['curFile'].seek(
                Segment.SEGMENT_PAYLOAD * (start_seq - 1 + i), 0)
            seg = Segment(
                header=SegmentHeader(
                    seq_num=((start_seq - 1 + i)) + 1,
                    ack_num=(start_seq + i),
                    flag=SegmentFlag(0b0000),
                    checksum=None
                ),
                payload=self.connections[addr]['curFile'].read(Segment.SEGMENT_PAYLOAD))
            print(f"Resend {start_seq + i}")
            self.socket.send(seg, addr)

    # To initiate file transfer, send metadata first
    def file_transfer(self, addr, path):
        if self.connections[addr]['state'] != "ESTABLISHED":
            return
        filename = path.split("/")[-1]
        self.connections[addr]['state'] = "SND_META"
        self.connections[addr]['curFile'] = open(path, "rb")
        with open(path, "rb") as f:
            f.seek(0, 2)
            self.connections[addr]['curFileSize'] = f.tell()

        # Send metadata
        self.socket.send(Segment(
            header=SegmentHeader(
                seq_num=1,
                ack_num=1,
                flag=SegmentFlag(0b0001),
                checksum=None
            ),
            payload=f"{filename}:{self.connections[addr]['curFileSize']}".encode(
            )
        ), addr)


if __name__ == '__main__':

    if len(sys.argv) != 3:
        print(f"Error: {len(sys.argv)} argumennts given, expected 3")
        print("server.py [broadcast port] [path file input]")
    else:
        broadcast = int(sys.argv[1])
        path = sys.argv[2]

        server = Server("127.0.0.1", broadcast)
        print(f"[!] Server started at 127.0.0.1:{broadcast}...")
        while True:
            # Listen
            server.listen()

            # File Transfer
            for conn in server.connections.keys():
                if server.connections[conn]['state'] == "ESTABLISHED":
                    print(f"[!] Sending file to {conn[0]}:{conn[1]}")
                    # server.file_transfer(conn, "files/ata.png")
                    server.file_transfer(conn, path)
                    # server.file_transfer(conn, "files/mbd.pdf")
