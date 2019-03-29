import cv2
import numpy as np
import os
import select
import socket
import struct
import threading

from queue import Empty, Queue

#from matplotlib import pyplot as plt
from PIL import Image, ImageChops, ImageDraw, ImageGrab


home = os.path.dirname(os.path.realpath(__file__))


def get_stream():
    port = 9999  # where do you expect to get a msg?
    bufferSize = 2048 # whatever you need

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('', port))
    s.setblocking(0)

    if True:
        result = select.select([s],[],[])
        msg = result[0][0].recv(bufferSize)
        print(msg)

        cap = ImageGrab.grab()

        cv2.imdecode(cap, flags=1)


def get_stream2():
    HOST = ''
    PORT = 9999

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print('Socket created')

    s.bind((HOST, PORT))
    print('Socket bind complete')

    s.listen(10)
    print('Socket now listening')

    conn, addr = s.accept()

    while True:
        data = conn.recv(8192)
        nparr = np.fromstring(data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        cv2.imshow('frame', frame)
        time.sleep(2)


def get_stream3():
    MCAST_GRP = '224.1.1.1'
    MCAST_PORT = 9999
    IS_ALL_GROUPS = True

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if IS_ALL_GROUPS:
        # on this port, receives ALL multicast groups
        sock.bind(('', MCAST_PORT))
    else:
        # on this port, listen ONLY to MCAST_GRP
        sock.bind((MCAST_GRP, MCAST_PORT))
    mreq = struct.pack("4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)

    sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

    while True:
        print(sock.recv(10240))


def get_stream_data(main_queue, image_queue):
    print('Getting stream data')
    cap = cv2.VideoCapture('udp://224.0.0.1:2424', cv2.CAP_FFMPEG)
    print(cap)
    if not cap.isOpened():
        print('VideoCapture not opened')
        exit(-1)
    x = 0
    while True:
        print('cap')
        image_queue.put(cap)
        print('put')
        item = get_queue(main_queue)
        if item == 'end':
            break


    cap.release()
    cv2.destroyAllWindows()


def convert_to_bw(pil_img, threshold=127):
    cv_img = np.array(pil_img)
    img_gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    thresh, array_bw = cv2.threshold(img_gray, threshold, 255, cv2.THRESH_BINARY_INV)
    pil_bw = Image.fromarray(array_bw)
    ImageDraw.floodfill(pil_bw, xy=(1, 1), value=0)
    return pil_bw, array_bw


def compare():
    imgs = os.listdir(os.path.join(home, 'flags'))
    [print(f'{str(i+1).rjust(2)}. {img}') for i, img in enumerate(imgs)]

    #x = 0
    while True:
        first = int(input('one>: '))
        img1 = Image.open(os.path.join(home, 'flags', imgs[first-1]))
        print(img1)

        second = int(input('two>: '))
        img2 = Image.open(os.path.join(home, 'flags', imgs[second-1]))
        print(img2)

        #small, large = sorted([img1, img2], key=lambda img: img.size[0])

        copy1 = img1.resize((64, 64))
        copy2 = img2.resize((64, 64))

        bw1, arr1 = convert_to_bw(copy1)
        bw2, arr2 = convert_to_bw(copy2)

        diff = ImageChops.difference(bw1, bw2)
        diff.show()
        arr = np.asarray(diff)
        total = 0
        different = 0
        for row in arr:
            for pixel in row:
                total += 1
                if pixel == 255:
                    different += 1
        sim = ((1 - (different/total)) * 100)
        print(sim)
        if sim < 98:
            print('different flag')
        else:
            print('same flag')

        #diff.save(f'diff-{x}.jpg')
        #x += 1


def get_queue(queue):
    try:
        item = queue.get(block=False)
        return item
    except Empty:
        return None


class ImageProcessingThread(threading.Thread):
    def __init__(self, main_queue, queue):
        super().__init__()

        self.queue = queue
        self.main_queue = main_queue

        self.x = 0

        print('Image processing thread started')


    def run(self):
        while True:
            cap = get_queue(self.queue)
            if cap:
                self.process_frame(cap)


    def process_frame(self, cap):
        ret, frame = cap.read()

        if not ret:
            print('frame empty')
            main_queue.put('end')

        flipped = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        img = Image.fromarray(flipped)
        img.save(os.path.join('test', f'{self.x}.jpg'))
        self.x += 1
        #cv2.imshow('image', frame)

        if cv2.waitKey(1)&0XFF == ord('q'):
            main_queue.put('end')
            pass


if __name__ == '__main__':

    main_queue = Queue()
    processing_queue = Queue()

    processing_thread = ImageProcessingThread(main_queue, processing_queue)
    processing_thread.daemon = True
    processing_thread.start()

    print('test')

    get_stream_data(main_queue, processing_queue)
