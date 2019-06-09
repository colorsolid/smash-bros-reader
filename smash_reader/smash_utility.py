import cv2
from   datetime import datetime
import json
from   logger import log_exception
import matplotlib.pyplot as plt
import mss
import numpy as np
from   PIL import Image, ImageChops
import pytesseract
import random
import requests
from   skimage.measure import compare_ssim
import string
import subprocess
import os
import sys
import time

sys.excepthook = log_exception


output = True
def _print(*args, **kwargs):
    if output:
        args = list(args)
        args.insert(0, '<Utility>')
        print(*args, **kwargs)

BASE_DIR = os.path.realpath(os.path.dirname(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')

override_path = os.path.join(BASE_DIR, 'index.txt')
if os.path.isfile(override_path):
    with open(override_path, 'r') as infile:
        MONITOR_INDEX = int(infile.read())
else:
    MONITOR_INDEX = 1

COORDS = {
    'LOBBY': {
        'BASIC_ID': (145, 32, 321, 70),
        'FLAGS_ID': (394, 291, 1525, 433),
        'CARDS_ID': (671, 152, 1247, 188),
        'GAME_INFO': (302, 217, 1443, 253),
        'CHARACTER_TEMPLATE': (144, 126, 206, 218),
        'CARDS_SLICE_IDS': (0, 877, 1920, 878),
        'CARDS_SLICE_COLORS': (0, 813, 1920, 814),
        'PLAYER': {
            'TEAM_COLOR': (17, 458, 18, 459),
            'CHARACTER_NAME': (0, 369, 396, 423),
            'NAME': (129, 436, 389, 475),
            'NUMBER': (37, 441, 82, 471),
            'GSP': (131, 490, 384, 526)
        }
    },
    'GAME': {
        'TIMER_PREGAME': (1722, 61, 1798, 89),
        'TIMER_VISIBLE': (1703, 63, 1715, 95),
        'TIMER_MILLI': (
            (1823, 70, 1831, 92),
            (1850, 70, 1858, 92)
        ),
        'TIMER_MINUTE': (1675, 54, 1686, 91),
        'TIMES_UP': (465, 299, 1451, 409),
        'SUDDEN_DEATH': (340, 172, 1602, 345),
        'END_ID': (411, 462, 1481, 522),
        'PLAYER': {
            'INFO': {
                2: (712, 1451),
                3: (457, 1081, 1705),
                4: (491, 899, 1307, 1715)
            },
            'STOCK_TEMPLATE': (223, 1045, 221, 1059),
            'CHARACTER_TEMPLATE': (272, 950, 242, 1020),
            'NAME': (182, 1007, 0, 1025),
            'COLOR': (5, 1003, 4, 1004)
        }
    },
    'FINAL': {
        'ID': (
            (468, 49, 550, 296),
            (204, 388, 286, 635)
        ),
        'ID2': (1825, 0, 1864, 73),
        'VICTORY_TEAM': (745, 870, 833, 978),
        'VICTORY_PLAYER': (125, 168, 126, 169),
        '2ND_PLACE': (525, 982, 526, 983),
        '2ND_PLACE_2_PLAYER': (690, 984, 691, 985),
        '3RD_PLACE': (1072, 1003, 1073, 1004),
        '4TH_PLACE': (1492, 1013, 1493, 1014)
    }
}

folders = [f for f in os.listdir(TEMPLATES_DIR) if os.path.isdir(os.path.join(TEMPLATES_DIR, f))]
TEMPLATES = {f.upper():{} for f in folders}
for root, dirs, files in os.walk(TEMPLATES_DIR, topdown=False):
    for file in files:
        path = os.path.join(root, file)
        name = os.path.splitext(file)[0]
        _type = os.path.split(root)[1].upper()
        if _type in TEMPLATES:
            TEMPLATES[_type][name] = Image.open(path)
        else:
            TEMPLATES[_type] = {name: Image.open(path)}


#####################################################################
############################# DECORATORS ############################
#####################################################################

def time_this(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        duration = end_time - start_time
        dur_str = '{:.2f}'.format(duration)
        _print(f'function: {func.__name__}() executed in {dur_str} seconds')
        return result
    return wrapper


# Make sure function runs at least as long as the set interval
def pad_time(interval):
    def outer(func):
        def inner(*args, **kwargs):
            start_time = time.time()
            result = func(*args, **kwargs)
            end_time = time.time()
            duration = end_time - start_time
            delta = interval - duration
            if delta > 0:
                # print(f'padding {delta} seconds')
                time.sleep(delta)
            else:
                # print(f'detection has fallen behind by [{"{:.2f}".format(delta)}] seconds')
                pass
            return result
        return inner
    return outer




#####################################################################
########################## IMAGE CAPTURING ##########################
#####################################################################


def save_frames(vid_path, framerate=None):
    print('saving template in 5 seconds')
    time.sleep(5)
    vid_cap = cv2.VideoCapture(vid_path)
    success = True
    frame_index = 0
    while success:
        vid_cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        success, image = vid_cap.read()
        _print(f'Read frame {frame_index}: ', success)
        cv2.imwrite(f'frame{frame_index}.png', image)     # save frame as JPEG file
        frame_index += 30


# @time_this
def capture_screen(monitor_index=MONITOR_INDEX):
    with mss.mss() as sct:
        monitor_count = len(sct.monitors)
        if monitor_index > monitor_count:
            monitor_index = monitor_count
        monitor = sct.monitors[monitor_index]
        sct_img = sct.grab(monitor)
        pil_img = Image.frombytes('RGB', sct_img.size, sct_img.bgra, 'raw', 'BGRX')
        return pil_img


def capture_cards_id():
    coords = COORDS['LOBBY']['CARDS_ID']
    cap = capture_screen()
    crop = cap.crop(coords)
    if 'CARDS_ID' in TEMPLATES['LOBBY']:
        del TEMPLATES['LOBBY']['CARDS_ID']
    crop.save(os.path.join(TEMPLATES_DIR, 'lobby', 'CARDS_ID.png'))
    TEMPLATES['LOBBY']['CARDS_ID'] = crop




#####################################################################
########################## IMAGE PROCESSING #########################
#####################################################################


def read_image(image, config_type='basic'):
    configs = {
        'basic': '--psm 6 --oem 3',
        'gsp': '--psm 8 --oem 3 -c tessedit_char_whitelist=0123456789,',
        'player_number': '--psm 8 --oem 3 -c tessedit_char_whitelist=p1234'
    }
    text = pytesseract.image_to_string(image, config=configs[config_type])
    return text


def convert_to_bw(pil_img, threshold=127, inv=True):
    cv_img = np.array(pil_img)
    try:
        img_gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        if inv:
            method = cv2.THRESH_BINARY_INV
        else:
            method = cv2.THRESH_BINARY
        thresh, array_bw = cv2.threshold(img_gray, threshold, 255, method)
        pil_bw = Image.fromarray(array_bw)
        return pil_bw, array_bw
    except cv2.error:
        return pil_img, cv_img


def find_most_similar(sample, templates, thresh=0):
    high_sim = ['', 0]
    for template_name in templates:
        sim = avg_sim(sample, templates[template_name])
        if sim > high_sim[1]:
            high_sim = [template_name, sim]
            if thresh and sim > thresh:
                return high_sim
    return high_sim


def compare_chops(sample, template, true_color=False):
    if sample.size == template.size:
        copy1 = sample.resize((64, 64))
        copy2 = template.resize((64, 64))

        if not true_color:
            copy1, arr1 = convert_to_bw(copy1)
            copy2, arr2 = convert_to_bw(copy2)

        diff = ImageChops.difference(copy1, copy2)
        arr = np.asarray(diff)
        total = 0
        different = 0
        for row in arr:
            for pixel in row:
                total += 1
                if isinstance(pixel, (int, np.uint8)):
                    if pixel == 255:
                        different += 1
                else:
                    for color in pixel:
                        different += (color / 255)
        sim = ((1 - (different/total)) * 100)
        return sim
    return 0


def compare_skim(sample, template, true_color=False):
    if sample.size == template.size:
        copy1 = sample.resize((64, 64))
        copy2 = sample.resize((64, 64))

        if not true_color:
            try:
                sample = cv2.cvtColor(np.array(sample), cv2.COLOR_BGR2GRAY)
            except cv2.error:
                sample = np.array(sample)
            try:
                template = cv2.cvtColor(np.array(template), cv2.COLOR_BGR2GRAY)
            except cv2.error:
                template = np.array(template)
                # Image is already b&w

        sim, diff = compare_ssim(sample, template, full=True, multichannel=True)
        return sim * 100
    return 0


def area_sim(cap, screen, area):
    template = TEMPLATES[screen][area]
    coords = COORDS[screen][area]
    if not isinstance(coords[0], (list, tuple)):
        coords = [coords]
    high_sim = 0
    for coord in coords:
        crop = cap.crop(coord)
        sim = avg_sim(crop, template)
        if sim > high_sim:
            high_sim = sim
    return high_sim


def avg_sim(sample, template, true_color=False):
    comp_funcs = (compare_chops, compare_skim)
    sims = [comp_func(sample, template, true_color) for comp_func in comp_funcs]
    avg = sum(sims) / len(sims)
    return avg


COLORS = {
    'CARDS':{
        'RED': (250, 52, 52),
        'BLUE': (43, 137, 253),
        'YELLOW': (248, 182, 16),
        'GREEN': (35, 179, 73)
    },
    'RESULTS': {
        'RED': (240, 159, 163),
        'BLUE': (125, 206, 254),
        'YELLOW': (255, 244, 89),
        'GREEN': (141, 212, 114)
    }
}


def match_color(pixel=None, arr=[], mode=None):
    best_match = ('', 0)
    if not mode:
        _print('mode required for color match')
        return best_match
    if pixel:
        sample = [rgb for row in np.asarray(pixel) for rgb in row][0]
    elif any(arr):
        sample = arr
    else:
        _print('no sample')
        return best_match
    colors = COLORS[mode]
    for color_name in colors:
        diff = 0
        for sv, tv in zip(sample, colors[color_name]):
            diff += abs(sv - tv)
        sim = 100 - ((diff / 765) * 100)
        if sim > best_match[1]:
            best_match = (color_name, sim)
    return best_match


def filter_color(image, color):
    color = np.uint8([[color]])
    hsv = cv2.cvtColor(color, cv2.COLOR_RGB2HSV)
    darker = np.array([hsv[0][0][0] - 10, 50, 50])
    lighter = np.array([hsv[0][0][0] + 10, 360, 360])
    image = np.asarray(image)
    hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
    mask = cv2.inRange(hsv, darker, lighter)
    result = cv2.bitwise_and(image, image, mask=mask)
    return result


def rgb_to_hex(rgb):
    return '#%02x%02x%02x' % rgb


#####################################################################
################################ MISC ###############################
#####################################################################


def simplify_players(game):
    players = []
    for team in game['teams']:
        color = team['color']
        for player in team['players']:
            keys = list(player.keys())
            for key in keys:
                if not player[key]:
                    del player[key]
            player['color'] = color
            players.append(player)
    return players



def filter_game_data(game, mode):
    simple_game = {}
    if mode == 1:
        simple_game['players'] = simplify_players(game)
        simple_game['map'] = game['map']
        simple_game['team_mode'] = game['team_mode']
        simple_game['game_mode'] = game['mode']
        simple_game['cancelled'] = game['cancelled']
    if mode == 3:
        if not game['team_mode']:
            for team in game['teams']:
                simple_game['players'] = simplify_players(game)
            simple_game['start_time'] = -1
    if mode == 4:
        simple_game = {'end_time': -1}
    if mode == 5:
        simple_game = {'winning_team': game['winning_color']}
    return simple_game


def post_data(message='No message'):
    URL = 'http://localhost:8000/reader_info/'
    DATA = {
        'secret_code': 't7q72Uo_0vs{NKRmH=3g3apvsf3zoW!8,b6]nj)',
        'data': message
    }
    try:
        r = requests.post(url=URL, json=DATA)
        return r
    except requests.exceptions.ConnectionError:
        print('Unable to reach REST API')
        return None


def dump_image_data(arr):
    filepath = os.path.join(BASE_DIR, 'img_dump.json')
    if os.path.isfile(filepath):
        with open(filepath, 'r') as infile:
            data = json.load(infile)
    else:
        data = []
    data.append({time.time(): arr})
    with open(filepath, 'w+') as outfile:
        json.dump(data, outfile)


def clear_console():
    try:
        none = os.system('cls')
    except:
        pass
    try:
        none = os.system('clear')
    except:
        pass


def save_game_data(game):
    data = load_game_data()
    data.append(game)
    with open('games.json', 'w+') as outfile:
        json.dump(data, outfile, separators=(',',':'))


def load_game_data():
    path = os.path.join(BASE_DIR, 'games.json')
    if os.path.isfile(path):
        try:
            with open(path, 'r') as infile:
                return json.load(infile)
        except json.decoder.JSONDecodeError:
            pass
    return []


def save_settings(settings):
    print(settings)
    path = os.path.join(BASE_DIR, 'settings.json')
    with open(path, 'w+') as outfile:
        json.dump(settings, outfile)


def load_settings():
    path = os.path.join(BASE_DIR, 'settings.json')
    if os.path.isfile(path):
        with open(path, 'r') as infile:
            settings = json.load(infile)
    else:
        settings = {
            'monitor_index': 1,
            'game_output': True,
            'watcher_output': True,
            'utility_output': True
        }
        save_settings(settings)
    return settings


def send_command():
    # subprocess.Popen()
    # PIGPIO_ADDR=169.254.183.202
    pass


def random_str(l=10):
    """Generate a random string of letters, digits and special characters """
    password_characters = string.ascii_letters + string.digits
    return ''.join(random.choice(password_characters) for i in range(l))
