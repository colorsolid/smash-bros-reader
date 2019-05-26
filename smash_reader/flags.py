import cv2
import datetime
import numpy as np
import os
#import pytesseract as pyt
import time

from datetime import datetime
from PIL import Image, ImageGrab, ImageDraw, ImageChops


COORDS = {
    'lobby-flag-screen-id': (379, 281, 1534, 445),
    'lobby-flag-screen-player-markers': (70, 820, 1800, 821),
    'flag-areas': (
        [(763, 528, 1156, 792)],
        [(472, 531, 857, 788), (1062, 531, 1447, 788)],
        [(327, 531, 682, 768), (782, 531, 1137, 768), (1237, 531, 1592, 768)],
        [(273, 540, 582, 745), (627, 540, 936, 745), (981, 540, 1290, 745), (1335, 540, 1644, 745)]
    )
}

HOME_DIR = os.path.dirname(os.path.realpath(__file__))
FLAG_DIR = os.path.join(HOME_DIR, 'flags')


###########################################################
########################### Main ##########################
###########################################################


def main():
    print('Starting')
    flags_dir = os.path.join(HOME_DIR, 'flags')
    if not os.path.isdir(flags_dir):
        os.mkdir(flags_dir)
    flag_list = []
    for root, dirs, files in os.walk(flags_dir):
        for name in files:
            folder_index = int(os.path.split(root)[1])
            if folder_index == len(flag_list):
                flag_list.append([name])
            else:
                flag_list[folder_index].append(name)
    cooldown = 0
    notif = False
    while True:
        if cooldown:
            cooldown -= 1
            time.sleep(1)
        elif is_flag_screen():
            notif = False
            print('Flag screen detected')
            img = ImageGrab.grab()
            img.save(os.path.join(HOME_DIR, 'screen.jpg'))
            flags = []
            cooldown = 20
            count = count_markers()
            if count > 0:
                count -= 1
            flag_areas = COORDS['flag-areas'][count]
            for i, area in enumerate(flag_areas):
                flag = read_flag(i, area)
                if not flags:
                    flags.append(flag)
                else:
                    if not any([image_similarity(flag, _flag) for _flag in flags]):
                        flags.append(flag)
            for flag in flags:
                name = new_flag(flag, flag_list)
                if name:
                    print(f'New flag: {name}')
        else:
            if not notif:
                print('Waiting for flag screen')
                notif = True
        time.sleep(0.01)
        break


###########################################################
######################### Utility #########################
###########################################################


def time_this(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        duration = '{:.2f}'.format(end_time - start_time)
        print(f'function: {func.__name__} executed in {duration} seconds')
        return result
    return wrapper


def new_flag(flag, flag_list):
    size = flag.size
    size_str = f'{size[0]}x{size[1]}'
    name = f'{size_str}.tif'
    if flag_list:
        for i, group in enumerate(flag_list):
            path = os.path.join(FLAG_DIR, str(i))
            _flag = Image.open(os.path.join(path, group[0]))
            if image_similarity(_flag, flag):
                if name in group:
                    return None
                else:
                    group.append(name)
                    if not os.path.isdir(path):
                        os.mkdir(path)
                    flag.save(os.path.join(path, name))
                    return f'{i}\\{name}'
    path = os.path.join(FLAG_DIR, str(len(flag_list)))
    flag_list.append([name])
    if not os.path.isdir(path):
        os.mkdir(path)
    flag.save(os.path.join(path, name))
    return f'{str(len(flag_list))}\\{name}'


###########################################################
########################## Image ##########################
###########################################################


#@time_this
def is_flag_screen():
    screen_crop = ImageGrab.grab(COORDS['lobby-flag-screen-id'])
    img_template = Image.open(os.path.join(HOME_DIR, 'template.jpg'))
    if image_similarity(screen_crop, img_template):
        return True
    else:
        return False


#@time_this
def convert_to_bw(pil_img, threshold=127):
    cv_img = np.array(pil_img)
    img_gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    thresh, array_bw = cv2.threshold(img_gray, threshold, 255, cv2.THRESH_BINARY_INV)
    pil_bw = Image.fromarray(array_bw)
    ImageDraw.floodfill(pil_bw, xy=(1, 1), value=0)
    return pil_bw, array_bw


#@time_this
def count_markers():
    img = ImageGrab.grab(COORDS['lobby-flag-screen-player-markers'])
    bw_img, bw_arr = convert_to_bw(img)
    skip = 0
    markers = 0
    for i, pixel in enumerate(bw_arr[0]):
        if skip:
            skip -= 1
            continue
        if pixel == 0:
            markers += 1
            skip = 100
    return markers


#@time_this
def read_flag(i, area):
    img = ImageGrab.grab(area)
    dt = datetime.fromtimestamp(time.time())
    t = dt.strftime('%Y_%m_%d-%H.%M.%S')
    name = f'{t}-{i}.tif'
    flag_dir = os.path.join(HOME_DIR, 'flags')
    if not os.path.isdir(flag_dir):
        os.mkdir(flag_dir)
    return img


def image_similarity(img1, img2, min_sim=90):
    thumb_img1 = img1.resize((64, 64))
    thumb_img2 = img2.resize((64, 64))
    bw1, arr1 = convert_to_bw(thumb_img1)
    bw2, arr2 = convert_to_bw(thumb_img2)

    bw1.show()
    bw2.show()

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
    return sim > min_sim


###########################################################
######################### Launch ##########################
###########################################################


if __name__ == '__main__':
    main()
