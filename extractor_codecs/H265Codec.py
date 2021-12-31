from .FrameExtractorCodecBase import FrameExtractorCodec
from FrameExtractorHelpers import *


class H265Codec(FrameExtractorCodec):
    def get_name(self):
        return 'hev1'

    def get_extension_name(self):
        return 'hvcC'

    def get_private_data(self, codec_data):
        nals_number = (read_unsigned_byte(codec_data, 22) & 3) + 1
        codec_private_bytes = bytes()
        offset_in_box = 23
        nals_types = 0  # we want only vps, sps and pps
        while offset_in_box < len(codec_data) and nals_types < 3:
            offset_in_box += 1  # skip nal_type byte
            nals_num = read_unsigned_short(codec_data, offset_in_box)
            offset_in_box += 2
            nals_types += 1
            for i in range(0, nals_num):
                nal_unit_length = read_unsigned_short(codec_data, offset_in_box)
                offset_in_box += 2
                data = codec_data[offset_in_box: offset_in_box + nal_unit_length]
                offset_in_box += nal_unit_length
                codec_private_bytes += bytes([0, 0, 0, 1])
                codec_private_bytes += data
        return nals_number, codec_private_bytes

    def decode_packet(self, packet, packet_size, nal_length):
        return convert_avcc_packet_to_annex_b(packet, packet_size, nal_length)
