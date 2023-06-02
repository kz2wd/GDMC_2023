import math
import random
import numpy as np
import time
from typing import Union

from gdpc import Editor, Box, Block, geometry
from gdpc.vector_tools import l1Norm
from glm import ivec3

from utils import circle_around, increase_y, get_normalized_direction, coord_scalar_mul, coords_add, \
    perpendicular_vector, shift_on_side, coords_sub, get_norm, with_y


def gradiantPlacer(editor, block_pattern: list[Block]):
    return lambda iterator: placeGradient(editor, block_list := list(iterator), min(y_coords := list(map(lambda b: b[1], block_list))), len(set(y_coords)), block_pattern)


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


def roof_blocks(center, shape_function, widths):
    for i, width in enumerate(widths):
        for coord in shape_function(increase_y(center, i), width):
            yield coord


def build_tower(tower_center, tower_width, tower_height, wall_function, roof_function):
    wall_function(geometry.cylinder(tower_center, tower_width, tower_height, hollow=True))

    def roof_shape(coord, width):
        return list(geometry.cylinder(coord, width, 1, hollow=True))

    def odd_width_generator(start_width, end=3, repeat=1):
        for i in range(start_width, end, -2):
            for _ in range(repeat):
                yield i

    roof_coords = list(roof_blocks(increase_y(tower_center, tower_height), roof_shape, list(odd_width_generator(tower_width + 2, repeat=3))))
    roof_function(roof_coords)


def build_castle(editor: Editor, castle_center, coord2d_to_ground_coord, wall_placer_fct, roof_placer_fct, rampart_placer_fct, castle_size=None, tower_ring_amount=None):
    if castle_size is None:
        castle_size = random.randint(30, 75)
    if tower_ring_amount is None:
        tower_ring_amount = random.randint(1, int(castle_size / 10))

    tower_amount_fun = lambda: random.randint(3, int((castle_size / 15) ** 2) + 3)

    tower_height_fun = lambda: random.randint(int(5 + 50 / ((castle_size / 10) ** 2 )), min(int(20 + 200 / ((castle_size / 10) ** 2 )), 200))
    tower_width = random.randint(3, int(40 / (castle_size / 10) + 4))
    wall_height_fun = lambda t_height: random.randint(int(t_height / 2), t_height - 2)
    wall_radius = random.randint(1, tower_width - 2)

    center_tower_amount = random.randint(1, 3)
    center_tower_width = random.randint(10, 20)
    center_tower_height = lambda: random.randint(40, 70)
    # Center tower
    build_tower_ring(False, castle_center, [1, 10, 10][center_tower_amount - 1], coord2d_to_ground_coord, editor, center_tower_amount,
                     center_tower_height, center_tower_width, wall_height_fun, wall_radius, wall_placer_fct, roof_placer_fct, rampart_placer_fct)

    for i in range(tower_ring_amount):
        build_tower_ring(random.random() > .5, castle_center, (i + 1) * (castle_size / tower_ring_amount), coord2d_to_ground_coord, editor, tower_amount_fun(),
                         tower_height_fun, tower_width, wall_height_fun, wall_radius, wall_placer_fct, roof_placer_fct, rampart_placer_fct)


def build_tower_ring(build_ramparts, ring_center, ring_size, coord2d_to_ground_coord, editor, tower_amount,
                     tower_height_fun, tower_width, wall_height_fun, wall_radius, wall_placer_fct, roof_placer_fct, rampart_placer_fct):
    circle = list(circle_around(ring_center, ring_size, tower_amount))
    tower_heights = []
    # Place towers
    for x, z in circle:
        if not editor.getBuildArea().contains((x, 0, z)):
            continue
        base_coord = coord2d_to_ground_coord(x, z)
        tower_heights.append(tower_height_fun())
        build_tower(base_coord, tower_width, tower_heights[-1], wall_placer_fct, roof_placer_fct)
    if build_ramparts and tower_heights:
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
                shift_vector = with_y(shift_function(coords_sub(coord1, coord2)), 0)
                shifted_coord1 = coords_add(coord1, shift_vector)
                shifted_coord2 = coords_add(coord2, shift_vector)

                # start_coord1 = coords_add(coord1, tower_shift)
                # end_coord2 = coords_add(coord2, coord_scalar_mul(tower_shift, -1))
                rampart_blocks = [increase_y(coord, i) for i in range(wall_height) for coord in
                                  geometry.line3D(shifted_coord1, shifted_coord2)]
                rampart_placer_fct(rampart_blocks)




