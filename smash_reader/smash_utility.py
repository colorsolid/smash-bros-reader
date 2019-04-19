import cv2
import mss
import numpy as np
from   PIL import Image, ImageChops
from   skimage.measure import compare_ssim
import os
import time



def time_this(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        duration = end_time - start_time
        dur_str = '{:.2f}'.format(duration)
        print(f'function: {func.__name__} executed in {dur_str} seconds')
        return result, duration
    return wrapper


# Make sure function runs at least as long as the set interval
def pad_time(interval):
    def outer(func):
        def inner(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            duration = end_time - start_time
            delta = interval - duration
            if delta > 0:
                # print(f'padding {delta} seconds')
                time.sleep(delta)
            else:
                print(f'detection has fallen behind by [{"{:.2f}".format(delta)}] seconds')
            return result
        return inner
    return outer


def save_frames(vid_path, framerate=None):
    vid_cap = cv2.VideoCapture(vid_path)
    success = True
    frame_index = 0
    while success:
        vid_cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        success, image = vid_cap.read()
        print(f'Read frame {frame_index}: ', success)
        cv2.imwrite(f'frame{frame_index}.png', image)     # save frame as JPEG file
        frame_index += 30


def capture_screen():
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        sct_img = sct.grab(monitor)
        pil_img = Image.frombytes('RGB', sct_img.size, sct_img.bgra, 'raw', 'BGRX')
        return pil_img


def convert_to_bw(pil_img, threshold=127):
    cv_img = np.array(pil_img)
    img_gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    thresh, array_bw = cv2.threshold(img_gray, threshold, 255, cv2.THRESH_BINARY_INV)
    pil_bw = Image.fromarray(array_bw)
    return pil_bw, array_bw


def compare_chops(sample, template):
    if sample.size == template.size:
        copy1 = sample.resize((64, 64))
        copy2 = template.resize((64, 64))

        bw1, arr1 = convert_to_bw(copy1)
        bw2, arr2 = convert_to_bw(copy2)

        diff = ImageChops.difference(bw1, bw2)
        arr = np.asarray(diff)
        total = 0
        different = 0
        for row in arr:
            for pixel in row:
                total += 1
                if pixel == 255:
                    different += 1
        sim = ((1 - (different/total)) * 100)
        return sim
    return 0


def compare_skim(sample, template):
    if sample.size == template.size:
        copy1 = sample.resize((64, 64))
        copy2 = sample.resize((64, 64))

        gray1 = cv2.cvtColor(np.array(sample), cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(np.array(template), cv2.COLOR_BGR2GRAY)

        sim, diff = compare_ssim(gray1, gray2, full=True)
        return sim * 100
    return 0


def avg_sim(sample, template):
    comp_funcs = (compare_chops, compare_skim)
    sims = [comp_func(sample, template) for comp_func in comp_funcs]
    avg = sum(sims) / len(sims)
    return avg
