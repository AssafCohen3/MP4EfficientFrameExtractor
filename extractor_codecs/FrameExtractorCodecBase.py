
class FrameExtractorCodec:
    def get_name(self):
        raise NotImplementedError()

    def get_extension_name(self):
        raise NotImplementedError()

    def get_private_data(self, codec_data):
        raise NotImplementedError()

    def decode_packet(self, packet, packet_size, nal_length):
        raise NotImplementedError()
