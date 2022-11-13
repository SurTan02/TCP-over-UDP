from lib.connection import Connection, SocketConnection
from lib.segment import Segment, SegmentFlag, SegmentHeader

ip = input("IP: ")
port = int(input("Port: "))
socket = SocketConnection(ip, port)
dest_ip = input("Destination IP: ")
dest_port = int(input("Destination Port: "))

while True:
    seg_type = input("Type: ")
    if seg_type == "SYN":
        socket.send(Segment.SYN(), (dest_ip, dest_port))
    elif seg_type == "SYN-ACK":
        socket.send(Segment.SYN_ACK(), (dest_ip, dest_port))
    elif seg_type == "ACK":
        seq_num = int(input("Seq Num: "))
        ack_num = int(input("Ack Num: "))
        socket.send(Segment.ACK(seq_num, ack_num), (dest_ip, dest_port))
    elif seg_type == "FIN":
        socket.send(Segment.FIN(), (dest_ip, dest_port))
    elif seg_type == "FIN-ACK":
        socket.send(Segment.FIN_ACK(), (dest_ip, dest_port))
    elif seg_type == "META":
        socket.send(Segment.META(), (dest_ip, dest_port))
    elif seg_type == "DEFAULT":
        seq_num = int(input("Seq num: "))
        ack_num = int(input("Ack num: "))
        socket.send(Segment.DEFAULT(seq_num, ack_num), (dest_ip, dest_port))
