from typing import Counter
import ffmpeg
import os
import warnings
import cv2
import numpy as np
import zlib

from p8scii import NumToP8Converter

# FFMPEG THRESH COMMAND: ffmpeg -i bad_apple_orig.mp4 -f lavfi -i color=gray -f lavfi -i color=black -f lavfi -i color=white -lavfi threshold threshv2.mp4

FPS = 30
TARGET_RESOLUTION = (64, 48)

IN_PATH = os.path.join(os.path.dirname(__file__), "bad_apple_orig.mp4")
OUT_PATH = os.path.join(os.path.dirname(__file__), "small_apple_v2.mp4")

FRAME_OUT_BIN = os.path.join(os.path.dirname(__file__), "frames.bin")
HEAD_OUT_BIN = os.path.join(os.path.dirname(__file__), "headers.bin")


# FRAME_OUT_PATH = "output_frames.txt"
# HEAD_OUT_PATH = "output_headers.txt"

def main():
    
    #vid_resize(IN_PATH, OUT_PATH, 32)
    #START FRAME FOR 30FPS: 46 end 6515
    #START FRAME FOR 24FPS: 36 end 5213
    #end frame for 24fps: 1400
    frame_bytes, header_bytes, rle_bytes = encode_video_p8(os.path.join(os.path.dirname(__file__), "retimed.mp4"), start_frame=4, end_frame=6428, show_frame_num=55, merge_header=False, wtiles=TARGET_RESOLUTION[0]//4, htiles=TARGET_RESOLUTION[1]//4)#2336

    combined_bytes = header_bytes + frame_bytes
    print(f"\nUncompressed vid length: {len(frame_bytes)}")
    compressed_frame_bytes = zlib.compress(frame_bytes, 9)
    print(f"Compressed vid length: {len(compressed_frame_bytes)}")

    print(f"\nUncompressed header length: {len(header_bytes)}")
    compressed_header_bytes = zlib.compress(header_bytes, 9)
    print(f"Compressed header length: {len(compressed_header_bytes)}")

    print(f"\nUncompressed combined vid length: {len(combined_bytes)}")
    compressed_combined_bytes = zlib.compress(combined_bytes, 9)
    print(f"Compressed combined vid length: {len(compressed_combined_bytes)}")

    print(f"\nUncompressed RLE vid length: {len(rle_bytes)}")
    compressed_rle_bytes = zlib.compress(rle_bytes, 9)
    print(f"Compressed RLE vid length: {len(compressed_rle_bytes)}")

    with open(FRAME_OUT_BIN, "wb") as framebinfile, open(HEAD_OUT_BIN, "wb") as headbinfile:
        framebinfile.write(frame_bytes)
        headbinfile.write(header_bytes)
    
    # print(frames)S
    # for i in range(256):
    #     print(f"{i}: {num_to_p8[i]}")



def vid_resize(vid_path, output_path, width, overwrite = True):
    '''
    use ffmpeg to resize the input video to the width given, keeping aspect ratio
    '''
    if not( os.path.isdir(os.path.dirname(output_path))):
        raise ValueError(f'output_path directory does not exists: {os.path.dirname(output_path)}')

    if os.path.isfile(output_path) and not overwrite:
        warnings.warn(f'{output_path} already exists but overwrite switch is False, nothing done.')
        return None

    input_vid = ffmpeg.input(vid_path, f="mp4")
    input_audio = input_vid.audio
    vid = (
        input_vid
        # .filter('scale', width, -1, flags="neighbor")
        # .filter('fps', fps=FPS, round='up')
        .output(input_audio, output_path, preset="ultrafast", crf=0)
        .overwrite_output()
        .run()
    )
    return output_path


def img_from_cap(capture):
    success, img = capture.read(cv2.IMREAD_GRAYSCALE)
    if success:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # img = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 7, 0)
        img = cv2.resize(img, TARGET_RESOLUTION, interpolation=cv2.INTER_AREA)
        retval, img = cv2.threshold(img,115,255,cv2.THRESH_BINARY)
        
        
    return success, img


def encode_video_p8(video_path, start_frame = 1, end_frame = -1, show_frame_num = -1, wtiles = 8, htiles = 6, merge_header = False):
    print(video_path)
    if not( os.path.isdir(os.path.dirname(video_path))):
        raise ValueError(f'video_path directory does not exists: {os.path.dirname(video_path)}')
    
    frame_num = start_frame
    capture = cv2.VideoCapture(video_path)
    capture.set(cv2.CAP_PROP_POS_FRAMES, frame_num-1)

    success, img = img_from_cap(capture)
    print(img.shape)
    prev_img = []
    
    p8_frame_chars = []
    p8_header_chars = []

    p8_frame_nums = []
    p8_header_nums = []

    p8_rle_nums = []
    total_empty_tiles = 0
    min_empty_tiles = 1000
    total_empty_frames = 0
    empty_frame_streak = 0
    empty_streak_history = Counter()
    
    head_to_p8 = NumToP8Converter().num_to_p8
    tile_to_p8 = NumToP8Converter().num_to_p8

    while success:
        p8_frame_str = ""
        p8_frame = None

        # First frame proccessed
        if len(prev_img) == 0:
            prev_img = img.copy()
            success,img = img_from_cap(capture)
            continue

        frame_num += 1

        
        diff_img = changed_pixels(img, prev_img)

        tiles = split_image_tiles(diff_img, wtiles, htiles)
        num_empty_tiles = empty_tile_count(tiles)
        
        

        if num_empty_tiles == len(tiles):
            empty_frame_streak += 1
            total_empty_frames += 1

            p8_header_nums.extend([255] * htiles)
            frame_header_chars = head_to_p8(255) * htiles

            p8_header_chars.append(frame_header_chars)

            if merge_header: 
                p8_frame_chars.append(frame_header_chars)
                p8_frame_nums.extend([255] * htiles)

        else:
            # Get frame encoded into list of 8 bit numbers. 6 bytes for header, 2 bytes per non-blank tile
            p8_frame = encode_p8_str(diff_img, wtiles, htiles)

            p8_header_nums.extend(p8_frame[0])
            frame_header_chars = "".join(head_to_p8(num) for num in p8_frame[0])
            p8_header_chars.append(frame_header_chars)
            if merge_header:
                p8_frame_str += frame_header_chars
            # Loop over processed tiles
            for i in range(1, len(p8_frame)):
                tile = p8_frame[i]
                # Each tile is 2 8 bit numbers.
                upper_tile_char = tile_to_p8(tile[0])
                lower_tile_char = tile_to_p8(tile[1])
                p8_frame_str += upper_tile_char + lower_tile_char
                p8_frame_nums.extend(tile)
            total_empty_tiles += num_empty_tiles
            min_empty_tiles = min(min_empty_tiles, num_empty_tiles)

        p8_frame_chars.append(p8_frame_str)

        diff_rle = encode_frame_RLE(diff_img)
        p8_rle_nums.extend(diff_rle)

        if frame_num == show_frame_num:
            diff_rle = encode_frame_RLE(diff_img)
            print(f"diff RLE encoded (length {len(diff_rle)}): {diff_rle}")
            # img_rle = encode_frame_RLE(img, True)
            # print(f"Image RLE encoded (length {len(img_rle)}): {img_rle}")
            print(f"showing frame diff {frame_num}")
            # print(f"Diff RLE string: \n{RLE_str}")
            cv2.imshow("Current", cv2.resize(img, (320, 240), interpolation=cv2.INTER_NEAREST))
            cv2.imshow("Previous", cv2.resize(prev_img, (320, 240), interpolation=cv2.INTER_NEAREST))
            cv2.imshow("Difference", cv2.resize(diff_img, (320, 240), interpolation=cv2.INTER_NEAREST))
            p8_frame_flat = [j for sub in p8_frame for j in sub]
            print(f"p8 num encoding (length {len(p8_frame_flat)}): {p8_frame_flat}")
            # print(f"p8 frame string encoding: ''{p8_frame_str}''")
            # print(f"p8 frame bytes encoding: [{p8_frame_nums}]")
            # print(f"p8 header bytes encoding: [{p8_header_nums}]")
            # cv2.imshow("TileTopM", cv2.resize(tiles[47], (80, 60), interpolation=cv2.INTER_NEAREST))
            # tiles = split_image_tiles(diff_img, 8, 6)
            # print(tiles)
            # print(len(tiles))
            # for i in range(len(tiles)):
            #     try:
            #         cv2.imshow(f"Split{i}", cv2.resize(tiles[i], (160, 120), interpolation=cv2.INTER_NEAREST))
            #     except:
            #         print("bruh")
            cv2.waitKey(0)
        
        if frame_num == end_frame:
            break
        prev_img = img.copy()
        success,img = img_from_cap(capture)

    p8_frames_as_str = "".join(p8_frame_chars)
    p8_headers_as_str = "".join(p8_header_chars)
    p8_frames_as_bytes = bytes(p8_frame_nums)
    p8_headers_as_bytes = bytes(p8_header_nums)

    num_frames = frame_num - start_frame
    print(f"Total Frames: {num_frames}")
    print(f"Total Tiles: {(num_frames - total_empty_frames) * 48 - total_empty_tiles}")
    print(f"Num Header Characters: {len(p8_headers_as_str)}")
    print(f"Num Characters: {len(p8_frames_as_str)}")
    print(f"Total empty frames: {total_empty_frames}/{num_frames} frames")
    print(f"Average empty tiles: {total_empty_tiles / (frame_num - start_frame - total_empty_frames)} per non-empty frame")
    print(f"Estimated num characters @ 3 chars/tile + 1 char/frame: {(frame_num - start_frame - total_empty_frames) * 48 - total_empty_tiles}")

    return p8_frames_as_bytes, p8_headers_as_bytes, bytes(p8_rle_nums)
        

def encode_p8_str(image, wtiles : int = 8, htiles : int = 6, invert: bool = True):
    tiles = split_image_tiles(image, wtiles, htiles)
    out_str = ""
    processed_tile_bytes = []
    header_bytes = []
    tiles_skipped = 0
    headers_per_row = wtiles // 8
    prev_p_val = 0
    curr_repeat_tiles = 0
    disabled_rows = 0
    for row_num in range(htiles):
        for header_index in range(headers_per_row):
            row_header = np.uint8(0)
            row_empty = True
            for col_num in range(header_index * 8, header_index * 8 + 8):
                tile_index = row_num * wtiles + col_num
                curr_tile = tiles[tile_index].flatten()

                p_val = np.uint16(0)
                for pixel_num in range(16):
                    pixel = curr_tile[pixel_num]
                    p_val = (p_val << 1)
                    if pixel > 0:
                        p_val = p_val | 1
                
                
                row_header = row_header << 1
                # If tile has a lit pixel, add it to the string
                if p_val > 0:
                    row_empty = False

                    top_number = np.uint8((p_val & 0b1111111100000000) >> 8)
                    bottom_number = np.uint8(p_val) & 0b0000000011111111

                    if invert:
                        top_number = np.subtract(np.uint8(255), top_number)
                        bottom_number = np.subtract(np.uint8(255), bottom_number)
                    processed_tile_bytes.append([top_number, bottom_number])
                    row_header = row_header | 1
                else:
                    tiles_skipped += 1
                prev_p_val = p_val
            if invert: 
                row_header = np.subtract(np.uint8(255), row_header)
            header_bytes.append(row_header)

    return [header_bytes, *processed_tile_bytes]


def encode_frame_RLE(image, invert: bool = False):
    pixel_array = np.trim_zeros(image.flatten(), 'b')

    max_skip = 127
    max_flip = 255
    rle_values = []
    curr_skip = np.uint8(0)
    curr_flip = np.uint8(0)
    is_skipping = True

    skip_col = 0
    if invert:
        skip_col = 255

    gap_found = False
    initial_gap = 0
    for pixel in pixel_array:
        # if not gap_found:
        #     if pixel == 0:
        #         initial_gap += 1
        #     else:
        #         gap_found = True
        # if gap_found:
            
        if is_skipping:
            if pixel == skip_col and curr_skip < max_skip:
                curr_skip += 1
            else:
                curr_flip = 0
                is_skipping = False
        if not is_skipping:
            if pixel != skip_col:
                if(curr_flip < max_flip):
                    curr_flip += 1
                    continue
            if(curr_flip == 1):
                # If we only flip 1 tile, set greatest bit of curr_skip to 1 and add only curr_skip to output
                rle_values.append(curr_skip | 0b10000000)
            else:
                rle_values.extend((curr_skip, curr_flip))
            curr_skip = 1
            curr_flip = 0
            is_skipping = True
    
    if not is_skipping:
        rle_values.extend((curr_skip, curr_flip))
    else:
        # TODO loop backwards through list and remove empty skips if they exist
        pass
    #rle_values.extend([np.uint8(0)] * 2)
    rle_values.insert(0, np.uint8(len(rle_values)))
    return rle_values


def empty_tile_count(tiles):
    count = 0
    for i in range(len(tiles)):
        if np.sum(tiles[i]) == 0:
            count += 1
    return count


def split_image_tiles(img, numcols: int, numrows: int):

    image_tile = []
    height = int(img.shape[0] / numrows)
    width = int(img.shape[1] / numcols)
    for row in range(numrows):
        for col in range(numcols):
            y0 = row * height
            y1 = y0 + height
            x0 = col * width
            x1 = x0 + width
            image_tile.append((img[y0:y1, x0:x1]))
    # height, width = img.shape
    # print(height, width)
    # for i in range(0,numcols):
    #     for j in range(0,numrows):
    #         image_tile.append(img[i * int(height/numrows):(i+1) * int(height/numrows), j * int(width/numcols):(j+1) * int(width/numcols)])
    return image_tile


def changed_pixels(curr_img, prev_img):
    h, w = curr_img.shape
    diff_image = np.zeros((h,w), np.uint8)
    for y in range(h):
        for x in range(w):
            if curr_img[y][x] != prev_img[y][x]:
                diff_image[y][x] = 255
    
    # cv2.imshow("curr_img", cv2.resize(curr_img, (320, 240), interpolation=cv2.INTER_NEAREST))
    # cv2.imshow("prev_img", cv2.resize(prev_img, (320, 240), interpolation=cv2.INTER_NEAREST))
    # cv2.imshow("diff", cv2.resize(diff_image, (320, 240), interpolation=cv2.INTER_NEAREST))
    # cv2.waitKey(0)
    return diff_image


if __name__=="__main__":
    main()