import os
from typing import List

import cv2
from extractor_codecs.FrameExtractorCodecBase import FrameExtractorCodec
from FrameExtractorExceptions import *
from FrameExtractorConstants import *
from FrameExtractorHelpers import *
from extractor_codecs.H264Codec import H264Codec
from extractor_codecs.H265Codec import H265Codec
from extractor_codecs.MPEG4Codec import MPEG4Codec
from extractor_handlers.StreamHandlerBase import StreamHandler


class FrameExtractor:
    def __init__(self, stream_handler: StreamHandler, verbose=SUMMERY_VERBOSE, target_frame_mult=1, target_frame_offset=0,
                 frames_after=0, chunk_size=DEFAULT_CHUNK_SIZE, chunk_limit=DEFAULT_CHUNKS_LIMIT,
                 download_threshold=DEFAULT_DOWNLOAD_THRESHHOLD, frames_limit_from_end=0, stsc_size_threshold=DEFAULT_STSC_SIZE_THRESHOLD,
                 download_limit=DEFAULT_DOWNLOAD_LIMIT, stsc_size_limit=DEFAULT_STSC_SIZE_LIMIT):
        # will cache chunks
        self.chunks_mapper = {}
        # saves how many chunks we used
        self.chunks_count = 0
        # the handler we will use to retrieve chunks and the file name and size.
        self.stream_handler: StreamHandler = stream_handler
        self.verbose = verbose
        # allows targeting frame in percentages(for example for the middle key frame we will put here 0.5)
        self.target_frame_mult = target_frame_mult
        # how many frames to retrieve after target key frame
        self.frames_after = frames_after
        # the chunk size. default is 10 kb
        self.chunk_size = chunk_size
        # limit the chunks that the algorithm will retrieve
        self.chunk_limit = chunk_limit
        # specify the offset from end to the target key frame(-1 for the last, -2 for the frame before the last and so on)
        self.target_frame_offset = target_frame_offset
        # any download above the threshold will require the confirmation of the user
        self.download_threshold = download_threshold
        # allows limiting the frames retrieved after the target key frame. for example if you want to target one of the last 90 frames put here 90
        # and the extractor will stop at 90 frames from the end
        self.frames_limit_from_end = frames_limit_from_end
        # any stsc size above the threshold will require the confirmation of the user
        self.stsc_size_threshold = stsc_size_threshold
        # any download size above will raise error
        self.download_limit = download_limit
        # any stsc size above will raise error
        self.stsc_size_limit = stsc_size_limit
        # allow the use of the same extractor multiple times without downloading the boxes' data every time
        self.initiated = False
        # the size of the processed file
        self.file_size = None
        # supported codecs
        self.codecs: List[FrameExtractorCodec] = [H264Codec(), H265Codec(), MPEG4Codec()]
        # caching the boxes for the extractor
        self.boxes = {}

    def print_verbose(self, to_print, verbose_level):
        if self.verbose >= verbose_level:
            print(to_print)

    def find_box(self, box_name, start_offset, end):
        if start_offset >= end:
            return 0

        offset = start_offset
        box_size = 0
        # look for the box
        while offset + 8 < end:
            box_entry_bytes = self.get_bytes(offset, 8)
            atom_size = read_unsigned_integer(box_entry_bytes, 0)
            if 1 < atom_size < 8:  # erroneous size
                return 0, 0  # file cut

            atom_type = read_bytes(box_entry_bytes, 4, 4)
            if len(atom_type) < 4:
                return 0, 0  # file cut

            if atom_size == 0:  # box extends to the end of file
                atom_size = self.get_file_size() - offset - 4
                if box_name is None or atom_type.decode(encoding='UTF-8') == box_name:
                    box_size = atom_size
                    break
                return 0, 0  # we have nothing more to look for
            elif atom_size == 1:  # 64 bit-size
                atom_size = self.read_unsigned_long_direct(offset + 8)

            if box_name is None or atom_type.decode(encoding='UTF-8') == box_name:
                box_size = atom_size
                break
            offset += atom_size
            self.print_verbose('%s    size    %12d' % (atom_type.decode(encoding='UTF-8'), atom_size), BOX_FINDERS_VERBOSE)
        if box_name is None or atom_type.decode(encoding='UTF-8') == box_name:
            self.print_verbose('found! %s    size    %12d' % (atom_type.decode(encoding='UTF-8'), atom_size), BOX_FINDERS_VERBOSE)
        return box_size, offset, atom_type.decode(encoding='UTF-8')

    def look_for_video_trak(self, start_offset, end):
        offs = start_offset
        video_trak = 0
        while offs + 8 < end:
            trak_size, trak_offs, _ = self.find_box('trak', offs, end)
            if trak_size == 0:
                raise BoxNotFoundException("trak")
            mdia_size, mdia_offs, _ = self.find_box('mdia', trak_offs + 8, trak_offs + trak_size)
            if mdia_size == 0:
                raise BoxNotFoundException("mdia")
            hdlr_size, hdlr_offs, _ = self.find_box('hdlr', mdia_offs + 8, mdia_offs + mdia_size)
            if hdlr_size == 0:
                raise BoxNotFoundException("hdlr")

            # skip over version and pre-defined
            trak_type = self.read_characters_direct(hdlr_offs + 16, 4)
            self.print_verbose(f'trak type: {trak_type}', BOX_FINDERS_VERBOSE)

            if trak_type.decode(encoding='UTF-8') == 'vide':
                return True, mdia_offs, mdia_size, video_trak

            offs = trak_offs + trak_size
            video_trak += 1
        return False, -1, -1, -1

    def get_file_size(self):
        if not self.file_size:
            self.file_size = self.stream_handler.get_file_size()
        return self.file_size

    def read_chunks(self, offset, chunk_number):
        self.print_verbose(f"reading {chunk_number} chunks in offset {offset}...", READING_VERBOSE)
        if self.chunks_count + chunk_number > self.chunk_limit:
            raise ChunksLimitException(self.chunks_count, chunk_number)
        chunks_dict = self.stream_handler.read_chunks(offset, chunk_number, self.chunk_size)
        self.chunks_count += chunk_number
        for chunk_offset, chunk_bytes in chunks_dict.items():
            self.chunks_mapper[chunk_offset] = chunk_bytes

    def get_bytes(self, offset, bytes_number):
        self.print_verbose(f"getting {bytes_number} bytes in offset {offset}", READING_VERBOSE)
        required_chunks_offsets = [o - o % self.chunk_size for o in range(offset, (offset + bytes_number) -
                                                                          (offset + bytes_number) % self.chunk_size + self.chunk_size, self.chunk_size)]
        sequence_start = -1
        for i, required_chunk_offset in enumerate(required_chunks_offsets):
            if required_chunk_offset not in self.chunks_mapper:
                if sequence_start < 0:
                    sequence_start = i
            elif sequence_start >= 0:
                self.read_chunks(required_chunks_offsets[sequence_start], i - sequence_start)
                sequence_start = -1
        if sequence_start >= 0:
            self.read_chunks(required_chunks_offsets[sequence_start], len(required_chunks_offsets) - sequence_start)

        target_chunk = self.chunks_mapper[required_chunks_offsets[0]]
        for chunk_offset in required_chunks_offsets[1:]:
            target_chunk += self.chunks_mapper[chunk_offset]
        return read_bytes(target_chunk, offset % self.chunk_size, bytes_number)

    def read_unsigned_long_direct(self, offset):
        target_bytes = self.get_bytes(offset, LONG_SIZE)
        return read_unsigned_long(target_bytes, 0)

    def read_unsigned_integer_direct(self, offset):
        target_bytes = self.get_bytes(offset, INT_SIZE)
        return read_unsigned_integer(target_bytes, 0)

    def read_unsigned_short_direct(self, offset):
        target_bytes = self.get_bytes(offset, SHORT_SIZE)
        return read_unsigned_short(target_bytes, 0)

    def read_unsigned_byte_direct(self, offset):
        target_bytes = self.get_bytes(offset, BYTE_SIZE)
        return read_unsigned_byte(target_bytes, 0)

    def read_characters_direct(self, offset, number_of_characters):
        target_bytes = self.get_bytes(offset, number_of_characters)
        return read_bytes(target_bytes, 0, number_of_characters)

    def ensure_box_exist(self, box_name):
        if box_name not in self.boxes:
            raise BoxNotFoundException(box_name)

    def get_target_key_sample(self):
        self.ensure_box_exist('stss')
        stss_offset = self.boxes['stss'][BOX_OFFSET_IDX]
        table_entry_bytes = self.get_bytes(stss_offset, 16)
        number_of_entries = read_unsigned_integer(table_entry_bytes, 12)
        target_entry = round((self.target_frame_offset % number_of_entries) * self.target_frame_mult)
        offset_from_start = stss_offset + 16 + target_entry * INT_SIZE
        return self.read_unsigned_integer_direct(offset_from_start)

    def get_number_of_samples(self):
        self.ensure_box_exist('stsz')
        stsz_offset = self.boxes['stsz'][BOX_OFFSET_IDX]
        return self.read_unsigned_integer_direct(stsz_offset + 16)

    def get_samples_chunks(self, target_samples_numbers):
        self.ensure_box_exist('stsc')
        stsc_size, stsc_offset = self.boxes['stsc']
        table_entry_bytes = self.get_bytes(stsc_offset, 16)
        number_of_entries = read_unsigned_integer(table_entry_bytes, 12)
        if stsc_size >= self.stsc_size_limit:
            raise StscLimitException(stsc_size)
        if stsc_size >= self.stsc_size_threshold:
            ans = input(f"idiotic chunks split. {round(stsc_size / MB_SIZE, 2)} MB to read. continue?(y/n) ") != 'n'
            if not ans:
                raise StscLimitException(stsc_size)
        self.get_bytes(stsc_offset, stsc_size)
        offset_to_table = stsc_offset + 16
        found_samples = 0
        found_chunks = 0
        current_target_index = 0
        chunks_to_return = []
        last_entry_first_chunk = None
        last_entry_chunk_samples_number = None
        last_entry_first_sample_number = None
        last_entry_reference_id = None
        for i in range(0, number_of_entries):
            entry_bytes = self.get_bytes(offset_to_table + i * 12, 12)
            entry_first_chunk = read_unsigned_integer(entry_bytes, 0)
            entry_samples_per_chunk = read_unsigned_integer(entry_bytes, 4)
            entry_reference_id = read_unsigned_integer(entry_bytes, 8)
            if last_entry_first_chunk is not None:
                last_chunks_count = entry_first_chunk - last_entry_first_chunk
                additional_samples = last_entry_chunk_samples_number * last_chunks_count
                found_samples += additional_samples
                while current_target_index < len(target_samples_numbers) and found_samples >= target_samples_numbers[current_target_index]:
                    target_chunk_index = ((target_samples_numbers[current_target_index] - last_entry_first_sample_number) // last_entry_chunk_samples_number) + found_chunks + 1
                    target_chunk_first_sample = last_entry_first_sample_number + (target_chunk_index - found_chunks - 1) * last_entry_chunk_samples_number
                    chunks_to_return.append((target_chunk_index, target_chunk_first_sample, last_entry_reference_id))
                    current_target_index += 1
                if current_target_index == len(target_samples_numbers):
                    break
                found_chunks += last_chunks_count
            last_entry_first_chunk = entry_first_chunk
            last_entry_chunk_samples_number = entry_samples_per_chunk
            last_entry_first_sample_number = found_samples + 1
            last_entry_reference_id = entry_reference_id

        while current_target_index < len(target_samples_numbers):
            target_chunk_index = ((target_samples_numbers[current_target_index] - last_entry_first_sample_number) // last_entry_chunk_samples_number) + found_chunks + 1
            target_chunk_first_sample = last_entry_first_sample_number + (target_chunk_index - found_chunks - 1) * last_entry_chunk_samples_number
            chunks_to_return.append((target_chunk_index, target_chunk_first_sample, last_entry_reference_id))
            current_target_index += 1
        return chunks_to_return

    def get_samples_sizes_and_chunks_offsets(self, target_chunks, target_samples_numbers):
        self.ensure_box_exist('stsz')
        stsz_offset = self.boxes['stsz'][BOX_OFFSET_IDX]
        samples_to_ret = []
        for target_chunk, target_sample_number in zip(target_chunks, target_samples_numbers):
            offset_in_chunk = 0
            target_chunk_samples_entries_bytes = self.get_bytes(
                stsz_offset + 20 + INT_SIZE * (target_chunk[CHUNK_FIRST_SAMPLE_IDX] - 1),
                (target_sample_number - target_chunk[CHUNK_FIRST_SAMPLE_IDX] + 1) * INT_SIZE)
            for i in range(0, target_sample_number - target_chunk[CHUNK_FIRST_SAMPLE_IDX] + 1):
                entry_sample_size = read_unsigned_integer(target_chunk_samples_entries_bytes, INT_SIZE * i)
                if i + target_chunk[CHUNK_FIRST_SAMPLE_IDX] == target_sample_number:
                    samples_to_ret.append(
                        (i + target_chunk[CHUNK_FIRST_SAMPLE_IDX], offset_in_chunk, entry_sample_size))
                offset_in_chunk += entry_sample_size
        return samples_to_ret

    def get_chunks_offsets(self, target_chunks):
        atom_to_use = 'stco'
        if 'stco' not in self.boxes:
            if 'co64' not in self.boxes:
                raise BoxNotFoundException('stco', 'co64')
            atom_to_use = 'co64'
        stco_offset = self.boxes[atom_to_use][BOX_OFFSET_IDX]
        offsets_to_return = []
        for target_chunk in target_chunks:
            if atom_to_use == 'stco':
                offsets_to_return.append(
                    self.read_unsigned_integer_direct(stco_offset + 16 + (target_chunk[CHUNK_NUMBER_IDX] - 1) * INT_SIZE))
            else:
                offsets_to_return.append(
                    self.read_unsigned_long_direct(stco_offset + 16 + (target_chunk[CHUNK_NUMBER_IDX] - 1) * LONG_SIZE))
        return offsets_to_return

    def get_target_sample_description_box(self, target_sample_id):
        self.ensure_box_exist('stsd')
        stsd_size, stsd_offset = self.boxes['stsd']
        offset_in_box = 16
        while offset_in_box < stsd_size:
            entry_bytes = self.get_bytes(stsd_offset + offset_in_box, 16)
            entry_size = read_unsigned_integer(entry_bytes, 0)
            entry_type = read_bytes(entry_bytes, 4, 4)
            entry_id = read_unsigned_short(entry_bytes, 14)
            if entry_id == target_sample_id:
                return entry_size, stsd_offset + offset_in_box, entry_type.decode(encoding='UTF-8')
            offset_in_box += entry_size
        raise SampleDescriptionDataNotFoundException(target_sample_id)

    def detect_codec(self, vsd_type):
        for codec in self.codecs:
            if codec.get_name() == vsd_type:
                return codec
        return None

    def find_boxes(self):
        moov_size, moov_offs, _ = self.find_box('moov', 0, self.get_file_size())
        if moov_size == 0:
            raise BoxNotFoundException('moov')
        moov_end = moov_offs + moov_size + 4
        video_found, mdia_offs, mdia_size, video_trak = self.look_for_video_trak(moov_offs + 8, moov_end)
        if not video_found:
            raise VideoTrakNotFoundException()
        self.print_verbose('Video Trak Number %d found' % video_trak, BOX_FINDERS_VERBOSE)
        minf_size, minf_offs, _ = self.find_box('minf', mdia_offs + 8, mdia_offs + mdia_size)
        if minf_size == 0:
            raise BoxNotFoundException('minf')
        stbl_size, stbl_offs, _ = self.find_box('stbl', minf_offs + 8, minf_offs + minf_size)
        if stbl_size == 0:
            raise BoxNotFoundException('stbl')

        stsd_size, stsd_offs, _ = self.find_box('stsd', stbl_offs + 8, stbl_offs + stbl_size)
        if stsd_size == 0:
            raise BoxNotFoundException('stsd')
        self.boxes['stsd'] = (stsd_size, stsd_offs)
        stss_size, stss_offs, _ = self.find_box('stss', stbl_offs + 8, stbl_offs + stbl_size)
        if stss_size == 0:
            raise BoxNotFoundException('stss')
        self.boxes['stss'] = (stss_size, stss_offs)
        stsc_size, stsc_offs, _ = self.find_box('stsc', stbl_offs + 8, stbl_offs + stbl_size)
        if stsc_size == 0:
            raise BoxNotFoundException('stsc')
        self.boxes['stsc'] = (stsc_size, stsc_offs)
        stsz_size, stsz_offs, _ = self.find_box('stsz', stbl_offs + 8, stbl_offs + stbl_size)
        if stsz_size == 0:
            raise BoxNotFoundException('stsz')
        self.boxes['stsz'] = (stsz_size, stsz_offs)
        stco_size, stco_offs, _ = self.find_box('stco', stbl_offs + 8, stbl_offs + stbl_size)
        if stco_size == 0:
            co64_size, co64_offs, _ = self.find_box('co64', stbl_offs + 8, stbl_offs + stbl_size)
            if co64_size == 0:
                raise BoxNotFoundException('stco', 'co64')
            self.boxes['co64'] = (co64_size, co64_offs)
        else:
            self.boxes['stco'] = (stco_size, stco_offs)

    def init(self):
        self.print_verbose("initiating...", ALG_VARS_VERBOSE)
        self.find_boxes()
        self.initiated = True

    def collect_target_samples(self):
        target_sample_number = self.get_target_key_sample()
        self.print_verbose(f"target sample number: {target_sample_number}", ALG_VARS_VERBOSE)
        number_of_samples = self.get_number_of_samples()
        self.print_verbose(f"video samples count: {number_of_samples}", ALG_VARS_VERBOSE)
        target_samples_numbers = [n for n in range(target_sample_number, max(target_sample_number + 1,
                                                                             min(number_of_samples - self.frames_limit_from_end,
                                                                                 target_sample_number + self.frames_after) + 1))]
        self.print_verbose(f"target samples: {target_samples_numbers}", ALG_VARS_VERBOSE)
        self.print_verbose(f"targeting {len(target_samples_numbers)} samples", ALG_VARS_VERBOSE)
        target_chunks = self.get_samples_chunks(target_samples_numbers)
        self.print_verbose(f"target chunks(chunk number, chunk first sample, chunk description data index): {target_chunks}", ALG_VARS_VERBOSE)
        target_samples = self.get_samples_sizes_and_chunks_offsets(target_chunks, target_samples_numbers)
        self.print_verbose(f"target samples(sample number, offset in chunk, sample size): {target_samples}", ALG_VARS_VERBOSE)
        target_chunks_offsets = self.get_chunks_offsets(target_chunks)
        self.print_verbose(f"target chunks offsets(chunk number, chunk offset): {list(zip(map(lambda c: c[CHUNK_NUMBER_IDX], target_chunks), target_chunks_offsets))}", ALG_VARS_VERBOSE)

        return target_chunks[0][CHUNK_DESCRIPTION_DATA_IDX], \
            [(target_sample_number, chunk_offset + target_sample_offset_in_chunk, target_sample_size) for
                ((target_sample_number, target_sample_offset_in_chunk, target_sample_size), chunk_offset) in
                zip(target_samples, target_chunks_offsets)]

    def retrieve_and_decode_samples_bytes(self, target_samples, description_data_id):
        vsd_size, vsd_offs, vsd_type = self.get_target_sample_description_box(description_data_id)
        video_codec = self.detect_codec(vsd_type)
        if video_codec is None:
            raise CodecNotSupportedException(vsd_type)
        self.print_verbose(f'using codec: {video_codec.get_name()}', ALG_VARS_VERBOSE)
        codec_size, codec_offs, _ = self.find_box(video_codec.get_extension_name(), vsd_offs + 86, vsd_offs + vsd_size)
        nals_number, codec_private_bytes = video_codec.get_private_data(self.get_bytes(codec_offs + 8, codec_size - 8))
        samples_converted_packets = bytes()
        min_byte = target_samples[0][SAMPLE_OFFSET_IN_FILE_IDX]
        max_byte = target_samples[-1][SAMPLE_OFFSET_IN_FILE_IDX] + target_samples[-1][SAMPLE_SIZE_IDX]
        download_size = max_byte - min_byte
        if download_size >= self.download_limit:
            raise DownloadLimitException(download_size)
        elif download_size > self.download_threshold:
            self.stream_handler.describe_stream()
            print(f"warning!!! download size {round(download_size/MB_SIZE, 2)} MB above download threshhold.")
            ans = input("procceed?(y/n) ") != 'n'
            if not ans:
                raise DownloadLimitException(download_size)
        self.get_bytes(min_byte, download_size)
        for sample_number, sample_offset_in_file, sample_size in target_samples:
            sample_packet = self.get_bytes(sample_offset_in_file, sample_size)
            conevrted_sample_packet = video_codec.decode_packet(sample_packet, sample_size, nals_number)
            samples_converted_packets += conevrted_sample_packet
        converted_samples_packets_with_extradata = combine_packet_with_codec_private_data(samples_converted_packets, codec_private_bytes)
        return converted_samples_packets_with_extradata

    def save_packets_and_extract_last_frame(self, samples_valid_packets):
        with open("tmp.mp4", "wb") as fw:
            fw.write(samples_valid_packets)
        try:
            vidcap = cv2.VideoCapture('tmp.mp4')
            success, image_toshow = vidcap.read()
            while success:
                success, tmp_image_to_show = vidcap.read()
                if success:
                    image_toshow = tmp_image_to_show
        except Exception as e:
            os.remove('tmp.mp4')
            raise PacketsReaderException(str(e))
        os.remove('tmp.mp4')
        cv2.imwrite(self.stream_handler.get_file_name(), image_toshow)

    def extract_frame(self):
        try:
            if not self.initiated:
                self.init()
            description_data_id, target_samples = self.collect_target_samples()
            converted_samples_packets = self.retrieve_and_decode_samples_bytes(target_samples, description_data_id)
            self.save_packets_and_extract_last_frame(converted_samples_packets)
        except ExtractorExceptionBase as e:
            return e.get_fail_code(), str(e)
        except Exception as e:
            return UNKNOWN_ERROR_FAIL_CODE, str(e)
        if self.verbose >= SUMMERY_VERBOSE:
            print(f"success!!!!!")
            print(f"used chunks: {self.chunks_count}.")
            print(f"used memory: {round((self.chunks_count * self.chunk_size) / MB_SIZE, 2)} MB")
            print(f"saved memory: {round((self.get_file_size() - (self.chunks_count * self.chunk_size)) / MB_SIZE, 2)} MB")
        return SUCCESS_CODE, f'frame extracted to {self.stream_handler.get_file_name()}'
