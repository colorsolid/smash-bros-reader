import cv2
import numpy as np
import pytesseract as pyt
import sys
import time

from PIL import ImageGrab, ImageDraw, Image

COORDS = (
    (282, 887, 430, 920),
    (245, 805, 392, 887)
)

def convert_to_bw(pil_img):
    cv_img = np.array(pil_img)
    img_gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(img_gray, (5, 5), 0)
    thr, img_bw = cv2.threshold(blur, 127, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    pil_bw = Image.fromarray(img_bw)
    ImageDraw.floodfill(pil_bw, xy=(1, 1), value=0)
    return pil_bw

    #filename = input('>: ')
    #bw = convert_to_bw(Image.open(filename))
    bw = convert_to_bw(ImageGrab.grab(coords))
    bw.show()
    return pil_bw


def crop(img, coords, save_location=None):
    print(coords)
    cropped_image = img.crop(coords)
    if save_location:
        cropped_image.save(save_location)
    return cropped_image


filename = sys.argv[1]

img = Image.open(filename)
img = np.asarray(img)
img = cv2.bilateralFilter(img,9,75,75)
img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
img = Image.fromarray(img)
img.save('large.jpg')
#img.show()
bw = convert_to_bw(img)
#bw.show()
crop = crop(bw, COORDS[1])
crop.show()

print(pyt.image_to_string(crop, config='digits'))
