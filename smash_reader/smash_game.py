import copy
import difflib
import json
import numpy as np
import os
from   PIL import Image
import re
import smash_utility as ut
import threading
import time


output = True
def _print(*args, **kwargs):
    if output:
        args = list(args)
        args.insert(0, '<Game>')
        print(*args, **kwargs)


CARD_WIDTH = 398
STOCK_SPACING = 26

with open('fighter_list.json', 'r') as infile:
    CHARACTER_NAMES = json.load(infile)
CHARACTER_NAMES = [name.lower() for name in CHARACTER_NAMES]


class ImageProcessor(threading.Thread):
    def __init__(self):
        pass


class Player:
    def __init__(self):
        self.player_name_image = []
        self.character_name = ''
        self.number = 0
        self.gsp = 0
        self.stock_template_image = []
        self.stock_count = 0


    def serialize(self, images_bool=True):
        _copy = copy.copy(self)
        img = _copy.player_name_image.tolist()
        for i, row in enumerate(img):
            img[i] = [int(bool(pixel)) for pixel in img[i]]
        if not images_bool:
            _copy.player_name_image = None
            _copy.stock_template_image = None
        else:
            if len(_copy.player_name_image):
                _copy.player_name_image = _copy.player_name_image.tolist()
            if len(_copy.stock_template_image):
                _copy.stock_template_image = _copy.stock_template_image.tolist()
        return _copy.__dict__


    def read_card(self, card):
        self.get_character_name(card)
        self.crop_player_name(card)
        self.read_number(card)
        self.read_gsp(card)


    # @ut.time_this
    def get_character_name(self, card):
        crop = card.crop(ut.COORDS['LOBBY']['PLAYER']['CHARACTER_NAME'])
        pil, arr = ut.convert_to_bw(crop, 240)
        # template_name, sim = find_most_similar(pil, TEMPLATES['CHARACTER_NAMES'])
        sim = 0
        if sim > 95:
            self.character_name = template_name
        else:
            name_as_read = ut.read_image(pil).lower()
            name = difflib.get_close_matches(name_as_read, CHARACTER_NAMES, n=1)
            if len(name):
                name = name[0]
                self.character_name = name
            else:
                self.character_name = '...'
                template, sim = ut.find_most_similar(pil, ut.TEMPLATES['CHARACTER_NAMES'], thresh=95)
                if sim >= 95:
                    self.character_name = template.split('-')[0]
                else:
                    template, sim = ut.find_most_similar(pil, ut.TEMPLATES['UNREADABLE'], thresh=95)
                    if sim < 95:
                        nums = list(ut.TEMPLATES['UNREADABLE'].keys())
                        if len(nums):
                            nums.sort(key=lambda num: int(num), reverse=True)
                            num = int(nums[0]) + 1
                        else:
                            num = 1
                        filename = f'{num}.png'
                        ut.TEMPLATES['UNREADABLE'][num] = pil
                        pil.save(os.path.join(ut.TEMPLATES_DIR, 'unreadable', filename))
            _print(f'{name_as_read.rjust(30)} --> {self.character_name}')


    # @ut.time_this
    def crop_player_name(self, card):
        crop = card.crop(ut.COORDS['LOBBY']['PLAYER']['NAME'])
        img, self.player_name_image = ut.convert_to_bw(crop, 20, False)
        # img.show()


    # @ut.time_this
    def read_number(self, card):
        crop = card.crop(ut.COORDS['LOBBY']['PLAYER']['NUMBER'])
        # crop.save(f'{time.time()}.png')
        templates = {t:ut.TEMPLATES['LOBBY'][t] for t in ut.TEMPLATES['LOBBY'] if re.match('P\d+', t)}
        template_name, sim = ut.find_most_similar(crop, templates)
        num = int(os.path.splitext(template_name)[0].split('P')[1])
        # pil, arr = convert_to_bw(crop, 1, False)
        # num = read_image(pil, 'player_number')[-1]
        # self.number = int(num)
        self.number = num


    # @ut.time_this
    def read_gsp(self, card):
        crop = card.crop(ut.COORDS['LOBBY']['PLAYER']['GSP'])
        text = ut.read_image(crop, 'gsp')
        self.gsp = int(text.replace(',', ''))


class Team:
    def __init__(self, color):
        self.color = color
        self.players = []
        self.gsp_total = 0
        self.placement = ''


    def serialize(self, images_bool=True):
        players = [player.serialize(images_bool) for player in self.players]
        _copy = copy.copy(self)
        _copy.players = players
        return _copy.__dict__


    def add_player(self, player):
        self.players.append(player)
        self.gsp_total += player.gsp


class Game:
    def __init__(self, num):
        self.number = num
        self.mode = ''
        self.map = ''
        self.team_mode = False
        self.teams = []
        self.player_count = 0
        self.winning_color = ''
        self.start_time = 0
        self.duration = 0
        self.cancelled = False
        self.colors_correct = False


    def serialize(self, images_bool=True):
        teams = [team.serialize(images_bool) for team in self.teams]
        _copy = copy.copy(self)
        _copy.teams = teams
        return _copy.__dict__


    def load(self, data):
        self.__dict__.update(data)


    def read_card_screen(self, card_screen):
        self.read_basic_info(card_screen)
        self.read_cards(card_screen)


    @ut.time_this
    def read_basic_info(self, screen):
        crop = screen.crop(ut.COORDS['LOBBY']['GAME_INFO'])
        text = ut.read_image(crop)
        splits = text.split(' / ')
        self.mode = splits[0]
        self.map = splits[1]

    @ut.time_this
    def read_cards(self, screen):
        # screen.save('screen.png')
        id_slice = screen.crop(ut.COORDS['LOBBY']['CARDS_SLICE_IDS'])
        pil, cv = ut.convert_to_bw(id_slice, threshold=220, inv=False)
        # pil.save('slice.png')
        color_slice = screen.crop(ut.COORDS['LOBBY']['CARDS_SLICE_COLORS'])
        id_arr = np.asarray(pil)
        color_arr = np.asarray(color_slice)
        players = []
        skip = 0
        id_pixels = [p for row in id_arr for p in row]
        color_pixels = [p for row in color_arr for p in row]
        players = []
        for i, id_pixel in enumerate(id_pixels):
            if skip:
                skip -= 1
            elif id_pixel == 255:
                card_boundary = (i - 62, 375, i + 341, 913)
                crop = screen.crop(card_boundary)
                crop2 = crop.crop(ut.COORDS['LOBBY']['CHARACTER_TEMPLATE'])
                # crop2.save(f'{time.time()}.png')
                color = ut.match_color(arr=color_pixels[i - 5], mode='CARDS')[0]

                player = Player()
                player.read_card(crop)
                if player.character_name == '...':
                    _print('GAME CANCELLED DUE TO UNREADABLE CHARACTER NAME')
                    self.cancelled = True
                else:
                    players.append(player.character_name)
                self.player_count += 1

                team = next((t for t in self.teams if t.color == color), None)
                if not team:
                    team = Team(color)
                    self.teams.append(team)
                team.add_player(player)

                skip = 340
        if len(self.teams) == 2 and self.player_count > 2:
            self.team_mode = True
            self.colors_correct = True
        if len(set(players)) < len(players):
            _print('GAME CANCELLED DUE TO DUPLICATE CHARACTER IN FFA')
            self.cancelled = True


    # HERE -


    def read_start_screen(self, screen):
        if not self.team_mode and not self.cancelled:
            # self.fix_colors(screen)
            pass
        if self.mode == 'Stock':
            self.get_stock_templates(screen)
        elif self.mode == 'Time':
            pass
        elif self.mode == 'Stamina':
            pass
        else:
            _print(f'unknown mode: {self.mode}')


    # @ut.time_this
    def get_stock_templates(self, screen):
        stocks = []
        for edge in ut.COORDS['GAME']['PLAYER']['INFO'][self.player_count]:
            stock_template_coords = list(ut.COORDS['GAME']['PLAYER']['STOCK_TEMPLATE'])
            stock_template_coords[0] = edge - stock_template_coords[0]
            stock_template_coords[2] = edge - stock_template_coords[2]
            template = screen.crop(stock_template_coords)
            player_stock_count = 1
            while True:
                stock_template_coords[0] += STOCK_SPACING
                stock_template_coords[2] += STOCK_SPACING
                crop = screen.crop(stock_template_coords)
                sim = ut.avg_sim(crop, template)
                if sim > 95:
                    player_stock_count += 1
                else:
                    break


    def fix_colors(self, screen):
        colors = ['RED', 'BLUE', 'YELLOW', 'GREEN']
        names = self.get_character_names_game(screen)
        players = [player for team in self.teams for player in team.players]
        self.teams = []
        for i, name in enumerate(names):
            player = next((p for p in players if p.character_name == name), None)
            team = Team(colors[i])
            team.add_player(player)
            self.teams.append(team)
            print(f'{team.color} - {player.character_name}')


    def get_character_templates_lobby(self, screen):
        characters = []
        for edge in ut.COORDS['GAME']['PLAYER']['INFO'][self.player_count]:
            char_template_coords = list(ut.COORDS['GAME']['PLAYER']['CHARACTER_TEMPLATE'])
            char_template_coords[0] = edge - char_template_coords[0]
            char_template_coords[2] = edge - char_template_coords[2]
            template = screen.crop(char_template_coords)
            template.save(f'{time.time()}.png')


    def get_character_templates_game(self, screen):
        characters = []
        for edge in ut.COORDS['GAME']['PLAYER']['INFO'][self.player_count]:
            char_template_coords = list(ut.COORDS['GAME']['PLAYER']['CHARACTER_TEMPLAT'])
            char_template_coords[0] = edge - char_template_coords[0]
            char_template_coords[2] = edge - char_template_coords[2]
            template = screen.crop(char_template_coords)
            template.save(f'{time.time()}.png')


    def get_character_names_game(self, screen):
        names = []
        rerun = True
        while rerun:
            for edge in ut.COORDS['GAME']['PLAYER']['INFO'][self.player_count]:
                char_template_coords = list(ut.COORDS['GAME']['PLAYER']['NAME'])
                char_template_coords[0] = edge - char_template_coords[0]
                char_template_coords[2] = edge - char_template_coords[2]
                template = screen.crop(char_template_coords)
                bw, _ = ut.convert_to_bw(template)
                name_as_read = ut.read_image(bw).lower()
                if name_as_read:
                    rerun = False
                    name = difflib.get_close_matches(name_as_read, CHARACTER_NAMES, n=1)
                    if len(name):
                        _print(f'{name_as_read.rjust(30)} --> {name}')
                        names.append(name[0])
                    else:
                        _print(f'Can\'t read <{name_as_read}>')
                    # template.show()
                    # template.save(f'{time.time()}.png')
                else:
                    _print(f'Can\'t read <{name_as_read}>')
        return names


    def wait_for_go(self):
        coords = ut.COORDS['GAME']['']
        template = ut.TEMPLATES['IDS']['FIGHT_START']
        screen = ut.capture_screen()
        crop = screen.crop(coords)
        while ut.avg_sim(crop, template) > 85:
            screen = ut.capture_screen()
            crop = screen.crop(coords)
            time.sleep(0.1)
        self.start_time = time.time()


    def read_end_screen(self, screen):
        pass


    def read_results_screen(self, screen):
        if self.team_mode:
            coords = ut.COORDS['FINAL']['VICTORY_TEAM']
            templates = ut.TEMPLATES['FINAL']
            crop = screen.crop(coords)
            sim_template = ut.find_most_similar(crop, templates)
            color = sim_template[0].split('_')[0]
            self.winning_color = color
            _print(self.winning_color)
        else:
            coords = ut.COORDS['FINAL']
            first_place_pixel = screen.crop(coords['VICTORY_PLAYER'])
            self.winning_color, sim = ut.match_color(pixel=first_place_pixel, mode='RESULTS')
            _print(self.winning_color)
        team = next((t for t in self.teams if t.color == self.winning_color), None)
        team.placement = '1st'
        # print(self.serialize())
