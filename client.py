from lib.connection import SocketConnection, Connection
from lib.segment import Segment, SegmentHeader, SegmentFlag
from typing import Tuple, List, Dict
import socket

class Client:
    socket: SocketConnection
    addr: Tuple[str, int]
    connection: Connection

    def __init__(self, ip: str, port: int, path : str):
        self.socket = SocketConnection(ip, port)
        self.connection = None
        self.addr = None
        self.path = path

    def listen(self):
        seg, addr = self.socket.listen()
        is_valid = seg.valid_checksum()
        
        if is_valid:
            self._handle_connection(seg, addr)
        else:  # Gatau mo ngapain ini, seharusnya buang aja
            print("Invalid checksum from", addr)

    def _send_ack(self, ack_num : int, seq_num : int = 0):
        if ack_num >= 0:

            ack_resp = Segment(
                header={
                "seq_num": seq_num,
                "ack_num": ack_num,
                "flag": SegmentFlag.get_flag("ACK"),
                "checksum": None
            },
                payload=b""
            )
            self.socket.send(ack_resp, self.addr)

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
                self.socket.send(Segment.SYN_ACK(), addr)
                self.connection['state'] = "SYN_SENT"

        elif state == "SYN_RCVD":
            if header['flag'] == "ACK":
                self.connection['headers'].append(header)
                self.connection['state'] = "ESTABLISHED"
                print("SocketConnection established with", addr)

        elif state == "SYN_SENT":
            if header['flag'] == "SYN-ACK":
                self.connection['headers'].append(header)
                self.socket.send(Segment.ACK(), addr)
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

    def listen_file_transfer(self):
        print(f"[!] Receiving file content...")

        fileBuffer = dict()
        Rn = 0
        while True:
            try:
                seg, addr = self.socket.listen()
                is_valid = seg.valid_checksum()

                if is_valid and addr == self.addr:
                    Sn = seg.get_header()["seq_num"]
                    if Rn == Sn:
                        print(f"[!] Sn={Rn} Received, sending ACK {Rn}")

                        fileBuffer[Rn] = seg.get_payload()

                        # Send acknowledgement for last received segment
                        self._send_ack(Rn)
                        Rn += 1

                    # End of file
                    elif seg.get_flag() == "FIN":
                        print(f"[!] Successfully received file")
                        
                        
                        fileBuffer[Rn-1] = fileBuffer[Rn-1].rstrip(b'\x00')
                        with open(self.path, 'wb+') as file:
                            for key in fileBuffer.keys():
                                file.write(fileBuffer[key])

                        # Send acknowledgement for last received segment
                        self.socket.send(seg.FIN_ACK(), self.addr)
                        break
                    else:
                        # Refuse segment
                        print(f"[!] Sn not equal with Rn ({Sn} =/= {Rn}), ignoring...")
                else:
                    print(f'[!] Checksum failed')
            except socket.timeout:
                print(f"[!] timeout, resending ACK {Rn-1}...")
                self._send_ack(Rn)

if __name__ == '__main__':
    main = Client("127.0.0.1", 7001, "./dump/terima.pdf")
    # main = Client("127.0.0.1", 7001, "./dump/terima.mp3")
    # main = Client("127.0.0.1", 7001, "./dump/ata.png")
    # main = Client("127.0.0.1", 7001, "./dump/tes.txt")
    main.connect("127.0.0.1", 7000)

    main.listen()

    main.listen_file_transfer()
    # print(main.connection)
