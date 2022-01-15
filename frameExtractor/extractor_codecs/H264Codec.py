from .FrameExtractorCodecBase import FrameExtractorCodec
from frameExtractor.FrameExtractorHelpers import *


class H264Codec(FrameExtractorCodec):
    def get_name(self):
        return 'avc1'

    def get_extension_name(self):
        return 'avcC'

    def get_private_data(self, codec_data):
        nals_number = (read_unsigned_byte(codec_data, 4) & 3) + 1
        nals_types = 0  # we want only sps and pps
        offset_in_box = 5
        codec_private_bytes = bytes()
        while offset_in_box < len(codec_data) and nals_types < 2:
            nals_num = read_unsigned_byte(codec_data, offset_in_box) & 31
            offset_in_box += BYTE_SIZE
            nals_types += 1
            for i in range(0, nals_num):
                nal_unit_length = read_unsigned_short(codec_data, offset_in_box)
                offset_in_box += SHORT_SIZE
                data = read_bytes(codec_data, offset_in_box, nal_unit_length)
                offset_in_box += nal_unit_length
                codec_private_bytes += bytes([0, 0, 0, 1])
                codec_private_bytes += data
        return nals_number, codec_private_bytes

    def decode_packet(self, packet, packet_size, nal_length):
        return convert_avcc_packet_to_annex_b(packet, packet_size, nal_length)
