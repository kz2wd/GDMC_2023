from __future__ import annotations

import math
import random
from typing import Any


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


def blob_expand(build_area, hmap, start: tuple[int, int], max_rel_diff=1, max_abs_diff=5, max_distance=5,
                excluded_coords_set=None) -> list[
    CoordExplore | Any]:
    start = CoordExplore(start[0], start[1], build_area)
    blob = [start]
    to_explore = [start]
    explored = {start}
    if excluded_coords_set is not None:
        explored = excluded_coords_set
        explored.add(start)

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


def from_angle(angle, radius, offset):
    return int(math.cos(angle) * radius + offset[0]), int(math.sin(angle) * radius + offset[1])


def get_borders(coord_area, center, point_amount, max_radius):
    angle_offset = random.random() * 2 * math.pi
    for i in range(point_amount):
        angle = i * 2 * math.pi / point_amount + angle_offset
        # raycast
        radius = 0
        coord = from_angle(angle, radius, center)
        radius += 1
        next_coord = from_angle(angle, radius, center)
        while next_coord in coord_area and radius <= max_radius:
            radius += 1
            coord = next_coord
            next_coord = from_angle(angle, radius, center)

        yield coord


def get_borders_from_outside(coord_area, center, point_amount, max_radius):
    angle_offset = random.random() * 2 * math.pi
    for i in range(point_amount):
        angle = i * 2 * math.pi / point_amount + angle_offset
        # raycast from outside
        radius = max_radius
        coord = from_angle(angle, radius, center)
        while coord not in coord_area and radius > 0:
            radius -= 1
            coord = from_angle(angle, radius, center)

        yield coord
