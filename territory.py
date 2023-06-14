from gdpc import Block

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

    district_centers = []
    district_radius = []
    occupied_coords = set()
    for district_size, tolerance in [(70, 0.01)]:
        try_amount = 50
        found_position = False
        print("Computing castle size", end="")
        while try_amount > 0 and not found_position:
            try:
                print(":", end="")
                x, z = placement_map.get_build_coordinates_2d(district_size, allow_next_to_occupied_zone=True, apply_bonus=True, min_score=tolerance, flatness_factor=3, height_factor=.5, centerness_factor=1.3, sampling=15)
                district_centers.append((x, z))
                district_radius.append(district_size)
                found_position = True
            except NoValidPositionException as e:
                district_size -= 2
                continue
        if not found_position:
            print("\nNo valid size found, exiting")
            return
        print(f"\nFound spot of radius {district_size} at ({x}, {z})")
        district_coords = blob_expand(placement_map.build_area, placement_map.height_map, (x, z), max_distance=district_size, max_rel_diff=1, max_abs_diff=15, excluded_coords_set=occupied_coords)
        for c in district_coords:
            occupied_coords.add(c)
        for coord in district_coords:
            placement_map.occupy_coordinate(coord.x, coord.z)
            # placement_map.editor.placeBlock(coord2d_to_3d_surface(coord, [0, -1, 0]), block)

    for a, b in zip(district_centers[1:], district_centers[:-1]):
        print("Computing roads between district")
        placement_map.compute_roads(a, b)

    for center, radius in zip(district_centers, district_radius):
        castle = batiment_builder(center, radius)

        generate_roads_around(placement_map, castle, center, radius * 1.5, 15)


def generate_roads_around(placement_map, castle, center, radius, road_amount):
    print("Generating roads around the build area")
    print("This step can last a while as it scale badly with build area size")
    print("Terminate the program if it last too long")
    if not castle.rings[-1].gates:
        return
    for point in placement_map.random_point_on_map(road_amount, center, radius, road_amount):
        print("_", end="")
        placement_map.compute_roads(coord3d_list_to_2d(castle.rings[-1].gates), point)
        road_pattern = {"INNER": {"stone": 1.0},
                        "MIDDLE": {"stone": 1.0},
                        "OUTER": {"stone": 1.0}}
        placement_map.build_roads(road_pattern)
        placement_map.editor.flushBuffer()
    print("Road generation over")
