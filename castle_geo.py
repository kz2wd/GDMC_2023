import math
import random
import time
from typing import Union

from gdpc import Editor, Box, Block, geometry

from utils import circle_around, increase_y


def placeGradient(editor: Editor, iterator, comp, size, blocks: list[Block]):
    block_amount = len(blocks)
    thickness = size / block_amount

    fun = lambda x, idx: math.sin(x * random.randint(1, 5) * 10) * math.sin(x * 100) * thickness + (idx * thickness) + 5

    def get_block(position):
        for i in range(block_amount):
            if fun(position[0] + position[2], i) > position[1] - comp:
                return i
        return block_amount - 1

    for position in iterator:

        i = get_block(position)
        editor.placeBlock(position, blocks[i])


def placeGradientBox(editor: Editor, box: Box, blocks: list[Block]) -> None:
    placeGradient(editor, box.shell, box.begin[1], box.size[1], blocks)


def build_castle(editor: Editor, castle_center, coord2d_to_ground_coord, castle_size=None, tower_amount=None,
                 tower_height=None, tower_width=None, wall_height=None):
    if castle_size is None:
        castle_size = random.randint(15, 50)
    if tower_amount is None:
        tower_amount = random.randint(3, int(castle_size / 3))

    if tower_height is None:
        tower_height = random.randint(5, 30)
    if tower_width is None:
        tower_width = random.randint(5, int(castle_size / 3))
    if wall_height is None:
        wall_height = random.randint(int(tower_height / 2), tower_height - 2)

    circle = list(circle_around(castle_center, castle_size, tower_amount))

    # Place towers
    for x, z in circle:
        if not editor.getBuildArea().contains((x, 0, z)):
            continue
        base_coord = coord2d_to_ground_coord(x, z)
        geometry.placeCylinder(editor, base_coord, tower_width, tower_height, Block("stone_bricks"))

    # Place walls
    for (x1, z1), (x2, z2) in zip(circle, circle[1:] + [circle[0]]):
        if not (editor.getBuildArea().contains((x1, 0, z1)) and editor.getBuildArea().contains((x2, 0, z2))):
            continue
        coord1 = coord2d_to_ground_coord(x1, z1)
        coord2 = coord2d_to_ground_coord(x2, z2)

        for coord in geometry.line3D(coord1, coord2):
            for i in range(wall_height):
                editor.placeBlock(increase_y(coord, i), Block("andesite"))

