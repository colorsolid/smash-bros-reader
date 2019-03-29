import cv2
import numpy as np
import pytesseract as pyt
import time

from PIL import ImageGrab, ImageDraw, Image


coords = (394, 291, 1525, 433)

def convert_to_bw(pil_img):
    cv_img = np.array(pil_img)
    img_gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    thresh, img_bw = cv2.threshold(img_gray, 251, 255, cv2.THRESH_BINARY_INV)
    pil_bw = Image.fromarray(img_bw)
    ImageDraw.floodfill(pil_bw, xy=(1, 1), value=0)
    return pil_bw


while True:
    screen = ImageGrab.grab()
    bw = convert_to_bw(screen)
    bw.show()
    total = 0
    black = 0
    arr = np.asarray(bw)
    for row in arr:
        for pixel in row:
            total += 1
            if pixel == 255:
                black += 1
    print(black)
    if ((black/total) * 100) > 95:
        print('black')
        while ((black/total) * 100) > 95:
            time.sleep(0.1)
        break
    time.sleep(0.5)

print('free')

time.sleep(3)
img = ImageGrab.grab()
crop = ImageGrab.grab(coords)
print(pyt.image_to_string(convert_to_bw(crop)))
img.save('screen.jpg')
crop.save('crop.jpg')
