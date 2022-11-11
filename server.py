import math
import socket
from typing import Dict, List, Tuple

from lib.connection import Connection, SocketConnection
from lib.segment import Segment, SegmentFlag, SegmentHeader

SEGMENT_SIZE = 32756

class Server:
    socket: SocketConnection
    connections: Dict[Tuple[str, int], Connection]

    def __init__(self, ip: str, port: int, path : str):
        self.socket = SocketConnection(ip, port)
        self.connections = {}
        self.path = path
        
        with open(self.path, "rb") as srcFile:
            srcFile.seek(0, 2)
            self.filesize = srcFile.tell()  
        
        self.segmentCount = math.ceil(self.filesize / SEGMENT_SIZE)

    def listen(self):
        seg, addr = self.socket.listen()
        # print(seg, addr)

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

    def start_file_transfer(self):
        # Handshake & file transfer for all client
        pass



    # def file_transfer(self, client_addr : ("ip", "port")):
    def file_transfer(self):
        # File transfer, server-side, Send file to 1 client
        Sb = 0                                      # Seq_Base
        N = 4                                       # Ukuran Window
        Sm = min(Sb + N, self.segmentCount)         # Sequence Max / Sliding Window

        seg, addr = self.socket.listen()
        with open(self.path, 'rb') as srcFile:
            print(f"[!] Sending file content...")
            
            
            while Sb < self.segmentCount:
                try:
                    for i in range(Sm - Sb):
                        srcFile.seek(SEGMENT_SIZE * (Sb + i))    
                        data = Segment(header={
                            "seq_num" : Sb+i, 
                            "ack_num" : 0,
                            "flag" : SegmentFlag.get_flag("ACK"),
                            "checksum" : None
                            }, 
                            payload = srcFile.read(SEGMENT_SIZE),
                            )

                        self.socket.send(data, addr)
                        print(f"[!] Sending segment with Sn {Sb + i}")
                    
                    for i in range(Sm - Sb):
                        seg, addr = self.socket.listen()
                        isValid = seg.valid_checksum()

                        if isValid and seg.get_flag() == "ACK":
                            Rn = seg.get_header()["ack_num"]
                            if (Rn >= Sb):
                                Sb = Rn + 1
                                Sm = min(Sb + N, self.segmentCount) 
                                print(f"[!] Received ACK {Rn} | Sb = {Sb}")
                                
                            # If Rn < Sb, Resend Segment Rn
                            else:
                                print(f"[!] ACK number {Rn} < Sb ({Sb}) | Resending segment with Sn {Rn}")
                                Sb = Rn
                                break           

                        elif not isValid:
                            print(f"[!] Checksum failed")
                            break
                        else:
                            print(f"[!] Unknown error")
                            break
                except socket.timeout:
                    print(f"[!] timeout")
                    
        print(f"[!] Successfully sent file to {addr[0]}:{addr[1]}")
        self.socket.send(Segment.FIN(), addr)

if __name__ == '__main__':
    # server = Server("127.0.0.1", 7000, "./dump/404.png")
    server = Server("127.0.0.1", 7000, "./dump/soal.pdf")
    # server = Server("127.0.0.1", 7000, "./dump/SPIRIT.mp3")
    # server = Server("127.0.0.1", 7000, "./dump/bro.txt")
    print(f"[!] Server started at 127.0.0.1:7000...")
    while True:

        # Handshake
        server.listen()

        # File Transfer
        server.file_transfer()
        break
        # print(server.connections)
