import cv2
import numpy as np
import os
import threading
import time
import util

from PIL import Image, ImageChops, ImageDraw, ImageGrab, ImageFilter


home = os.path.dirname(os.path.realpath(__file__))


class Stream:
    def __init__(self):
        self.frame = None

        self.frame_processor_thread = FrameProcessorThread(self)
        self.frame_processor_thread.daemon = True
        self.frame_processor_thread.start()

        self.frame_grabber_thread = FrameGrabberThread(self)
        self.frame_grabber_thread.daemon = True
        self.frame_grabber_thread.start()

        self.cap = cv2.VideoCapture('udp://@224.0.0.1:9999')

        self.frame_processor_thread.join()
        self.frame_grabber_thread.join()

        self.cap.release()
        cv2.destroyAllWindows()


class FrameGrabberThread(threading.Thread):
    def __init__(self, stream, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.stream = stream
        self.num = 0


    def run(self):
        while not hasattr(self.stream, 'cap'):
            time.sleep(0.01)
        print('FrameGrabber running')
        if not self.stream.cap.isOpened():
            print('VideoCapture not opened')
            exit(-1)

        while self.get_frame():
            pass


    #@util.time_this
    def get_frame(self):
        self.num += 1
        ret, frame = self.stream.cap.read()

        if not ret:
            print('frame empty')
            return False

        #if self.num % 30 == 0:
        self.stream.frame = frame
        return True


class FrameProcessorThread(threading.Thread):
    def __init__(self, stream, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.stream = stream


    def run(self):
        while True:
            try:
                if self.stream.frame:
                    pass
                else:
                    continue
            except ValueError:
                if self.stream.frame.any():
                    pass
                else:
                    continue

            print('frame')
            if not self.process_frame():
                break

    @util.time_this
    def process_frame(self):
            frame = self.stream.frame
            self.stream.frame = None
            #gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            #ret, bw = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
            #bw = gray.point(lambda x: 0 if x < 170 else 255, '1')
            flipped = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            img = Image.fromarray(flipped)
            img = img.filter(ImageFilter.FIND_EDGES)
            frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            #gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            #ret, bw = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
            #img.save(os.path.join('test', f'{x}.jpg'))
            cv2.imshow('image', frame)

            if cv2.waitKey(1)&0XFF == ord('q'):
                return False
            else:
                return True


if __name__ == '__main__':
    stream = Stream()
