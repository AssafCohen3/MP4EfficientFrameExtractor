from .FrameExtractorCodecBase import FrameExtractorCodec


class MPEG4Codec(FrameExtractorCodec):
    def get_name(self):
        return 'mp4v'

    def get_extension_name(self):
        return 'esds'

    def get_private_data(self, codec_data):
        return 4, codec_data[25:]

    def decode_packet(self, packet, packet_size, nal_length):
        return packet
