import cv2
import numpy as np
import os
import select
import socket
import struct
import threading
import time

from PIL import Image, ImageChops, ImageDraw, ImageGrab
from queue import Queue, Empty


home = os.path.dirname(os.path.realpath(__file__))



class FrameReader:
    def __init__(self):
        self.queue = Queue()

        self.frame_thread = FrameProcessingThread(self)
        self.frame_thread.daemon = True
        self.frame_thread.start()

        self.cap = cv2.VideoCapture('udp://224.0.0.1:4242', cv2.CAP_FFMPEG)


        self.frame_thread.join()

        self.cap.release()
        cv2.destroyAllWindows()


class FrameProcessingThread(threading.Thread):
    def __init__(self, reader, *args, **kwargs):
        super().__init__()

        self.reader = reader


    def run(self):
        while not hasattr(self.reader, 'cap'):
            time.sleep(0.01)
        print('run')
        if not self.reader.cap.isOpened():
            print('VideoCapture not opened')
            exit(-1)

        while True:
            ret, frame = self.reader.cap.read()

            if not ret:
                print('frame empty')
                break

            flipped = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            img = Image.fromarray(flipped)
            #img.save(os.path.join('test', f'{x}.jpg'))
            cv2.imshow('image', frame)

            if cv2.waitKey(1)&0XFF == ord('q'):
                break


    def get_queue_item(self):
        try:
            item = self.queue.get(block=False)
            return item
        except Empty:
            return None


if __name__ == '__main__':
    frame_reader = FrameReader()
