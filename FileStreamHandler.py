import os

from StreamHandlerBase import StreamHandler


class FileStreamHandler(StreamHandler):
    def __init__(self, src_file_name, dst_file_name):
        self.src_file_name = src_file_name
        self.dst_file_name = dst_file_name
        self.file_size = os.stat(src_file_name).st_size

    def get_file_size(self):
        return self.file_size

    def get_file_name(self):
        return self.dst_file_name

    def read_chunks(self, offset, chunks_number, chunk_size):
        to_return = {}
        with open(self.src_file_name, 'rb') as f:
            f.seek(offset)
            for i in range(0, chunks_number):
                to_return[offset + i * chunk_size] = f.read(chunk_size)
        return to_return

    def describe_stream(self):
        print("this is an example of extracting the middle key frame from local file")
