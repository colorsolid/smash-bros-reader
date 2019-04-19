import cv2
import multiprocessing
import numpy as np
import os
#import select
import socket
#import struct
#import threading
import time

#from matplotlib import pyplot as plt
from PIL import Image, ImageChops, ImageDraw, ImageGrab, ImageFilter



cap = cv2.VideoCapture('udp://@224.0.0.1:9999', cv2.CAP_FFMPEG)
if not cap.isOpened():
    print('VideoCapture not opened')
    exit(-1)

x = 0
while True:
    ret, frame = cap.read()

    if not ret:
        print('frame empty')
        break

    flipped = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    img = Image.fromarray(flipped)
    #img = img.filter(ImageFilter.EDGE_ENHANCE_MORE)
    #frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    #img.save(os.path.join('test', f'{x}.jpg'))
    cv2.imshow('image', frame)
    x += 1

    if cv2.waitKey(1)&0XFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
