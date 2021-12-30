# stream handler base class
class StreamHandler:
    def get_file_name(self):
        raise NotImplementedError()

    def get_file_size(self):
        raise NotImplementedError()

    def read_chunks(self, offset, chunk_number, chunk_size):
        raise NotImplementedError()

    def describe_stream(self):
        raise NotImplementedError()
