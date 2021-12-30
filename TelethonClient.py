import time

from telethon.errors import FloodWaitError
from telethon.tl.types import InputMessagesFilterVideo


class TelethonClient:
    def __init__(self, client, verbose=1):
        self.client = client
        self.verbose = verbose

    async def get_last_video_id_and_size_in_channel(self, channel_id):
        msgs = [m async for m in self.client.iter_messages(channel_id, filter=InputMessagesFilterVideo(), limit=1)]
        if not msgs:
            print(f"there is no videos in channel {channel_id}")
            exit(1)
        return msgs[0].id, msgs[0].file.size

    async def get_video_chunks(self, channel_id, message_id, offset, chunks_number, chunk_size):
        message = [m async for m in self.client.iter_messages(channel_id, ids=message_id)][0]
        if self.verbose >= 1:
            print(f"downloading {chunk_size*chunks_number} bytes from offset {offset} of video {message_id} in channel {channel_id}...")
        to_return = {}
        i = 0
        while True:
            try:
                async for chunk in self.client.iter_download(message, limit=chunks_number-i, request_size=chunk_size, offset=offset + chunk_size * i):
                    to_return[offset + i*chunk_size] = bytes(chunk)
                    i += 1
                break
            except FloodWaitError as f:
                print(f)
                print(f"sleeping {f.seconds}")
                time.sleep(f.seconds)
        return to_return
