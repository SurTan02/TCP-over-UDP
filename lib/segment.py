from struct import pack, unpack
import struct
from typing import TypedDict

# Constants
SYN_FLAG = 0b1000
ACK_FLAG = 0b0100
SYN_ACK_FLAG = 0b1100
FIN_FLAG = 0b0010
FIN_ACK_FLAG = 0b0110
RST_FLAG = 0b0001
DEFAULT_FLAG = 0b0000

# Change this to set SEGMENT_SIZE, minimum is 12 (header only)
SEGMENT_SIZE = 32768
'''
Segment Header
seq_num: int
ack_num: int
flag: 1 byte
padding: 1 byte
checksum: 2 bytes

Segment Data (if SEGMENT_SIZE = 32MB)
payload: 32756 bytes
'''
HEADER_FORMAT = '>LLBxH'
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
PAYLOAD_FORMAT = f'>{SEGMENT_SIZE - HEADER_SIZE}s'

FULL_SEGMENT_FORMAT = f'>{SEGMENT_SIZE}s'


class SegmentFlag:
    def __init__(self, flag: bytes):
        self.flag = flag

    def get_flag_bytes(self) -> bytes:
        return self.flag

    def __str__(self):
        if self.flag == SYN_FLAG:
            return "SYN"
        elif self.flag == ACK_FLAG:
            return "ACK"
        elif self.flag == SYN_ACK_FLAG:
            return "SYN-ACK"
        elif self.flag == FIN_FLAG:
            return "FIN"
        elif self.flag == FIN_ACK_FLAG:
            return "FIN-ACK"
        elif self.flag == DEFAULT_FLAG:
            return "DEFAULT"
        else:
            return "UNKNOWN"

    def __eq__(self, other):
        if type(other) == SegmentFlag:
            return self.flag == other.flag
        elif type(other) == bytes:
            return self.flag == other
        elif type(other) == str:
            return self.flag == SegmentFlag.get_flag(other).flag
        else:
            return False

    @staticmethod
    def get_flag(flag: str):
        if flag == "SYN":
            return SegmentFlag(SYN_FLAG)
        elif flag == "ACK":
            return SegmentFlag(ACK_FLAG)
        elif flag == "SYN-ACK":
            return SegmentFlag(SYN_ACK_FLAG)
        elif flag == "FIN":
            return SegmentFlag(FIN_ACK_FLAG)
        elif flag == "FIN-ACK":
            return SegmentFlag(FIN_FLAG)
        elif flag == "DEFAULT":
            return SegmentFlag(DEFAULT_FLAG)
        else:
            raise Exception("Invalid flag")


class SegmentHeader(TypedDict):
    # Segment header
    seq_num: int
    ack_num: int
    flag: SegmentFlag
    checksum: bytes


class Segment:
    data: bytes = unpack(FULL_SEGMENT_FORMAT, b'\x00' * SEGMENT_SIZE)[0]
    # -- Internal Function --

    def __init__(self, bytes: bytes = None, header: SegmentHeader = None, payload: bytes = None):
        if bytes is None:

            if header['checksum'] == None:
                self.data = pack(
                    HEADER_FORMAT, header["seq_num"], header["ack_num"], header['flag'].get_flag_bytes(), 0)
                self.data += pack(PAYLOAD_FORMAT, payload)
                header['checksum'] = self._calculate_checksum()
                self.header = header

            else:
                self.data = pack(
                    HEADER_FORMAT, header["seq_num"], header["ack_num"], header['flag'].get_flag_bytes(), 0)
                self.data += pack(PAYLOAD_FORMAT, payload)
        else:
            self.data = bytes

    def __str__(self):
        # Optional, override this method for easier
        return str(self.header)

    def _calculate_checksum(self) -> int:
        # do 16 bit checksum without data.header['checksum'] part
        checksum = 0
        for i in range(0, len(self.data), 2):
            checksum += self.data[i] + (self.data[i+1] << 8)

        # remove checksum header
        checksum = checksum - self.data[10] - (self.data[11] << 8)
        return checksum % 65536

    # -- Setter --

    def set_header(self, header: SegmentHeader):
        self.data = pack(HEADER_FORMAT, header['seq_num'],
                         header['ack_num'], int(header['flag'].get_flag_bytes()), header['checksum']) + self.get_payload()

    def set_payload(self, payload: bytes):
        self.data = self.data[0:HEADER_SIZE] + pack(PAYLOAD_FORMAT, payload)

    def set_flag(self, flag_list: SegmentFlag):
        self.data[8] = flag_list.get_flag_bytes()

    # -- Getter --

    def get_flag(self) -> SegmentFlag:
        return SegmentFlag(self.data[8])

    def get_header(self) -> SegmentFlag:
        header = unpack(HEADER_FORMAT, self.data[0:HEADER_SIZE])
        return {
            "seq_num": header[0],
            "ack_num": header[1],
            "flag": SegmentFlag(header[2]),
            "checksum": header[3]
        }

    def get_payload(self) -> bytes:
        return unpack(PAYLOAD_FORMAT, self.data[HEADER_SIZE:])[0]

    # -- Marshalling --

    def set_from_bytes(self, src: bytes):
        self.data = src

    def get_bytes(self) -> bytes:
        return self.data

    # -- Checksum --

    def valid_checksum(self) -> bool:
        return self.header['checksum'] == self._calculate_checksum()

    header = property(get_header, set_header)
    payload = property(get_payload, set_payload)
    flag = property(get_flag, set_flag)
    is_valid = property(valid_checksum)
    bytes = property(get_bytes, set_from_bytes)

    @staticmethod
    def SYN():
        return Segment(
            header={
                "seq_num": 0,
                "ack_num": 0,
                "flag": SegmentFlag.get_flag("SYN"),
                "checksum": None
            },
            payload=b""
        )

    @staticmethod
    def SYN_ACK():
        return Segment(
            header={
                "seq_num": 0,
                "ack_num": 1,
                "flag": SegmentFlag.get_flag("SYN-ACK"),
                "checksum": None
            },
            payload=b""
        )

    @staticmethod
    def ACK():
        return Segment(
            header={
                "seq_num": 0,
                "ack_num": 1,
                "flag": SegmentFlag.get_flag("ACK"),
                "checksum": None
            },
            payload=b""
        )

    @staticmethod
    def FIN():
        return Segment(
            header={
                "seq_num": 0,
                "ack_num": 1,
                "flag": SegmentFlag.get_flag("FIN"),
                "checksum": None
            },
            payload=b""
        )

    @staticmethod
    def FIN_ACK():
        return Segment(
            header={
                "seq_num": 0,
                "ack_num": 1,
                "flag": SegmentFlag.get_flag("FIN-ACK"),
                "checksum": None
            },
            payload=b""
        )
