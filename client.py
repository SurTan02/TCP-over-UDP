import sys
from lib.connection import SocketConnection, Connection
from lib.segment import Segment, SegmentHeader, SegmentFlag
from typing import Tuple, List, Dict

WINDOW_SIZE = 4


class Client:
    socket: SocketConnection
    addr: Tuple[str, int]
    connection: Connection
    folder: str

    def __init__(self, ip: str, port: int, folder: str):
        self.socket = SocketConnection(ip, port)
        self.connection = None
        self.addr = None
        self.folder = folder

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
            if (str(e) != 'timed out'):
                print(f"[!] Error: {e}")

    def _handle_connection(self, seg: Segment, addr: Tuple[str, int]):
        if self.addr is None:
            self.addr = addr
            self.connection = {
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
        state = self.connection['state']

        # Three way Handshake, after this seq_num and ack_num will be equal to 1
        if state == "LISTEN":
            if header['flag'] == "SYN":
                self.socket.send(Segment.SYN_ACK(), addr)
                self.connection['state'] = "SYN_SENT"

        elif state == "SYN_RCVD":
            if header['flag'] == "ACK":
                self.connection['state'] = "ESTABLISHED"
                self.connection['seq_num'] = 1
                self.connection['ack_num'] = 1
                print("SocketConnection established with", addr)

        elif state == "SYN_SENT":
            if header['flag'] == "SYN-ACK":
                self.socket.send(Segment.ACK(), addr)
                self.connection['state'] = "ESTABLISHED"
                self.connection['seq_num'] = 1
                self.connection['ack_num'] = 1
                print("SocketConnection established with", addr)

        # Metadata Format: <filename>:<filesize> less than 32 MB
        # Receive Metadata File
        elif state == "ESTABLISHED":
            if header['flag'] == "META":
                self.connection['state'] = "RCV_META"
                [filename, filesize] = seg.get_trimmed_payload().decode().split(":")
                self.connection['curFile'] = open(
                    self.folder+"/"+filename, 'wb')
                self.connection['curFileSize'] = int(filesize)
                self.socket.send(Segment.ACK(1, 1), addr)

        # Receive File Content
        elif state == "RCV_META":
            if header['flag'] == "DEFAULT":
                self.connection['state'] = "RCV_FILE"
                self.connection['payload'] = seg.get_payload()
                self.connection['seq_num'] = 1
                self.connection['ack_num'] = 2
                self.socket.send(Segment.ACK(
                    self.connection['seq_num'], self.connection['ack_num']), addr)

        elif state == "RCV_FILE":
            if header['flag'] == "DEFAULT":
                if (header['seq_num'] == self.connection['ack_num']):
                    # Append payload
                    self.connection['payload'] += seg.get_payload()

                    # Update seq_num and ack_num
                    self.connection['seq_num'] = header['ack_num']
                    self.connection['ack_num'] = header['seq_num'] + 1

                    # Send ACK
                    print(
                        f"Send ACK = {self.connection['seq_num']} | Request Seq = {self.connection['ack_num']}")
                    self.socket.send(Segment.ACK(
                        self.connection['seq_num'], self.connection['ack_num']), addr)
                # Resend ACK for sequence number that already received
                elif (header['seq_num'] < self.connection['ack_num']):
                    # Send ACK
                    print(
                        f"Send ACK = {header['seq_num']} | Request Seq = {self.connection['ack_num']}")
                    self.socket.send(Segment.ACK(
                        header['seq_num'], self.connection['ack_num']), addr)
                else:
                    print("Wrong seq_num, expected",
                          self.connection['ack_num'], "got", header['seq_num'])
                    return

            elif header['flag'] == "FIN":
                self.connection['state'] = "CLOSE_WAIT"
                # Write to file
                self.connection['curFile'].write(
                    self.connection['payload'].rstrip(b'\x00'))
                self.connection['curFile'].close()
                print(
                    f"[!] Successfully received file from {addr[0]}:{addr[1]}")
                self.socket.send(Segment.FIN_ACK(), addr)

        elif state == "CLOSE_WAIT":
            if header['flag'] == "FIN-ACK":
                self.connection['state'] = "LAST_ACK"
                self.socket.send(Segment.ACK(
                    self.connection['seq_num'], self.connection['ack_num']), addr)

        elif state == "LAST_ACK":
            if header['flag'] == "ACK":
                self.connection = None
                print("SocketConnection closed with", addr)

    def connect(self, ip: str, port: int):
        self.socket.send(Segment.SYN(), (ip, port))
        self.addr = (ip, port)

        self.connection = {
            'addr': self.addr,
            'seq_num': 0,
            'ack_num': 0,
            'payloads': b"",
            'state': "SYN_SENT",
            'curFile': None,
            'curFileSize': 0,
            'buf': [],
        }
        self.listen()


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print(f"Error: {len(sys.argv)} arguments given, expected 4")
        print("client.py [client port] [broadcast port] [path output]")
    else:

        client = int(sys.argv[1])
        broadcast = int(sys.argv[2])
        path = (sys.argv[3])

        main = Client("127.0.0.1", client, path)
        main.connect("127.0.0.1", broadcast)

        while True:
            try:
                main.listen()

            except Exception as e:
                if (str(e) != 'timed out'):
                    print(f"[!] Error: {e}")
                continue
