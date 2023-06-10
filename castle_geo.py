import math
import random
import numpy as np
import time
from typing import Union

from gdpc import Editor, Box, Block, geometry
from gdpc.vector_tools import l1Norm
from glm import ivec3

from utils import circle_around, increase_y, get_normalized_direction, coord_scalar_mul, coords_add, \
    perpendicular_vector, shift_on_side, coords_sub, get_norm, with_y, coord_int


def gradiantPlacer(editor, block_pattern: list[Block]):
    def placer(iterator):
        block_list = list(iterator)
        if not len(block_list):
            return
        y_coords = list(map(lambda b: b[1], block_list))
        placeGradient(editor, block_list, min(y_coords), len(set(y_coords)), block_pattern)

    return placer


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


def build_castle(editor: Editor, castle_center, coord2d_to_ground_coord, wall_placer_fct, roof_placer_fct, rampart_placer_fct, castle_radius=None, ring_amount=None):
    if castle_radius is None:
        castle_radius = random.randint(30, 75)
    if ring_amount is None:
        ring_amount = random.randint(1, int(castle_radius / 20))

    tower_amount_factor = random.randint(5, 8)
    tower_amount_scaling = random.random() / 2 + 0.5
    tower_amounts = [max(3, int(tower_amount_factor * i * tower_amount_scaling)) for i in range(1, ring_amount + 1)]

    tower_amount_fun = lambda i: tower_amounts[i]

    tower_height_downscaling = random.random() / 2 + 0.5
    downscaling_factor = random.randint(5, 10)
    tower_base_height = random.randint(30, 50)
    tower_heights = [int(tower_base_height - (i * downscaling_factor)) for i in range(1, ring_amount + 1)]

    min_height = 10
    max_height = tower_base_height
    tower_height_variation = random.randint(1, 8)
    tower_height_fun_generator = lambda i: lambda: random.randint(max(tower_heights[i] - tower_height_variation, min_height), max(min_height, min(tower_heights[i] + tower_height_variation, max_height)))

    def variation_clamped_around(_min, _max, around, var):
        return random.randint(max(_min, around - var), min(around + var, _max))

    tower_width_generator = lambda: random.randint(3, 15)
    wall_height_fun = lambda t_height: variation_clamped_around(min_height - 2, t_height, int(t_height / 2), 5)
    wall_width_fun = lambda t_width: variation_clamped_around(2, t_width, int(t_width / 2), 3)

    center_tower_amount = random.randint(1, 3)
    center_tower_width = random.randint(10, 20)
    center_tower_height = lambda: random.randint(40, 70)
    # Center tower
    build_tower_ring(False, castle_center, [1, 10, 10][center_tower_amount - 1], coord2d_to_ground_coord, editor, center_tower_amount,
                     center_tower_height, center_tower_width, wall_height_fun, wall_width_fun(center_tower_width), wall_placer_fct, roof_placer_fct, rampart_placer_fct)

    for i in range(ring_amount):
        ring_radius = (i + 1) * (castle_radius / ring_amount)
        if random.random() > .5:
            # Generate tower ring
            tower_width = tower_width_generator()
            build_tower_ring(True, castle_center, ring_radius, coord2d_to_ground_coord, editor, tower_amount_fun(i),
                             tower_height_fun_generator(i), tower_width, wall_height_fun, wall_width_fun(tower_width), wall_placer_fct, roof_placer_fct, rampart_placer_fct)
        else:
            # Generate habitation ring
            def house_wall_placer(coords):
                for coord in coords:
                    editor.placeBlock(coord, Block("oak_log"))

            house_fun = house_builder_generator(10, 10, house_wall_placer, roof_placer_fct)
            build_habitation_ring(castle_center,  ring_radius, coord2d_to_ground_coord, editor, tower_amount_fun(i), house_fun)


def build_tower_ring(build_ramparts, ring_center, ring_radius, coord2d_to_ground_coord, editor, tower_amount,
                     tower_height_fun, tower_width, wall_height_fun, wall_width, wall_placer_fct, roof_placer_fct, rampart_placer_fct):
    circle = list(circle_around(ring_center, ring_radius, tower_amount))
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

            rampart_blocks = [increase_y(coord, i) for i in range(wall_height) for coord in
                              geometry.line3D(coord_int(coord1), coord_int(coord2), width=wall_width)]

            rampart_placer_fct(rampart_blocks)


def house_builder_generator(house_height, house_size, wall_placer, roof_placer):
    def house_builder(center):
        wall_placer(geometry.cylinder(center, diameters=house_size, length=house_height, tube=True))
        for y, i in enumerate(range(house_size, 3, -2), start=house_height):
            roof_placer(geometry.cylinder(increase_y(center, y), diameters=i, length=1))
    return house_builder


def build_habitation_ring(ring_center, ring_radius, coord2d_to_ground_coord, editor, house_amount,
                     house_fun):
    circle = list(circle_around(ring_center, ring_radius, house_amount))
    # Place habitations
    for x, z in circle:
        if not editor.getBuildArea().contains((x, 0, z)):
            continue
        base_coord = coord2d_to_ground_coord(x, z)
        house_fun(base_coord)



