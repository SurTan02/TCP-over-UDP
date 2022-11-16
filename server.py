import sys
import math
from typing import Dict, List, Tuple
from lib.connection import Connection, SocketConnection
from lib.segment import Segment, SegmentFlag, SegmentHeader
from threading import Thread
import threading

WINDOW_SIZE = 4


class Server:
    socket: SocketConnection
    connections: Dict[Tuple[str, int], Connection]
    threads: Dict[Tuple[str, int], Thread]
    queue: List[Tuple[Tuple[str, int], Segment]]
    distributor: Thread
    queue_lock = threading.Lock()
    connection_lock = threading.Lock()

    def __init__(self, ip: str, port: int):
        self.socket = SocketConnection(ip, port)
        self.connections = {}
        self.threads = {}
        self.queue = []
        self.distributor = None

    def listen(self):
        try:
            seg, addr = self.socket.listen()

            is_valid = seg.valid_checksum()
            if is_valid:
                # Add to queue
                self.queue_lock.acquire()
                self.queue.append((addr, seg))
                self.queue_lock.release()
                # Distribute
                if (self.distributor is None) or (not self.distributor.is_alive()):
                    self.distributor = Thread(target=self._distribute)
                    self.distributor.start()
            else:  # Gatau mo ngapain ini, seharusnya buang aja
                print("Invalid checksum from", addr)
        except Exception as e:
            # Handle Timeout
            for conn in self.connections.values():
                if self.threads[conn['addr']] is None or not self.threads[conn['addr']].is_alive():
                    # If time out after sending syn_ack, resend syn_ack
                    if conn['state'] == "SYN_RCVD":
                        self.threads[conn['addr']] = Thread(target=self.socket.send(
                            Segment.SYN_ACK(), conn['addr']))
                        self.threads[conn['addr']].start()
                    # If time out after sending metadata, resend metadata
                    elif conn['state'] == "SND_META":
                        self.threads[conn['addr']] = Thread(target=self.socket.send(
                            Segment(
                                header=SegmentHeader(
                                    flag=SegmentFlag(0b0010),
                                    seq_num=conn['seq_num'],
                                    ack_num=conn['ack_num'],
                                    checksum=None),
                                payload=f"{conn['curFileName']}:{conn['curFileSize']}".encode(
                                )
                            ), conn['addr']))
                        self.threads[conn['addr']].start()
                    elif conn['state'] == "SND_FILE":
                        self.threads[conn['addr']] = Thread(target=self._send_window(
                            conn['addr'], conn['ack_num']))
                        self.threads[conn['addr']].start()
                    elif conn['state'] == "FIN_WAIT_1":
                        self.threads[conn['addr']] = Thread(target=self.socket.send(
                            Segment.FIN(), conn['addr']))
                        self.threads[conn['addr']].start()
                    elif conn['state'] == "FIN_WAIT_2":
                        self.threads[conn['addr']] = Thread(target=self.socket.send(
                            Segment.FIN_ACK(), conn['addr']))
                        self.threads[conn['addr']].start()
            print(f"[!] Error: {e}")
            print("Current thread count:", threading.active_count())

    def _distribute(self):
        while len(self.queue) > 0:
            self.queue_lock.acquire()
            addr, seg = self.queue.pop(0)
            self.queue_lock.release()
            if addr not in self.threads.keys() or self.threads[addr] is None:
                # If the thread doesn't exist, create it
                self.threads[addr] = Thread(
                    target=self._handle_connection, args=(seg, addr))
                self.threads[addr].start()
            else:
                # If the thread exists, wait for it to finish, then create a new one

                # If old sequence is in the queue, ignore it
                if (seg.flag == "DEFAULT" and seg.header['seq_num'] < self.connections[addr]['ack_num']):
                    continue
                self.threads[addr].join()
                self.threads[addr] = Thread(
                    target=self._handle_connection, args=(seg, addr))
                self.threads[addr].start()

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
            }

        header = seg.header

        # Connection State
        state = self.connections[addr]['state']

        self.connection_lock.acquire()

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
            if header['flag'] == "ACK":
                # If it's the correct segment
                # Only accept the first ack in the window (Sb is self.connections[addr]['ack_num'])
                if header['seq_num'] == self.connections[addr]['ack_num']:
                    # TODO: Improve this to handle store acks in buffer before sliding the window
                    print(
                        f"[!] {addr} RCV ACK {header['seq_num']} | REQ {header['ack_num']}")
                    # Preparing to send the next sequence
                    # Update seq_num and ack_num
                    self.connections[addr]['seq_num'] = header['ack_num']
                    self.connections[addr]['ack_num'] = header['seq_num'] + 1

                    segmentCount = math.ceil(
                        self.connections[addr]['curFileSize'] / Segment.SEGMENT_PAYLOAD)
                    # Sliding Window First Sequence
                    Sb = self.connections[addr]['ack_num']
                    # Sliding Window Last Sequencee
                    Sm = min(Sb + WINDOW_SIZE, segmentCount)
                    if (header['ack_num']) <= Sm:
                        print("[!] Sending sequence",
                              header['ack_num'] + WINDOW_SIZE - 1)
                        self._send_seq(
                            addr, header['ack_num'] + WINDOW_SIZE - 1)
                else:
                    print(
                        f"[!] ACK number {header['seq_num']} is not matched with Sb ({self.connections[addr]['ack_num']})")
                    self._send_window(addr, self.connections[addr]['ack_num'])

                 # If that is the last ack
                if self.connections[addr]['ack_num'] >= math.ceil(self.connections[addr]['curFileSize'] / Segment.SEGMENT_PAYLOAD) + 1:
                    print(f"[!] Successfully sent file to {addr[0]}:{addr[1]}")
                    self.socket.send(Segment.FIN(), addr)
                    self.connections[addr]['state'] = "FIN_WAIT_1"
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

        self.connection_lock.release()

    def _send_seq(self, addr: Tuple[str, int], Sn: int):
        # Seek file to the correct position
        self.connections[addr]['curFile'].seek(
            (Sn - 1) * Segment.SEGMENT_PAYLOAD)
        # Create Segment
        seq = Segment(
            header=SegmentHeader(
                seq_num=Sn,
                ack_num=Sn,
                flag=SegmentFlag(0b0000),
                checksum=None
            ),
            payload=self.connections[addr]['curFile'].read(Segment.SEGMENT_PAYLOAD))
        # Send Segment
        self.socket.send(seq, addr)

    def _send_window(self, addr: Tuple[str, int], Sb: int = 1):
        # Get Sm fron the window
        if Sb + WINDOW_SIZE > math.ceil(self.connections[addr]['curFileSize'] / Segment.SEGMENT_PAYLOAD):
            Sm = math.ceil(
                self.connections[addr]['curFileSize'] / Segment.SEGMENT_PAYLOAD)
        else:
            Sm = Sb + WINDOW_SIZE - 1

        # Loop from Sb to Sm
        for i in range(Sm - Sb + 1):
            # Seek file to the correct position
            self.connections[addr]['curFile'].seek(
                Segment.SEGMENT_PAYLOAD * (Sb - 1 + i), 0)
            # Create Segment
            seg = Segment(
                header=SegmentHeader(
                    seq_num=Sb + i,
                    ack_num=Sb + i,
                    flag=SegmentFlag(0b0000),
                    checksum=None
                ),
                payload=self.connections[addr]['curFile'].read(Segment.SEGMENT_PAYLOAD))
            # Send Segment
            print(f"Sending Window | Sequence = {Sb + i}")
            self.socket.send(seg, addr)

    # To initiate file transfer, send metadata first
    def file_transfer(self, addr, path):
        if self.connections[addr]['state'] != "ESTABLISHED":
            return
        self.connections[addr]['curFileName'] = path.split("/")[-1]
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
            payload=f"{self.connections[addr]['curFileName']}:{self.connections[addr]['curFileSize']}".encode(
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
            count = 0
            for conn in server.connections.keys():
                if server.connections[conn]['state'] == "ESTABLISHED":
                    count += 1

            if count == 1:
                for conn in server.connections.keys():
                    if server.connections[conn]['state'] == "ESTABLISHED":
                        print(f"[!] Sending file to {conn[0]}:{conn[1]}")
                        server.file_transfer(conn, path)
