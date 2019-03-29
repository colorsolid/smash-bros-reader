import cv2
import multiprocessing
import numpy as np
import os
import select
import socket
import struct
#import threading
import time

#from matplotlib import pyplot as plt
from PIL import Image, ImageChops, ImageDraw, ImageGrab



cap = cv2.VideoCapture('udp://224.0.0.1:4242', cv2.CAP_FFMPEG)
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
    #img.save(os.path.join('test', f'{x}.jpg'))
    cv2.imshow('image', frame)
    x += 1

    if cv2.waitKey(1)&0XFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
