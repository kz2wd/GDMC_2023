import math
import random
import numpy as np
import time
from typing import Union

from gdpc import Editor, Box, Block, geometry
from gdpc.vector_tools import l1Norm
from glm import ivec3

from utils import circle_around, increase_y, get_normalized_direction, coord_scalar_mul, coords_add, \
    perpendicular_vector, shift_on_side


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


def build_roof(editor: Editor, center, shape_function, widths, block):
    for i, width in enumerate(widths):
        for coord in shape_function(increase_y(center, i), width):
            editor.placeBlock(coord, block)


def build_tower(editor: Editor, tower_center, tower_width, tower_height):
    geometry.placeCylinder(editor, tower_center, tower_width, tower_height, Block("stone_bricks"))

    def roof_function(coord, width):
        return list(geometry.cylinder(coord, width, 1))

    build_roof(editor, increase_y(tower_center, tower_height), roof_function,
               list(map(int, np.linspace(tower_width + 1, 3, (tower_width + 1) * 2))), Block("oak_planks"))


def build_castle(editor: Editor, castle_center, coord2d_to_ground_coord, castle_size=None, tower_amount=None,
                 tower_height_fun=None, tower_width=None, wall_height_fun=None, wall_radius=None):
    if castle_size is None:
        castle_size = random.randint(5, 75)
    if tower_amount is None:
        tower_amount = random.randint(3, int((castle_size / 15) ** 2 ) + 3)
    if tower_height_fun is None:
        tower_height_fun = lambda: random.randint(int(1 + 50 / ((castle_size / 10) ** 2 )), min(int(20 + 200 / ((castle_size / 10) ** 2 )), 200))
    if tower_width is None:
        tower_width = random.randint(3, int(80 / (castle_size / 10) / tower_amount + 8))
    if wall_height_fun is None:
        wall_height_fun = lambda t_height: random.randint(int(t_height / 2), t_height - 2)
    if wall_radius is None:
        wall_radius = random.randint(1, tower_width - 2)

    circle = list(circle_around(castle_center, castle_size, tower_amount))

    tower_heights = []
    # Place towers
    for x, z in circle:
        if not editor.getBuildArea().contains((x, 0, z)):
            continue
        base_coord = coord2d_to_ground_coord(x, z)
        tower_heights.append(tower_height_fun())
        print("Tower height :", tower_heights[-1])
        build_tower(editor, base_coord, tower_width, tower_heights[-1])

    wall_height = wall_height_fun(min(tower_heights) + 5)
    # Place walls
    for (x1, z1), (x2, z2) in zip(circle, circle[1:] + [circle[0]]):
        if not (editor.getBuildArea().contains((x1, 0, z1)) and editor.getBuildArea().contains((x2, 0, z2))):
            continue
        coord1 = coord2d_to_ground_coord(x1, z1)
        coord2 = coord2d_to_ground_coord(x2, z2)
        # tower_shift = coord_scalar_mul(get_normalized_direction(coord2, coord1), tower_width / 2)

        wall_shift_functions = lambda shift: lambda vector: shift_on_side(vector, shift)
        for shift_function in map(wall_shift_functions, [wall_radius, -wall_radius]):
            shifted_coord1 = shift_function(coord1)
            shifted_coord2 = shift_function(coord2)

            # start_coord1 = coords_add(coord1, tower_shift)
            # end_coord2 = coords_add(coord2, coord_scalar_mul(tower_shift, -1))

            for coord in geometry.line3D(shifted_coord1, shifted_coord2):
                for i in range(wall_height):
                    editor.placeBlock(increase_y(coord, i), Block("andesite"))
