from __future__ import annotations

import math
import random
from typing import List, Any, Sequence

import gdpc
from gdpc import Editor, Block, geometry, Box
from gdpc.block import transformedBlockOrPalette
from gdpc.geometry import placeLine
from gdpc.vector_tools import distance, X, Z, circle, ellipse
from glm import ivec3, ivec2

import cProfile
import pstats

import numpy as np

from castle_geo import placeGradientBox, placeGradient, build_castle, gradiantPlacer, build_tower_ring
from utils import shift_on_side, coord_normalize


class CoordExplore:
    def __hash__(self) -> int:
        return int(self.x * 7 + self.z * 17)

    def __eq__(self, other) -> bool:
        return self.x == other.x and self.z == other.z

    def __init__(self, x, z, build_area):
        self.x = x
        self.z = z
        self.build_area = build_area

    @property
    def coord(self):
        return self.x, self.z

    def __add__(self, other: tuple):
        return CoordExplore(self.x + other[0], self.z + other[1], self.build_area)

    @property
    def to_relative(self) -> tuple[int, int]:
        return self.x - self.build_area.begin[0], self.z - self.build_area.begin[2]

    @property
    def to_absolute(self) -> tuple[int, int]:
        return self.x + self.build_area.begin[0], self.z + self.build_area.begin[2]

    def distance_to(self, other: CoordExplore) -> float:
        return math.sqrt((other.x - self.x) ** 2 + (other.z - self.z) ** 2)

    def __str__(self):
        return f"{self.x} {self.z}"

    def to_3d(self, y):
        return self.x, y, self.z


def blob_expand(editor, start: tuple[int, int], max_rel_diff=1, max_abs_diff=5, max_distance=5) -> list[
    CoordExplore | Any]:
    hmap = editor.worldSlice.heightmaps["WORLD_SURFACE"]
    build_area = editor.getBuildArea()
    start = CoordExplore(start[0], start[1], build_area)
    blob = [start]
    to_explore = [start]
    explored = {start}
    while len(to_explore) > 0:
        current = to_explore.pop()
        blob.append(current)
        explored.add(current)
        for direction in [(1, 0), (0, 1), (-1, 0), (0, -1)]:
            neighbor = current + direction
            rel_cur = current.to_relative
            rel_neigb = neighbor.to_relative
            if neighbor not in explored \
                    and neighbor.distance_to(start) <= max_distance \
                    and 0 <= rel_cur[0] < hmap.shape[0] and 0 <= rel_cur[1] < hmap.shape[1] \
                    and 0 <= rel_neigb[0] < hmap.shape[0] and 0 <= rel_neigb[1] < hmap.shape[1] \
                    and abs(hmap[rel_cur] - hmap[rel_neigb]) <= max_rel_diff \
                    and abs(hmap[rel_neigb] - hmap[start.to_relative]) <= max_abs_diff:
                explored.add(neighbor)
                to_explore.append(neighbor)

    return blob


def sample_array2d(array2d, sampling):
    return array2d[::sampling, ::sampling]


def generate_decay_matrix(size):
    center = (size - 1) / 2
    x, y = np.indices((size, size))
    distance = np.sqrt((x - center) ** 2 + (y - center) ** 2)
    normalized_values = (np.max(distance) - distance) / np.max(distance)
    return normalized_values


def compute_variance_map(hmap: np.ndarray, sampling=5, blur_size=3):
    variance_map = np.array([[np.nanvar(hmap[max(i - blur_size, 0): min(i + blur_size, hmap.shape[0]),
                                        max(j - blur_size, 0): min(j + blur_size, hmap.shape[1])].flatten()) for
                              j in range(0, hmap.shape[1], sampling)] for i in range(0, hmap.shape[0], sampling)])

    def conversion_function(i, j):
        return i * sampling, j * sampling

    return variance_map, conversion_function


def get_lowest_indices_1d(array, k):
    return array.argpartition(k)[:k]


def get_lowest_indices_2d(array2d, k) -> np.array:
    return np.column_stack(np.unravel_index(array2d.flatten().argpartition(k)[:k], array2d.shape))


def get_highest_index_2d(array2d: np.array) -> np.array:
    return np.unravel_index(array2d.argmax(), array2d.shape)


def normalize_2d_array_sum(array, max_val):
    row_sums = array.max(axis=1)
    return (array / row_sums[:, np.newaxis]) * max_val


def oppose_values(array2d: np.array):
    max_val = array2d.max()
    return - array2d + max_val


def main():

    colors = "white, orange, magenta, light_blue, yellow, lime, pink, gray, light_gray, cyan, purple, blue, brown, " \
             "green, red, black".split(", ")

    glass_blocks = [Block(color + "_stained_glass") for color in colors]
    stone_gradient = [Block("blackstone"), Block("basalt"), Block("deepslate"),
                      Block("tuff"), Block("dead_bubble_coral_block"),
                      Block("andesite"), Block("diorite"), Block("calcite")]

    planks = [Block(wood_type + "_planks") for wood_type in ["dark_oak", "spruce", "oak", "birch"]]

    editor = Editor(buffering=True, bufferLimit=64000)

    # placeGradientBox(editor, Box((30, 70, 50), (10, 10, 1)), stone_gradient)

    stone_gradiant_placer = gradiantPlacer(editor, stone_gradient)
    planks_gradiant_placer = gradiantPlacer(editor, planks[::-1])

    def get_rampart_function():
        return gradiantPlacer(editor, [Block(name) for name in random.choice(
            [["diorite", "calcite", "polished_diorite"],
             ["polished_andesite", "andesite", "polished_andesite"],
             ["cobbled_deepslate", "polished_deepslate"],
             ["deepslate_bricks", "cracked_deepslate_bricks", "deepslate_bricks", "cracked_deepslate_bricks",
              "deepslate_bricks", "cracked_deepslate_bricks", "deepslate_bricks", "cracked_deepslate_bricks"],
             ["polished_blackstone", "blackstone", "polished_blackstone"]])])

    build_area = editor.getBuildArea()

    editor.loadWorldSlice(heightmapTypes=["WORLD_SURFACE"], cache=True)

    hmap = editor.worldSlice.heightmaps["WORLD_SURFACE"]
    sampling = 10
    urban_area_radius = 40
    variance_map, coord_converter = compute_variance_map(hmap, sampling=sampling, blur_size=urban_area_radius)

    debug_palette = [Block(color + "_stained_glass") for color in ["lime", "yellow", "red", "purple", "black"]][::-1]
    palette_size = len(debug_palette)

    normalized_variance_debug = normalize_2d_array_sum(variance_map, palette_size + 1)

    def coord_relative_to_absolute(x, z):
        return x + build_area.begin.x, z + build_area.begin.z

    def coord_absolute_to_relative(x, z):
        return x - build_area.begin.x, z - build_area.begin.z

    def get_associated_block(value):
        index = int(value)
        if index > palette_size - 1:
            return debug_palette[palette_size - 1]
        return debug_palette[index]

    def place_debug_hmap(score_map):
        for i in range(score_map.shape[0]):
            for j in range(score_map.shape[1]):
                x_rel, z_rel = coord_converter(i, j)
                x_abs, z_abs = coord_relative_to_absolute(x_rel, z_rel)
                editor.placeBlock((x_abs, hmap[x_rel, z_rel] - 1, z_abs), get_associated_block(score_map[i, j]))

    def coord2d_to_3d_surface(coord: CoordExplore, shift: tuple[int, int, int] = None):
        if shift is None:
            return coord.x, editor.worldSlice.heightmaps["WORLD_SURFACE"][coord.to_relative], coord.z
        return coord.x + shift[0], editor.worldSlice.heightmaps["WORLD_SURFACE"][coord.to_relative] + shift[
            1], coord.z + shift[2]

    def filter_in_build(coords):
        if not isinstance(coords, Sequence):
            coords = [coords]
        return filter(lambda coord: build_area.contains(coord.to_3d(0)), coords)

    def coord2d_to_ground_coord(x, z):
        return tuple(map(int, (x, hmap[tuple(map(int, coord_absolute_to_relative(x, z)))], z)))

    exclusion_radius = 0
    indices_urban_radius = 2 * math.ceil(urban_area_radius / sampling) + exclusion_radius

    flatness_factor = 3
    high_factor = 2
    centerness_factor = 1

    height_score = normalize_2d_array_sum(sample_array2d(hmap, sampling) * high_factor, 1)
    centerness_score = generate_decay_matrix(height_score.shape[0]) * centerness_factor
    flatness_score = oppose_values(normalize_2d_array_sum(variance_map, 1)) * flatness_factor
    occupation_score = np.ones(flatness_score.shape)

    castle_amount = 3
    for i in range(castle_amount):
        best_score = height_score * centerness_score * flatness_score * occupation_score
        best_indices = get_highest_index_2d(best_score)
        print(f"Best pos at {best_indices} with value {best_score[best_indices]}.")

        occupation_score[
        max(0, best_indices[0] - indices_urban_radius): min(occupation_score.shape[0], best_indices[0] + indices_urban_radius),
        max(0, best_indices[1] - indices_urban_radius): min(occupation_score.shape[1],
                                                         best_indices[1] + indices_urban_radius)] = 0

        best_coord = coord_relative_to_absolute(*coord_converter(*best_indices))
        if not best_coord:
            break

        build_castle(editor, best_coord, coord2d_to_ground_coord, stone_gradiant_placer, planks_gradiant_placer, get_rampart_function())

    # place_debug_hmap(normalize_2d_array_sum(height_score * centerness_score * flatness_score, palette_size + 1))

    # ground = editor.worldSlice.heightmaps["WORLD_SURFACE"][build_area.center[0] - build_area.begin[0],
    #                                                        build_area.center[2] - build_area.begin[2]]
    #
    # ground_pos = build_area.center.to_list()
    # ground_pos[1] = ground
    # print(build_area.center)
    #
    # ground_pos = ivec3(*ground_pos)
    # print(ground_pos)
    #
    # placeGradient(editor, geometry.line3D(ground_pos, build_area.center, 3),
    #               ground,
    #               distance(ground_pos, build_area.center), stone_gradient)


if __name__ == '__main__':
    main()
    exit(0)

    with cProfile.Profile() as pr:
        main()

    stats = pstats.Stats(pr)
    stats.sort_stats(pstats.SortKey.TIME)
    stats.print_stats()
    stats.dump_stats(filename='profiler.prof')
