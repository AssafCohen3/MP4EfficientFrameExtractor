from FrameExtractorConstants import *


class ExtractorExceptionBase(Exception):
    def __init__(self, message, fail_code):
        self.fail_code = fail_code
        super().__init__(message)

    def get_fail_code(self):
        return self.fail_code


class StscLimitException(ExtractorExceptionBase):
    def __init__(self, stsc_size):
        self.stcs_size = stsc_size
        super().__init__(f'stsc size too big: {stsc_size} bytes.', STSC_LIMIT_FAIL_CODE)


class BoxNotFoundException(ExtractorExceptionBase):
    def __init__(self, *box_names):
        self.box_names = box_names
        super().__init__(f'non of {box_names} has been found.', BOX_NOT_FOUND_FAIL_CODE)


class DownloadLimitException(ExtractorExceptionBase):
    def __init__(self, download_size):
        self.download_size = download_size
        super().__init__(f'download size too big: {download_size} bytes', DOWNLOAD_LIMIT_FAIL_CODE)


class ChunksLimitException(ExtractorExceptionBase):
    def __init__(self, current_chunks, new_chunks_number):
        self.current_chunks = current_chunks
        self.new_chunks_number = new_chunks_number
        super().__init__(f'reached chunks limit. current chunks count: {current_chunks}. ' +
                         f'asked to retrieve more {new_chunks_number} chunks', CHUNKS_LIMIT_FAIL_CODE)


class PacketsReaderException(ExtractorExceptionBase):
    def __init__(self, msg):
        super().__init__(msg, PACKETS_READER_FAIL_CODE)


class SampleDescriptionDataNotFoundException(ExtractorExceptionBase):
    def __init__(self, sample_description_id):
        self.sample_description_id = sample_description_id
        super().__init__(f'not found sample description data with id {sample_description_id}', SAMPLE_DESCRIPTION_DATA_NOT_FOUND_FAIL_CODE)


class SampleConvertErrorException(ExtractorExceptionBase):
    def __init__(self, msg):
        super().__init__(msg, SAMPLE_CONVERT_ERROR_FAIL_CODE)


class VideoTrakNotFoundException(ExtractorExceptionBase):
    def __init__(self):
        super().__init__('no video trak found', VIDEO_TRACK_NOT_FOUND_FAIL_CODE)


class CodecNotSupportedException(ExtractorExceptionBase):
    def __init__(self, found_codec):
        self.found_codec = found_codec
        super().__init__(f'codec not supported. found codec: {found_codec}', CODEC_NOT_SUPPORTED_FAIL_CODE)
