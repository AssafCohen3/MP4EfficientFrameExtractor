import struct
from FrameExtractorExceptions import SampleConvertErrorException


# bytes unpacking helper methods
def read_unsigned_long(bytes_to_read_from, offset):
    return struct.unpack("!Q", bytes_to_read_from[offset: offset + 8])[0]


def read_unsigned_integer(bytes_to_read_from, offset):
    return struct.unpack("!I", bytes_to_read_from[offset: offset + 4])[0]


def read_unsigned_short(bytes_to_read_from, offset):
    return struct.unpack("!H", bytes_to_read_from[offset: offset + 2])[0]


def read_unsigned_byte(bytes_to_read_from, offset):
    return struct.unpack("!B", bytes_to_read_from[offset: offset + 1])[0]


def read_characters(bytes_to_read_from, offset):
    return bytes_to_read_from[offset: offset + 4]


# packets converting helpers
def convert_avcc_packet_to_annex_b(sample_packet_bytes, sample_packet_size, nal_length_size):
    res = bytes()
    if nal_length_size == 4:
        offset_in_packet = 0
        while offset_in_packet < sample_packet_size:
            size = read_unsigned_integer(sample_packet_bytes, offset_in_packet)
            res += bytes([0, 0, 0, 1])
            res += sample_packet_bytes[offset_in_packet + 4: offset_in_packet + 4 + size]
            offset_in_packet += size + 4
    else:
        raise SampleConvertErrorException("nal length size defferent then 4 is not supported")
    return res


def combine_packet_with_codec_private_data(sample_packet_decoded, codec_private_bytes):
    return codec_private_bytes + sample_packet_decoded
