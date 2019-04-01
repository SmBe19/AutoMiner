#!/usr/bin/env python3

import argparse
import itertools
import random
import subprocess
import time
from PIL import Image

class Game:

    def __init__(self, args):
        self.args = args

    def init_game(self):
        self.get_screenshot(delay=1)
        print("Init game parameters")
        im = Image.open('screen.png')
        self.imwidth, self.imheight = im.size
        self.background = im.getpixel((0, 0))

        def get_tiles():
            for y in range(self.imheight):
                for x in range(self.imwidth//2):
                    px = im.getpixel((x, y))
                    if px != self.background and im.getpixel((x+5, y+5)) == px:
                        return px, x, y

        self.tilecol, self.imstart_x, self.imstart_y = get_tiles()

        def count_tiles(dx, dy):
            count = 0
            innersize = 0
            size = 0
            inside = True
            ax = self.imstart_x
            ay = self.imstart_y
            while ax < self.imwidth and ay < self.imheight:
                px = im.getpixel((ax, ay))
                if inside:
                    if px == self.background:
                        inside = False
                        count += 1
                        if innersize == 0:
                            innersize = ax - self.imstart_x + ay - self.imstart_y
                else:
                    if px == self.tilecol:
                        inside = True
                        if size == 0:
                            size = ax - self.imstart_x + ay - self.imstart_y
                ax += dx
                ay += dy
            return count, size, innersize

        self.width, self.tilewidth, self.tileinnerwidth = count_tiles(1, 0)
        self.height, self.tileheight, self.tileinnerheight = count_tiles(0, 1)
        im.close()

    def read_field(self):
        self.get_screenshot(delay=0.5)
        print("Read field")
        im = Image.open('screen.png')
        field_open = [[False for _ in range(self.width)] for _ in range(self.height)]
        field_num = [[0 for _ in range(self.width)] for _ in range(self.height)]
        for y in range(self.width):
            for x in range(self.height):
                px = self.get_tile_col(im, x, y)
                field_open[y][x] = self.get_err(px, self.opencol) < 10
                avg = self.get_tile_avg(im, x, y)
                field_num[y][x] = self.guess_num(x, y, avg)
        im.close()
        return field_open, field_num

    def guess_num(self, x, y, avg):
        if self.get_err(avg, self.opencol) < 10:
            return 0
        if self.get_err(avg, self.tilecol) < 10:
            return 0
        if self.get_err(avg, (205, 208, 209)) < 10:
            return 1
        if self.get_err(avg, (202, 214, 200)) < 10:
            return 2
        if self.get_err(avg, (222, 201, 194)) < 10:
            return 3
        if self.get_err(avg, (205, 204, 207)) < 10:
            # TODO differentiate between 1 and 4
            return 4
        if self.get_err(avg, (210, 201, 196)) < 10:
            return 5
        if self.get_err(avg, (169, 137, 132)) < 22:
            return -1
        print("Could not match", x, y, avg)
        print(self.opencol, self.tilecol)
        exit(1)

    def choose_tile(self, field_open, field_num):
        def print_number():
            print("Field Number")
            for line in field_num:
                print(*['{:2}'.format(l) for l in line])
        def print_open():
            print("Field Open")
            for line in field_open:
                print(*[1 if l else 0 for l in line])
        def print_required():
            print("Field Required")
            for line in field_req:
                print(*['{:2}'.format(l) for l in line])
        print_number()
        print_open()
        field_req = [[field_num[y][x] for x in range(self.width)] for y in range(self.height)]

        def inside(x, y):
            return 0 <= y < self.height and 0 <= x < self.width

        def valid_neighbor(x, y, xx, yy):
            return inside(xx, yy) and (yy != y or xx != x)

        def get_neighbors(x, y):
            for yy in range(y-1, y+2):
                for xx in range(x-1, x+2):
                    if valid_neighbor(x, y, xx, yy):
                        yield xx, yy

        def count_neighbors(x, y, check):
            cnt = 0
            for xx, yy in get_neighbors(x, y):
                if check(field_open[yy][xx], field_num[yy][xx]):
                    cnt += 1
            return cnt

        def find_neighbor(x, y, check):
            for xx, yy in get_neighbors(x, y):
                if check(field_open[yy][xx], field_num[yy][xx]):
                    return xx, yy
            return None, None

        def reduce_required(x, y):
            for xx, yy in get_neighbors(x, y):
                if field_open[yy][xx]:
                    field_req[yy][xx] -= 1
                    assert field_req[yy][xx] >= 0

        # calculate the remaining required number of bombss
        for y in range(self.height):
            for x in range(self.width):
                if field_num[y][x] == -1:
                    reduce_required(x, y)
        print_required()

        found_some = False

        # all requirements satisfied
        for y in range(self.height):
            for x in range(self.width):
                if field_open[y][x] and field_req[y][x] == 0:
                    xx, yy = find_neighbor(x, y, lambda a, b: not a and b != -1)
                    if xx is not None:
                        self.open_tile(xx, yy)

        if found_some:
            print('All requirements are satisfied for some fields')
            return None, None

        # all have to be bombs
        for y in range(self.height):
            for x in range(self.width):
                if field_open[y][x] and field_req[y][x] > 0:
                    if count_neighbors(x, y, lambda a, b: not a and b != -1) == field_req[y][x]:
                        print('Found all bombs', x, y, field_req[y][x])
                        for xx, yy in get_neighbors(x, y):
                            if not field_open[yy][xx] and field_num[yy][xx] != -1:
                                self.mark_tile(xx, yy)
                                field_num[yy][xx] = -1
                                reduce_required(xx, yy)
                                found_some = True
                        print_required()
        if found_some:
            print('Marked some as necessary bombs')
            return self.choose_tile(field_open, field_num)

        for y in range(self.height):
            for x in range(self.width):
                if field_open[y][x] and field_req[y][x] > 0:
                    neighs = [(xx, yy) for xx, yy in get_neighbors(x, y) if not field_open[yy][xx] and field_num[yy][xx] != -1]
                    bmb = [False] * len(neighs)
                    for i in range(field_req[y][x]):
                        bmb[i] = True
                    for abmb in itertools.permutations(bmb):
                        # TODO check whether the current bomb assignment is consistent
                        pass

        # play random
        x = random.randint(0, self.width-1)
        y = random.randint(0, self.height-1)
        while field_open[y][x]:
            x = random.randint(0, self.width-1)
            y = random.randint(0, self.height-1)
        print('Play random')
        return x, y

    def do_round(self):
        field_open, field_num = self.read_field()
        if not any(any(field for field in line) for line in field_open):
            print("Boom")
            return False
        x, y = self.choose_tile(field_open, field_num)
        if x is not None:
            self.open_tile(x, y)
        return True

    def first_round(self):
        x = random.randint(0, self.width-1)
        y = random.randint(0, self.height-1)
        self.open_tile(x, y)
        self.get_screenshot(delay=0.5)
        print("Make first move")
        im = Image.open('screen.png')
        self.opencol = self.get_tile_col(im, x, y)
        im.close()

    def play(self):
        self.first_round()
        self.do_round()
        while self.do_round():
            pass

    def get_err(self, px, pxprime):
        err = 0
        for i in range(len(px)):
            err += abs(px[i]-pxprime[i])
        return err

    def get_tile_avg(self, im, xx, yy):
        val = [0, 0, 0]
        startx = self.imstart_x + xx * self.tilewidth
        starty = self.imstart_y + yy * self.tilewidth
        cnt = 0
        for y in range(starty, starty+self.tileinnerheight-4):
            for x in range(startx, startx+self.tileinnerwidth-4):
                cnt += 1
                px = im.getpixel((x, y))
                for i in range(3):
                    val[i] += px[i]
        for i in range(3):
            val[i] = round(val[i]/cnt)
        return tuple(val)

    def get_tile_col(self, im, x, y, offx=0, offy=0):
        return im.getpixel((self.imstart_x + offx + x * self.tilewidth, self.imstart_y + offy + y * self.tileheight))

    def open_tile(self, x, y):
        print('Click tile', x, y)
        self.mouse_click(self.imstart_x + x * self.tilewidth, self.imstart_y + y * self.tileheight, 1)

    def mark_tile(self, x, y):
        print('Mark tile', x, y)
        self.mouse_click(self.imstart_x + x * self.tilewidth, self.imstart_y + y * self.tileheight, 3)

    def focus_window(self):
        res = subprocess.run(['xdotool', 'search', '--onlyvisible', '--limit', '1', '--sync', '--name', self.args.window_name], stdout=subprocess.PIPE)
        self.wid = res.stdout.decode('utf-8').strip()
        subprocess.run(['xdotool', 'windowactivate', '--sync', self.wid])

    def get_screenshot(self, delay=0):
        self.focus_window()
        self.move_mouse(0, 0)
        time.sleep(delay)
        subprocess.run(['gnome-screenshot', '-f', 'screen.png', '-B', '-w'])

    def move_mouse(self, x, y):
        subprocess.run(['xdotool', 'mousemove', '--window', self.wid, str(x), str(y)])

    def mouse_click(self, x, y, button):
        subprocess.run(['xdotool', 'mousemove', '--window', self.wid, str(x), str(y), 'click', str(button)])


def play_game(args):
    game = Game(args)
    game.init_game()
    print("Game size: {} {}".format(game.width, game.height))
    game.play()

def main():
    parser = argparse.ArgumentParser(description='Automatically find mines')
    parser.add_argument('window_name', nargs='?', default='Minen', help='Title of window which contains the game')
    args = parser.parse_args()
    play_game(args)

if __name__ == '__main__':
    main()