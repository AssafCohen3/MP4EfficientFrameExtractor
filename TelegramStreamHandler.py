from StreamHandlerBase import StreamHandler
from TelethonClient import TelethonClient


class TelegramStreamHandler(StreamHandler):
    def __init__(self, client, channel_id, file_name, verbose=1):
        self.channel_id = channel_id
        self.file_name = file_name
        self.tel_client = TelethonClient(client, verbose)
        self.client = client
        video_id_to_target, video_size = self.run_async(self.tel_client.get_last_video_id_and_size_in_channel, channel_id)
        self.message_id = video_id_to_target
        self.file_size = video_size

    def get_file_size(self):
        return self.file_size

    def get_file_name(self):
        return self.file_name

    def read_chunks(self, offset, chunks_number, chunk_size):
        to_return = self.run_async(self.tel_client.get_video_chunks, self.channel_id, self.message_id, offset, chunks_number, chunk_size)
        return to_return

    def describe_stream(self):
        print("this is an example of extracting the middle key frame from the last video in telegram channel")

    def run_async(self, func, *args):
        return self.client.loop.run_until_complete(func(*args))
