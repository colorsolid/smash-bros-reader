import cv2
import numpy as np
import os
import pytesseract as pyt
import re
import sys
import time

from datetime import datetime
from PIL import ImageGrab, Image, ImageDraw

COORDS = {
    'lobby-id-basic': (145, 32, 321, 70),
    'lobby-id-cards': (671, 152, 1247, 188),
    'lobby-flag-screen-id': (394, 291, 1525, 433),
    'lobby-map': (1, 131, 255, 264),
    'lobby-mode': (246, 211, 285, 254),
    'lobby-portrait-upper-slice': (1, 813, 1920, 814),
    'fight-id': (1809, 60, 1872, 104),
    'timer-num-small': (1840, 62, 1869, 101),
    'timer-num-large': (1719, 38, 1803, 105)
}


def main():
    home_dir = os.path.dirname(os.path.realpath(__file__))
    img_names = os.listdir(os.path.join(home_dir, 'frames'))
    img_names.sort(key=lambda img_name: int(re.search('\d+', img_name).group()))
    print('"q" to quit')
    while True:
        search_term = input('img>: ')
        if search_term == 'q':
            break
        img_name = next((img_name for img_name in img_names if search_term in img_name), None)
        if img_name:
            img_path = os.path.join(home_dir, 'frames', img_name)
            img = cv2.imread(img_path, 0)
            frame = Frame(img)
        else:
            print('No image found')


def time_this(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        duration = '{:.2f}'.format(end_time - start_time)
        print(f'function: {func.__name__} executed in {duration} seconds')
        return result
    return wrapper


class Frame:
    def __init__(self, img):
        self.img = img
        self.determine_type()


    def crop(self, area_name, save_location=None):
        cropped_image = self.img.crop(COORDS[area_name])
        if save_location:
            cropped_image.save(save_location)
        return cropped_image


    #@time_this
    def determine_type(self):
        ids = ['lobby-id-basic', 'fight-id']
        text = ''
        for id in ids:
            img_crop = self.crop(id)
            if id in ['fight-id']:
                print('reading number')
                text = read_numbers(img_crop)
            else:
                text = pyt.image_to_string(img_crop).lower()
            if text:
                print(text)
                break


    def find_lobby_cards(self):
        left_edges = []
        upper_slice = crop(self.img, 'lobby-portrait-upper-slice')
        lower_slice = crop(self.img, 'lobby-portrait-lower-slice')
        upper_arr = np.asarray(upper_slice)
        lower_arr = np.asarray(lower_slice)
        in_card = False
        threshold = 10
        for row in upper_arr:
            for i, pixel in enumerate(row):
                if in_card:
                    if np.all(lower_arr[0][i] < threshold):
                        in_card = False
                else:
                    if np.all(pixel < threshold):
                        in_card = True
                        left_edges.append(i)
        return left_edges


def save_frames(vid_path, framerate=None):
    vid_cap = cv2.VideoCapture(vid_path)
    success = True
    frame_index = 0
    while success:
        vid_cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        success, image = vid_cap.read()
        print(f'Read frame {frame_index}: ', success)
        cv2.imwrite(f'frame{frame_index}.jpg', image)     # save frame as JPEG file
        frame_index += 30


@time_this
def read_numbers(img):
    return pyt.image_to_string(img, config='outputbase digits')


def convert_to_bw(pil_img):
    cv_img = np.array(pil_img)
    img_gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    thresh, img_bw = cv2.threshold(img_gray, 251, 255, cv2.THRESH_BINARY_INV)
    pil_bw = Image.fromarray(img_bw)
    ImageDraw.floodfill(pil_bw, xy=(1, 1), value=0)
    return pil_bw


if __name__ == '__main__':
    #main()
    while True:
        dt = datetime.fromtimestamp(time.time())
        t = dt.strftime('%H.%M.%S.%f')
        img = ImageGrab.grab(COORDS['lobby-flag-screen-id'])
        img.show()
        bw = convert_to_bw(img)
        #text = read_numbers(bw)
        #name = f'{text}-{t}.tif'
        #bw.save(os.path.join('timer', name))
        text = pyt.image_to_string(bw)
        print(text)
        break
        #frame = Frame(img)

    #print(pyt.image_to_string(crop(r'frames\frame90.jpg', 'test')))
    #crop(r'frames\frame69210.jpg', 'lobby-mode', 'time.jpg')
