import random

from gdpc import Block

import castle_geo
from PlacementMap import PlacementMap, NoValidPositionException
from blob_expand import blob_expand, CoordExplore
from utils import coord3d_list_to_2d


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
    for district_size, tolerance in [(70, 0.01)]:
        try:
            x, z = placement_map.get_build_coordinates_2d(district_size, allow_next_to_occupied_zone=True, apply_bonus=True, min_score=tolerance, flatness_factor=3, height_factor=.5, centerness_factor=1.3, sampling=15)
            district_centers.append((x, z))
            district_radius.append(district_size)
        except NoValidPositionException as e:
            print(f"{e.args}")
            continue
        district_coords = blob_expand(placement_map.build_area, placement_map.height_map, (x, z), max_distance=district_size, max_rel_diff=1, max_abs_diff=15, excluded_coords_set=occupied_coords)
        for c in district_coords:
            occupied_coords.add(c)
        block = random.choice(debug_palette)
        print("Adding district")
        for coord in district_coords:
            placement_map.occupy_coordinate(coord.x, coord.z)
            # placement_map.editor.placeBlock(coord2d_to_3d_surface(coord, [0, -1, 0]), block)

    for a, b in zip(district_centers[1:], district_centers[:-1]):
        placement_map.compute_roads(a, b)

    for center, radius in zip(district_centers, district_radius):
        castle = batiment_builder(center, radius)

        generate_roads_around(placement_map, castle, center, radius * 1.5, 5)


def generate_roads_around(placement_map, castle, center, radius, road_amount):
    if not castle.rings[-1].gates:
        return
    for point in placement_map.random_point_on_map(road_amount, center, radius, road_amount):
        placement_map.compute_roads(coord3d_list_to_2d(castle.rings[-1].gates), point)

