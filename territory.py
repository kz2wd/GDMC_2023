import random

from gdpc import Block

import castle_geo
from PlacementMap import PlacementMap, NoValidPositionException
from blob_expand import blob_expand, CoordExplore


def build_territories(placement_map: PlacementMap, batiment_builder):

    def coord2d_to_3d_surface(coord: CoordExplore, shift: tuple[int, int, int] = None):
        if shift is None:
            return coord.x, placement_map.height_map[coord.to_relative], coord.z
        return coord.x + shift[0], placement_map.height_map[coord.to_relative] + shift[
            1], coord.z + shift[2]

    debug_palette = [Block(color + "_concrete") for color in ["lime", "yellow", "red", "purple", "black"]]
    palette_size = len(debug_palette)

    district_amount = 20
    district_centers = []
    district_radius = []
    occupied_coords = set()
    for i in range(district_amount):
        district_size = random.randint(20, 60)
        try:
            x, z = placement_map.get_build_coordinates_2d(district_size)
            district_centers.append((x, z))
            district_radius.append(district_size)
        except NoValidPositionException as e:
            print(f"{e.args}")
            continue
        district_coords = blob_expand(placement_map.build_area, placement_map.height_map, (x, z), max_distance=district_size, max_rel_diff=1, max_abs_diff=15, excluded_coords_set=occupied_coords)
        for c in district_coords:
            occupied_coords.add(c)
        block_index = i % palette_size
        print("Adding district")
        for coord in district_coords:
            placement_map.occupy_coordinate(coord.x, coord.z)
            placement_map.editor.placeBlock(coord2d_to_3d_surface(coord, [0, -1, 0]), debug_palette[block_index])

    for a, b in zip(district_centers[1:], district_centers[:-1]):
        placement_map.compute_roads(a, b)

    for center, radius in zip(district_centers, district_radius):
        batiment_builder(center, radius)

