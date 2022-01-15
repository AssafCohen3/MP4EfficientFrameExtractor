import os.path

import cv2
from frameExtractor.FrameExtractor import FrameExtractor
from frameExtractor.FrameExtractorConstants import ALG_VARS_VERBOSE, SUCCESS_CODE
from frameExtractor.extractor_handlers.FileStreamHandler import FileStreamHandler


def show_image(path):
    img = cv2.imread(path)
    cv2.namedWindow(path, cv2.WINDOW_FULLSCREEN)
    cv2.setWindowProperty(path, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_AUTOSIZE)
    cv2.setWindowProperty(path, cv2.WND_PROP_TOPMOST, 1)
    cv2.imshow(path, img)
    cv2.waitKey(0)
    cv2.destroyWindow(path)


print("this example will extract the middle key frame from local file.")
file_name = input("insert the file name: ")
if not os.path.isfile(file_name):
    print("file not exist.")
    exit(1)
handler = FileStreamHandler(file_name, 'example.png')
extractor = FrameExtractor(handler, verbose=ALG_VARS_VERBOSE, target_frame_mult=0.5, target_frame_offset=-1)
status_code, msg = extractor.extract_frame()
if status_code == SUCCESS_CODE:
    show_image(handler.get_file_name())
    os.remove(handler.get_file_name())
else:
    print(f"Error ({status_code}): {msg}")
