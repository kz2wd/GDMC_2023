import math
import random
import numpy as np
import time
from typing import Union

from gdpc import Editor, Box, Block, geometry
from gdpc.vector_tools import l1Norm
from glm import ivec3

from PlacementMap import PlacementMap
from blob_expand import blob_expand, get_borders, get_borders_from_outside
from utils import circle_around, increase_y, get_normalized_direction, coord_scalar_mul, coords_add, \
    perpendicular_vector, shift_on_side, coords_sub, get_norm, with_y, coord_int, coord_in_area, get_distance, \
    coord3d_list_to_2d


class Tower:
    def __init__(self, center, width, height, wall_fct, roof_fct):
        self.center = center
        self.width = width
        self.height = height
        self.wall_fct = wall_fct
        self.roof_fct = roof_fct

    def build_tower(self):
        print(":", end="")
        self.wall_fct(geometry.cylinder(self.center, self.width, self.height, hollow=True))

        def roof_shape(coord, width):
            return list(geometry.cylinder(coord, width, 1, hollow=True))

        def odd_width_generator(start_width, end=2, repeat=1):
            for i in range(start_width, end, -2):
                for _ in range(repeat):
                    yield i

        roof_coords = list(roof_blocks(increase_y(self.center, self.height), roof_shape,
                                       list(odd_width_generator(self.width + 2, repeat=3))))
        self.roof_fct(roof_coords)


class CastleRing:
    def __init__(self, castle, center, radius, tower_amount, build_rampart, coord2d_to_ground_coord, editor, tower_height_fun,
                 tower_width, wall_height_fun, wall_width, wall_placer_fct, roof_placer_fct, rampart_placer_fct, placement_map):
        self.placement_map: PlacementMap = placement_map
        self.rampart_placer_fct = rampart_placer_fct
        self.roof_placer_fct = roof_placer_fct
        self.wall_placer_fct = wall_placer_fct
        self.wall_width = wall_width
        self.wall_height_fun = wall_height_fun
        self.tower_width = tower_width
        self.tower_height_fun = tower_height_fun
        self.editor: Editor = editor
        self.coord2d_to_ground_coord = coord2d_to_ground_coord
        self.build_rampart = build_rampart
        self.center = center
        self.radius = radius
        self.tower_amount = tower_amount
        self.towers: list[Tower] = []
        self.gates = []
        self.blocks = []
        self.castle: Castle = castle

    def get_territory(self):
        self.blocks = set(map(lambda coord: (coord.x, coord.z), blob_expand(self.placement_map.build_area, self.placement_map.height_map, self.center, max_distance=self.radius,
                    max_rel_diff=1, max_abs_diff=15)))

    def build_tower_ring(self):
        print("&", end="")
        self.get_territory()
        circle = list(get_borders_from_outside(self.blocks, self.center, self.tower_amount, self.radius))
        tower_heights = []
        # Place towers
        for x, z in circle:
            if not self.editor.getBuildArea().contains((x, 0, z)) or (x, z) not in self.blocks:
                continue
            base_coord = self.coord2d_to_ground_coord(x, z)

            # Check for tower collision
            i, j = self.placement_map.coord_absolute_to_relative(x, z)

            all_towers = [tower for ring in self.castle.rings for tower in ring.towers]

            # get nearest tower
            if len(all_towers) > 0:
                min_distance, nearest_tower = min([(get_distance((tower.center[0], tower.center[2]), (x, z)), tower) for tower in all_towers], key=lambda a: a[0])
                if min_distance <= self.tower_width + nearest_tower.width:
                    self.towers.append(nearest_tower)
                    tower_heights.append(nearest_tower.height)
                    print("M", end="")
                else:
                    tower_heights.append(self.tower_height_fun())
                    self.towers.append(Tower(base_coord, self.tower_width, tower_heights[-1], self.wall_placer_fct,
                                             self.roof_placer_fct))
                    self.towers[-1].build_tower()
            else:
                tower_heights.append(self.tower_height_fun())
                self.towers.append(Tower(base_coord, self.tower_width, tower_heights[-1], self.wall_placer_fct, self.roof_placer_fct))
                self.towers[-1].build_tower()

        if self.build_rampart and tower_heights:
            print(".", end="")
            wall_height = self.wall_height_fun(min(tower_heights) + 5)
            # Place walls
            tower_coords = coord3d_list_to_2d(map(lambda t: t.center, self.towers))
            for (x1, z1), (x2, z2) in zip(tower_coords, tower_coords[1:] + [tower_coords[0]]):
                if not (self.editor.getBuildArea().contains((x1, 0, z1)) and self.editor.getBuildArea().contains((x2, 0, z2))):
                    continue
                coord1 = self.coord2d_to_ground_coord(x1, z1)
                coord2 = self.coord2d_to_ground_coord(x2, z2)

                rampart_line = list(geometry.line3D(coord_int(coord1), coord_int(coord2), width=self.wall_width))

                # Build dict with max Y's
                rampart_height = {(coord[0], coord[2]): 300 for coord in rampart_line}
                for coord in rampart_line:
                    if coord[1] < rampart_height[(coord[0], coord[2])]:
                        rampart_height[(coord[0], coord[2])] = coord[1]

                rampart_biggest_ys = [(index[0], rampart_height[index], index[1]) for index in rampart_height.keys()]

                rampart_blocks = [increase_y(coord, i) for i in range(wall_height) for coord in
                                  rampart_biggest_ys] + rampart_line

                self.rampart_placer_fct(rampart_blocks)

        self.compute_gates()


    def compute_gates(self):
        if not len(self.towers):
            return
        for t1, t2 in zip(self.towers, self.towers[1:] + [self.towers[0]]):
            self.gates.append(coord_int(coords_add(coord_scalar_mul(coords_sub(t2.center, t1.center), .5), t1.center)))

    def __contains__(self, coord):
        return coord_in_area(coord, self.center, self.radius)


class Castle:
    def __init__(self, center, radius, ring_amount, placement_map):
        self.placement_map: PlacementMap = placement_map
        self.center = center
        self.radius = radius
        self.ring_amount = ring_amount
        self.rings: list[CastleRing] = []

    def build_castle(self, editor: Editor, coord2d_to_ground_coord, wall_placer_fct, roof_placer_fct,
                     rampart_placer_fct):

        print("Building castle ", end="")
        tower_amount_factor = random.randint(5, 8)
        tower_amount_scaling = random.random() / 2 + 0.5
        tower_amounts = [max(5, int(tower_amount_factor * i * tower_amount_scaling)) for i in range(1, self.ring_amount + 1)]

        tower_amount_fun = lambda i: tower_amounts[i]

        tower_height_downscaling = random.random() / 5 + 0.6
        downscaling_factor = random.randint(10, 20)
        tower_base_height = random.randint(30, 50)
        tower_heights = [int(tower_base_height * (tower_height_downscaling ** i)) for i in range(1, self.ring_amount + 1)]

        min_height = 10
        max_height = tower_base_height
        tower_height_variation = random.randint(1, 8)
        tower_height_fun_generator = lambda i: lambda: random.randint(
            max(tower_heights[i] - tower_height_variation, min_height),
            max(min_height, min(tower_heights[i] + tower_height_variation, max_height)))

        def variation_clamped_around(_min, _max, around, var):
            return random.randint(max(_min, around - var), min(around + var, _max))

        base_width = random.randint(15, 25)
        width_decrease = random.random() / 5 + 0.75
        tower_widths = [int(base_width * (width_decrease ** i)) for i in
                         range(1, self.ring_amount + 1)]
        tower_width_generator = lambda i: variation_clamped_around(5, 25, tower_widths[i], 0)
        wall_height_fun = lambda t_height: variation_clamped_around(min_height - 2, t_height, int(t_height / 2), 5)
        wall_width_fun = lambda t_width: variation_clamped_around(2, t_width, int(t_width / 2), 3)

        for i in range(self.ring_amount):
            ring_radius = (i + 1) * (self.radius / self.ring_amount)

            # Generate tower ring
            tower_width = tower_width_generator(i)
            self.rings.append(CastleRing(self, self.center, ring_radius, tower_amount_fun(i), True, coord2d_to_ground_coord, editor,
                                         tower_height_fun_generator(i), tower_width, wall_height_fun, wall_width_fun(tower_width),
                                         wall_placer_fct, roof_placer_fct, rampart_placer_fct, self.placement_map))
            self.rings[-1].build_tower_ring()

        print("\nCastle generation over")

    def __contains__(self, coord):
        return coord_in_area(coord, self.center, self.radius)


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



