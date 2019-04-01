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
        self.get_screenshot(delay1=1)
        print("Init game parameters")
        im = Image.open('screen.png')
        self.imwidth, self.imheight = im.size

        def get_background():
            col = im.getpixel((self.imwidth//2, self.imheight//2))
            for y in range(self.imheight//2, self.imheight):
                for x in range(self.imwidth//2, self.imwidth):
                    px = im.getpixel((x, y))
                    if px[0] < col[0] and im.getpixel((x-5, y-5)) == col:
                        return col[:3]
                    else:
                        col = px

        self.background = get_background()

        def find_bounds_tl():
            for y in range(self.imheight):
                for x in range(self.imwidth):
                    px = im.getpixel((x, y))
                    if px[:3] == self.background:
                        return (x, y)
        def find_bounds_br():
            for y in range(self.imheight-1, -1, -1):
                for x in range(self.imwidth-1, -1, -1):
                    px = im.getpixel((x, y))
                    if px[:3] == self.background:
                        return (x, y)
        self.cr_left, self.cr_top = find_bounds_tl()
        self.cr_right, self.cr_bottom = find_bounds_br()

        def get_tiles():
            for y in range(self.cr_top, self.cr_bottom):
                for x in range(self.cr_left, self.imwidth//2):
                    px = im.getpixel((x, y))
                    if px[:3] != self.background and im.getpixel((x+5, y+5)) == px:
                        return px[:3], x, y

        self.tilecol, self.imstart_x, self.imstart_y = get_tiles()

        def count_tiles(dx, dy):
            count = 0
            innersize = 0
            size = [0]
            inside = True
            ax = self.imstart_x
            ay = self.imstart_y
            while ax < self.imwidth and ay < self.imheight:
                px = im.getpixel((ax, ay))[:3]
                if inside:
                    if px == self.background:
                        inside = False
                        count += 1
                    if innersize == 0 and px != self.tilecol:
                        innersize = ax - self.imstart_x if dx > 0 else ay - self.imstart_y
                else:
                    if px == self.tilecol:
                        inside = True
                        size.append(ax - self.imstart_x if dx > 0 else ay - self.imstart_y)
                ax += dx
                ay += dy
            return count, size, innersize

        self.width, self.tilewidth, self.tileinnerwidth = count_tiles(1, 0)
        self.height, self.tileheight, self.tileinnerheight = count_tiles(0, 1)

        self.need_read = [[True for _ in range(self.width)] for _ in range(self.height)]
        self.field_open = [[False for _ in range(self.width)] for _ in range(self.height)]
        self.field_num = [[0 for _ in range(self.width)] for _ in range(self.height)]

        im.close()

    def read_field(self):
        self.get_screenshot()
        print("Read field")
        im = Image.open('screen.png')
        for y in range(self.height):
            for x in range(self.width):
                if self.need_read[y][x]:
                    px = self.get_tile_col(im, x, y)
                    self.field_open[y][x] = self.get_err(px, self.opencol) < 10
                    if self.field_open[y][x]:
                        col = self.get_tile_num_col(im, x, y)
                        self.field_num[y][x] = self.guess_num(x, y, col)
                        self.need_read[y][x] = False
                    else:
                        # check for boom
                        num = self.guess_num(x, y, px)
        im.close()
        return self.field_open, self.field_num

    def guess_num(self, x, y, col):
        if col == (-1, -1, -1):
            return 0
        if self.get_err(col, self.opencol) < 22:
            return 0
        if self.get_err(col, self.tilecol) < 22:
            return 0
        if self.get_err(col, (75, 105, 131)) < 10:
            return 1
        if self.get_err(col, (70, 160, 70)) < 10:
            return 2
        if self.get_err(col, (223, 66, 30)) < 10:
            return 3
        if self.get_err(col, (98, 91, 129)) < 10:
            return 4
        if self.get_err(col, (136, 70, 49)) < 10:
            return 5
        if self.get_err(col, (157, 184, 210)) < 10:
            return 6
        if self.get_err(col, (0, 0, 0)) < 10:
            return 7
        if self.get_err(col, (0, 0, 0)) < 10:
            return 8
        if self.get_err(col, (119, 119, 119)) < 10:
            return -1
        print('Could not match', x, y, col)
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
        if self.args.d_number:
            print_number()
        if self.args.d_open:
            print_open()
        field_req = [[field_num[y][x] for x in range(self.width)] for y in range(self.height)]

        def inside(x, y):
            return 0 <= y < self.height and 0 <= x < self.width

        def valid_neighbor(x, y, xx, yy):
            return inside(xx, yy) and (yy != y or xx != x)

        def get_neighbors(x, y, dx=1, dy=1):
            for yy in range(y-dy, y+dy+1):
                for xx in range(x-dx, x+dx+1):
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
                    yield xx, yy

        def reduce_required(x, y):
            for xx, yy in get_neighbors(x, y):
                if field_open[yy][xx]:
                    field_req[yy][xx] -= 1
                    assert field_req[yy][xx] >= 0

        # calculate the remaining required number of mines
        for y in range(self.height):
            for x in range(self.width):
                if field_num[y][x] == -1:
                    reduce_required(x, y)
        if self.args.d_required:
            print_required()

        found_some = False

        # all requirements satisfied
        for y in range(self.height):
            for x in range(self.width):
                if field_open[y][x] and field_req[y][x] == 0:
                    for xx, yy in find_neighbor(x, y, lambda a, b: not a and b != -1):
                        self.open_tile(xx, yy)
                        found_some = True

        if found_some:
            print('Open neighbors of finished fields')
            return

        # all have to be mines
        for y in range(self.height):
            for x in range(self.width):
                if field_open[y][x] and field_req[y][x] > 0:
                    if count_neighbors(x, y, lambda a, b: not a and b != -1) == field_req[y][x]:
                        if self.args.d_allmines:
                            print('All neighbors are mines', x, y, field_req[y][x])
                        for xx, yy in get_neighbors(x, y):
                            if not field_open[yy][xx] and field_num[yy][xx] != -1:
                                self.mark_tile(xx, yy)
                                field_num[yy][xx] = -1
                                reduce_required(xx, yy)
                                found_some = True
                        if self.args.d_required:
                            print_required()
        if found_some:
            print('Mark necessary mines')
            self.choose_tile(field_open, field_num)
            return

        def check_consistent(maybe_mines):
            for y in range(self.height):
                for x in range(self.width):
                    if field_open[y][x]:
                        ma = 0
                        mi = 0
                        for xx, yy in get_neighbors(x, y):
                            if maybe_mines[yy][xx] == 1:
                                ma += 1
                                mi += 1
                            elif maybe_mines[yy][xx] == 0:
                                ma += 1
                        if mi > field_num[y][x] or ma < field_num[y][x]:
                            if self.args.d_brute:
                                print('Not consistent', x, y, mi, ma, field_num[y][x])
                            return False
            if self.args.d_brute:
                print('Consistent')
            return True

        for y in range(self.height):
            for x in range(self.width):
                if field_open[y][x] and field_req[y][x] > 0:
                    maybe_mines = [[1 if field_num[y][x] == -1 else (-1 if field_open[y][x] else 0) for x in range(self.width)] for y in range(self.height)]
                    neighs = [(xx, yy) for xx, yy in get_neighbors(x, y) if not field_open[yy][xx] and field_num[yy][xx] != -1]
                    neighsum = [0 for _ in range(len(neighs))]
                    mines = [False] * len(neighs)
                    for i in range(field_req[y][x]):
                        mines[i] = True

                    if self.args.d_brute:
                        print('Brute try', x, y, neighs)

                    cnt = 0
                    for amine in set(itertools.permutations(mines)):
                        if self.args.d_brute:
                            print('Amine', amine)
                        for neigh, mine in zip(neighs, amine):
                            maybe_mines[neigh[1]][neigh[0]] = 1 if mine else -1

                        if check_consistent(maybe_mines):
                            cnt += 1
                            for i in range(len(neighs)):
                                neighsum[i] += 1 if amine[i] else -1
                    assert cnt > 0
                    if self.args.d_brute:
                        print('Neighsum', cnt, neighsum)
                    for neigh, su in zip(neighs, neighsum):
                        if su == cnt:
                            self.mark_tile(neigh[0], neigh[1])
                            field_num[neigh[1]][neigh[0]] = -1
                            reduce_required(neigh[0], neigh[1])
                            found_some = True
                        elif su == -cnt:
                            self.open_tile(neigh[0], neigh[1])
                            found_some = True

        if found_some:
            print('Brute force thinking')
            return

        # play random
        x = random.randint(0, self.width-1)
        y = random.randint(0, self.height-1)
        while field_open[y][x] or field_num[y][x] == -1:
            x = random.randint(0, self.width-1)
            y = random.randint(0, self.height-1)
        print('Play random')
        self.open_tile(x, y)

    def first_round(self):
        x = random.randint(0, self.width-1)
        y = random.randint(0, self.height-1)
        self.open_tile(x, y)
        self.get_screenshot()
        print("Make first move")
        im = Image.open('screen.png')
        self.opencol = self.get_tile_col(im, x, y)
        im.close()

    def play(self):
        self.first_round()
        while True:
            field_open, field_num = self.read_field()
            self.choose_tile(field_open, field_num)

    def get_err(self, px, pxprime):
        err = 0
        for i in range(len(px)):
            err += abs(px[i]-pxprime[i])
        return err

    def get_tile_num_col(self, im, xx, yy):
        startx = self.imstart_x + self.tilewidth[xx]
        starty = self.imstart_y + self.tileheight[yy]
        pxx = [[im.getpixel((x, y)) for x in range(startx, startx+self.tileinnerwidth)] for y in range(starty, starty+self.tileinnerheight)]
        for y in range(self.tileinnerheight):
            for x in range(self.tileinnerwidth):
                neighborhood = [(x+i, y+j) for i in range(-1, 1) for j in range(-1, 1)]
                px = pxx[y][x]
                if self.get_err(self.opencol, px[:3]) > 22 and self.get_err(self.tilecol, px[:3]) > 22:
                    if all(px == pxx[yyy][xxx] for xxx, yyy in neighborhood):
                        return px[:3]
        return (-1, -1, -1)

    def get_tile_avg(self, im, xx, yy):
        val = [0, 0, 0]
        startx = self.imstart_x + self.tilewidth[xx]
        starty = self.imstart_y + self.tileheight[yy]
        cnt = 0
        for y in range(starty, starty+self.tileinnerheight):
            for x in range(startx, startx+self.tileinnerwidth):
                cnt += 1
                px = im.getpixel((x, y))[:3]
                for i in range(3):
                    val[i] += px[i]
        for i in range(3):
            val[i] = round(val[i]/cnt)
        return tuple(val)

    def get_tile_col(self, im, x, y, offx=0, offy=0):
        return im.getpixel((self.imstart_x + offx + self.tilewidth[x], self.imstart_y + offy + self.tileheight[y]))[:3]

    def open_tile(self, x, y):
        if self.args.d_click:
            print('Click tile', x, y)
        self.mouse_click(self.imstart_x + self.tilewidth[x] + self.tilewidth[1]//2, self.imstart_y + self.tileheight[y] + self.tileheight[1]//2, 1)

    def mark_tile(self, x, y):
        if self.args.d_mark:
            print('Mark tile', x, y)
        self.field_num[y][x] = -1
        self.mouse_click(self.imstart_x + self.tilewidth[x] + self.tilewidth[1]//2, self.imstart_y + self.tileheight[y] + self.tileheight[1]//2, 3)

    def focus_window(self):
        res = subprocess.run(['xdotool', 'search', '--onlyvisible', '--limit', '1', '--sync', '--name', self.args.window_name], stdout=subprocess.PIPE)
        self.wid = res.stdout.decode('utf-8').strip()
        subprocess.run(['xdotool', 'windowactivate', '--sync', self.wid])

    def get_screenshot(self, delay1=0.2, delay2=0.2):
        time.sleep(delay1)
        self.focus_window()
        self.move_mouse(0, 0)
        time.sleep(delay2)
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
    parser.add_argument('--d-number', action='store_true', help='Print the number field')
    parser.add_argument('--d-open', action='store_true', help='Print the open field')
    parser.add_argument('--d-required', action='store_true', help='Print the required field')
    parser.add_argument('--d-brute', action='store_true', help='Print brute force info')
    parser.add_argument('--d-click', action='store_true', help='Print all clicks')
    parser.add_argument('--d-mark', action='store_true', help='Print all markings')
    parser.add_argument('--d-allmines', action='store_true', help='Print if all neighbors are mines')
    args = parser.parse_args()
    play_game(args)

if __name__ == '__main__':
    main()
