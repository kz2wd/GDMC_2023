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

import territory
from PlacementMap import PlacementMap, NoValidPositionException
from blob_expand import CoordExplore
from castle_geo import placeGradientBox, placeGradient, build_castle, gradiantPlacer, build_tower_ring
from utils import shift_on_side, coord_normalize


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

    placement_map = PlacementMap(editor)
    # placement_map.show_steep_map([Block(color + "_concrete") for color in ["black", "purple", "red", "orange", "green", "lime", "white"]], 1, 40)
    # editor.flushBuffer()
    # input()

    stone_gradiant_placer = placement_map.occupy_on_place(gradiantPlacer(editor, stone_gradient))
    planks_gradiant_placer = placement_map.occupy_on_place(gradiantPlacer(editor, planks[::-1]))

    def get_rampart_function():
        return placement_map.occupy_on_place(gradiantPlacer(editor, [Block(name) for name in random.choice(
            [["diorite", "calcite", "polished_diorite"],
             ["polished_andesite", "andesite", "polished_andesite"],
             ["cobbled_deepslate", "polished_deepslate"],
             ["deepslate_bricks", "cracked_deepslate_bricks", "deepslate_bricks", "cracked_deepslate_bricks",
              "deepslate_bricks", "cracked_deepslate_bricks", "deepslate_bricks", "cracked_deepslate_bricks"],
             ["polished_blackstone", "blackstone", "polished_blackstone"]])]))

    build_area = editor.getBuildArea()

    debug_palette = [Block(color + "_concrete") for color in ["lime", "yellow", "red", "purple", "black"]][::-1]
    palette_size = len(debug_palette)

    def get_associated_block(value):
        index = int(value)
        if index > palette_size - 1:
            return debug_palette[palette_size - 1]
        return debug_palette[index]

    # def place_debug_hmap(score_map):
    #     for i in range(score_map.shape[0]):
    #         for j in range(score_map.shape[1]):
    #             x_rel, z_rel = coord_converter(i, j)
    #             x_abs, z_abs = coord_relative_to_absolute(x_rel, z_rel)
    #             editor.placeBlock((x_abs, hmap[x_rel, z_rel] - 1, z_abs), get_associated_block(score_map[i, j]))

    def filter_in_build(coords):
        if not isinstance(coords, Sequence):
            coords = [coords]
        return filter(lambda coord: build_area.contains(coord.to_3d(0)), coords)

    def batiment_builder(center, radius):
        build_castle(editor, center, placement_map.coord2d_to_ground_coord, stone_gradiant_placer,
                     planks_gradiant_placer,
                     get_rampart_function(), castle_radius=radius, ring_amount=random.choice([2, 3]))

    territory.build_territories(placement_map, batiment_builder)
    editor.flushBuffer()
    exit(0)

    try_amount = 3
    castle_radius = random.randint(40, 60)
    for i in range(try_amount):

        print(f"Castle size : {castle_radius}")
        try:
            x, z = placement_map.get_build_coordinates_2d(castle_radius)
        except NoValidPositionException:
            print(f"Retrying with smaller castle")
            castle_radius -= 7
            continue

        print(f"Found Building coordinate ({x}, {z}).")

        build_castle(editor, (x, z), placement_map.coord2d_to_ground_coord, stone_gradiant_placer, planks_gradiant_placer,
                     get_rampart_function(), castle_radius=castle_radius, ring_amount=random.choice([2, 3]))
        editor.flushBuffer()

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
