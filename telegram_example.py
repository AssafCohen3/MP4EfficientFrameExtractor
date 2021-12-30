import os

import cv2
from telethon import TelegramClient

from FrameExtractor import FrameExtractor
from FrameExtractorConstants import ALG_VARS_VERBOSE, SUCCESS_CODE
from extractor_handlers.TelegramStreamHandler import TelegramStreamHandler


def show_image(path):
    img = cv2.imread(path)
    cv2.namedWindow(path, cv2.WINDOW_FULLSCREEN)
    cv2.setWindowProperty(path, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_AUTOSIZE)
    cv2.setWindowProperty(path, cv2.WND_PROP_TOPMOST, 1)
    cv2.imshow(path, img)
    cv2.waitKey(0)
    cv2.destroyWindow(path)


print("this example will extract the middle key frame of the last video of provided telegram channel and shows it with opencv.")
try:
    api_id = int(input('insert your api id: '))
except ValueError:
    print("ilegal number")
    exit(1)
api_hash = input('insert your api hash: ')
username = input('insert your username: ')
try:
    channel_id = int(input('insert the id of the channel to download from: '))
except ValueError:
    print("ilegal number")
    exit(1)
client = TelegramClient(username, api_id, api_hash)
client.start(lambda: input('insert your phone: '), lambda: input('insert your password: '))
handler = TelegramStreamHandler(client, channel_id, 'example.png', verbose=1)
extractor = FrameExtractor(handler, verbose=ALG_VARS_VERBOSE, target_frame_mult=0.5)
status_code, msg = extractor.extract_frame()
if status_code == SUCCESS_CODE:
    show_image(handler.get_file_name())
    os.remove(handler.get_file_name())
else:
    print(f"Error ({status_code}): {msg}")
