import asyncio
import cv2
import numpy as np
import os
import threading
import time

from PIL import Image, ImageChops, ImageDraw, ImageGrab, ImageFilter


home = os.path.dirname(os.path.realpath(__file__))


class Stream(threading.Thread):
    def __init__(self, loop, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.frame = None


    def run(self):
        asyncio.set_event_loop(loop)
        loop.run_forever()


    def capture(self):
        print('capturing')
        self.cap = cv2.VideoCapture('udp://@224.0.0.1:9999')
        print('done capturing')
        self.cap.release()
        cv2.destroyAllWindows()


async def frame_grabber(stream):
    print('frame grabber running')
    while not stream.cap.isOpened():
        time.sleep(1)
        print('VideoCapture not opened')
        #exit(-1)

    num = 0
    while True:
        num += 1
        ret, frame = stream.cap.read()

        if not ret:
            print('frame empty')
            break

        if num % 30 == 0:
            num = 0
            stream.frame = frame


async def frame_processor(stream):
    print('processing')
    while True:
        try:
            if stream.frame:
                pass
            else:
                continue
        except ValueError:
            if stream.frame.any():
                pass
            else:
                continue

        print('frame')
        frame = stream.frame
        stream.frame = None

        flipped = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        img = Image.fromarray(flipped)
        img = img.filter(ImageFilter.EDGE_ENHANCE_MORE)
        frame = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        #img.save(os.path.join('test', f'{x}.jpg'))
        cv2.imshow('image', frame)

        if cv2.waitKey(1)&0XFF == ord('q'):
            break


if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    stream = Stream(loop)
    stream.daemon = True
    stream.start()

    while not hasattr(stream, 'cap'):
        time.sleep(0.01)

    print(stream.cap.isOpened())

    loop.call_soon_threadsafe(frame_grabber, stream)
    loop.call_soon_threadsafe(frame_processor, stream)

    def test():
        try:
            asyncio.ensure_future(frame_grabber(stream))
            asyncio.ensure_future(frame_processor(stream))
        except KeyboardInterrupt:
            pass
        finally:
            loop.close()
    #test()
