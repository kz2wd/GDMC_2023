from __future__ import annotations

import math
import random
from typing import List, Any, Sequence
import termcolor

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
from castle_geo import placeGradientBox, placeGradient, gradiantPlacer, Castle
from utils import shift_on_side, coord_normalize


def main():
    colors = "white, orange, magenta, light_blue, yellow, lime, pink, gray, light_gray, cyan, purple, blue, brown, " \
             "green, red, black".split(", ")

    glass_blocks = [Block(color + "_stained_glass") for color in colors]
    stone_gradient = [Block("blackstone"), Block("basalt"), Block("deepslate"),
                      Block("tuff"), Block("dead_bubble_coral_block"),
                      Block("andesite"), Block("diorite"), Block("calcite")]

    planks = [Block(wood_type + "_planks") for wood_type in ["dark_oak", "spruce", "oak", "birch"]]

    editor = Editor(buffering=True, bufferLimit=64000, multithreading=True)

    placement_map = PlacementMap(editor)

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

    def batiment_builder(center, radius):
        c = Castle(center, radius, 7, placement_map)
        c.build_castle(editor, placement_map.coord2d_to_ground_coord,
                       stone_gradiant_placer, planks_gradiant_placer,
                       get_rampart_function())
        return c

    def house_builder(center, radius):
        x, y, z = center
        geometry.placeBoxHollow(editor, Box((x - radius, y, z - radius), (radius * 2, radius * 2, radius * 2)), Block('oak_planks'))

    territory.build_territories(placement_map, batiment_builder)

    editor.flushBuffer()
    print("It may seems as nothing is happening but the editor is surely placing blocks")
    print("Wait a bit or kill the process if it last too long")


if __name__ == '__main__':
    main()
    print("Generation about to end, thank you for using this castle generator.")


