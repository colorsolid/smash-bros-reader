import argparse
import cv2
import difflib
import json
import matplotlib.pyplot as plt
import mss
import numpy as np
import os
import re
import requests
import select
import smash_game
import smash_utility as ut
import socket
import struct
import threading

from queue import Empty, Queue

#from matplotlib import pyplot as plt
from PIL import Image, ImageChops, ImageDraw


BASE_DIR = os.path.realpath(os.path.dirname(__file__))
CAPTURES_DIR = os.path.join(BASE_DIR, 'captures')
if not os.path.isdir(CAPTURES_DIR):
    os.mkdir(CAPTURES_DIR)


def test_pixel():
    img = Image.open('1560221662.467294.png')
    img = ut.filter_color2(img, (0, 10))
    p = plt.imshow(img)
    plt.show()


def test_stencil():
    img = Image.open('1560219739.917792.png')
    ut.stencil(img)


def test_game_data():
    with open('game_state.json', 'r') as infile:
        game = json.load(infile)
    ut.filter_game_data(game, 1)


def req(message='No message'):
    URL = 'http://localhost:8000/reader_info/'
    DATA = {
        'secret_code': 'Mj76uiJ*(967%GVr57UNJ*^gBVD#W4gJ)ioM^)',
        'data': message
    }
    r = requests.post(url = URL, json = DATA)
    return r


class KeyThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super().__init__()

        self.key = keyboard.KeyCode(char='g')


    def run(self):
        with keyboard.Listener(on_press=self.on_press) as listener:
            listener.join()


    def on_press(self, key):
        if key == self.key:
            print('test')


def start_key_thread():
    thread = KeyThread()
    thread.daemon = True
    thread.start()



def fight_tester():
    captures = os.listdir(CAPTURES_DIR)
    get_fight_num = lambda f: re.match('\d+', f).group()
    fight_nums = list({get_fight_num(f) for f in captures})
    fight_nums.sort(key=lambda n: int(n))
    # n = fight_nums[int(random.random() * len(fight_nums))]
    # n = '0001'
    modes = {}
    for i, n in enumerate(fight_nums[16:]):
        print(f'{"*" * 80}\n{n}')
        card_screen = Image.open(os.path.join(CAPTURES_DIR, n + '.2.LOBBY_CARDS.png'))
        fight_start_screen = Image.open(os.path.join(CAPTURES_DIR, n + '.3.FIGHT_START.png'))
        # fight_end_screen = Image.open(os.path.join(CAPTURES_DIR, n + '.4.FIGHT_END.png'))
        # try:
        #     fight_results_screen = Image.open(os.path.join(CAPTURES_DIR, n + '.5.FIGHT_RESULTS_SOLO.png'))
        # except FileNotFoundError:
        #     fight_results_screen = Image.open(os.path.join(CAPTURES_DIR, n + '.5.FIGHT_RESULTS_TEAM.png'))


        game = smash_game.Game(1)
        game.read_card_screen(card_screen)
        if game.mode in modes:
            modes[game.mode].append(i)
        else:
            modes[game.mode] = [i]
        break
    for mode in modes:
        print(f'{mode}: {modes[mode]}')
        game.read_start_screen(fight_start_screen)
        print(game.serialize(images_bool=False))
        # game.fix_colors(fight_start_screen)
        # game.read_end_screen(fight_end_screen)
        # game.read_results_screen(fight_results_screen)
        # print(str(game))
        # with open('game.json', 'w+') as outfile:
        #    json.dump(game.serialize(), outfile, separators=(',',':'))


def crop_char_lobby():
    cap = ut.capture_screen()
    game = smash_game.Game(1)
    game.player_count = 4
    game.read_cards(cap)


def crop_char_game():
    cap = ut.capture_screen()
    game = smash_game.Game(1)
    game.player_count = 3
    name_images = game.get_character_name_game(cap)
    for img in name_images:
        bw, _ = ut.convert_to_bw(img)
        name_as_read = ut.read_image(bw).lower()
        name = difflib.get_close_matches(name_as_read, smash_game.CHARACTER_NAMES, n=1)
        print(name)


def filter():
    plt.ion()
    while True:
        cap = ut.capture_screen()
        img = ut.filter_color(cap, [236, 236, 236])
        plt.imshow(img)
        plt.pause(0.001)
        plt.show()


def cropper(coord_name, name=None):
    coords = ut.COORDS['FINAL'][coord_name]
    capture = ut.capture_screen()
    crop = capture.crop(coords)
    if name:
        crop.save(f'{name}.png')
    else:
        return np.asarray(crop)
        # crop.show()


def capture_screen():
    with mss.mss() as sct:
    # Get rid of the first, as it represents the "All in One" monitor:
        #for num, monitor in enumerate(sct.monitors[1:], 1):
        monitor = sct.monitors[1]
        # Get raw pixels from the screen
        sct_img = sct.grab(monitor)

        # Create the Image
        img = Image.frombytes('RGB', sct_img.size, sct_img.bgra, 'raw', 'BGRX')
        # The same, but less efficient:
        # img = Image.frombytes('RGB', sct_img.size, sct_img.rgb)
        num = 0
        name = os.path.join(home, 'screens', f'{num}.png')
        while os.path.isfile(name):
            num += 1
            name = os.path.join(home, 'screens', f'{num}.png')
        return img


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


def thread_test():
    main_queue = Queue()
    processing_queue = Queue()

    processing_thread = ImageProcessingThread(main_queue, processing_queue)
    processing_thread.daemon = True
    processing_thread.start()

    print('test')

    get_stream_data(main_queue, processing_queue)


def ocr_test():
    # construct the argument parse and parse the arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--image", required=True,
    	help="path to input image to be OCR'd")
    ap.add_argument("-p", "--preprocess", type=str, default="thresh",
    	help="type of preprocessing to be done")
    args = vars(ap.parse_args())

    # load the example image and convert it to grayscale
    image = cv2.imread(args["image"])
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # check to see if we should apply thresholding to preprocess the
    # image
    if args["preprocess"] == "thresh":
    	gray = cv2.threshold(gray, 0, 255,
    		cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

    # make a check to see if median blurring should be done to remove
    # noise
    elif args["preprocess"] == "blur":
    	gray = cv2.medianBlur(gray, 3)

    # write the grayscale image to disk as a temporary file so we can
    # apply OCR to it
    #filename = "{}.png".format(os.getpid())
    #cv2.imwrite(filename, gray)

    pil_gray = Image.fromarray(gray)

    # load the image as a PIL/Pillow image, apply OCR, and then delete
    # the temporary file
    text = pytesseract.image_to_string(pil_gray)
    #os.remove(filename)
    print(text)

    # show the output images
    cv2.imshow("Image", image)
    cv2.imshow("Output", gray)
    cv2.waitKey(0)


if __name__ == '__main__':
    #ocr_test()
    #fight_tester()
    #test_game_data()
    #test_stencil()
    test_pixel()
    pass
