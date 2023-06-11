import random

import networkx
import networkx as nx
import numpy as np
from gdpc import Editor, Block

from utils import increase_y, coord_in_area


class NoValidPositionException(Exception):
    pass


directions_ortho = [(1, 0), (-1, 0), (0, 1), (0, -1)]
directions_diag = (1, 1), (-1, 1), (-1, -1), (1, -1)


class PlacementMap:

    def __init__(self, editor: Editor, default_precision=1):
        self.editor = editor
        self.default_precision = default_precision
        self.build_area = editor.getBuildArea()

        self.height_map = self.sample_array2d(self.__get_heightmap_no_trees(),
                                              self.default_precision)
        self.occupation_map = np.ones_like(self.height_map)
        self.bonus_map = np.ones_like(self.height_map, dtype=np.float64)
        self.graph: networkx.Graph | None = None

    def __get_heightmap_no_trees(self) -> np.ndarray:
        """Return a list of block representing a heightmap without trees

        It is not perfect as sometimes, there can be flower or grass or other blocks between the ground and the '
        floating' logs, but it is good enough for our use"""
        self.editor.loadWorldSlice(heightmapTypes=["MOTION_BLOCKING_NO_LEAVES"], cache=True)
        heightmap = self.editor.worldSlice.heightmaps["MOTION_BLOCKING_NO_LEAVES"]

        for x, rest in enumerate(heightmap):
            for z, h in enumerate(rest):
                base_coord = (self.build_area.begin.x + x, h - 1, self.build_area.begin.z + z)

                ground_coord = None
                # To get to the last block until the ground
                for ground_coord in self.__yield_until_ground(base_coord):
                    pass
                if ground_coord:
                    heightmap[x, z] = ground_coord[1]

        return heightmap

    @staticmethod
    def __any_pattern_in(patterns, _str):
        for p in patterns:
            if p in _str:
                return True
        return False

    def __yield_until_ground(self, coordinates):
        """Yield the coordinates """
        current_coord = coordinates
        while self.__any_pattern_in(('air', 'leaves', 'log', 'vine', 'bamboo'), self.editor.getBlock(current_coord).id):
            yield current_coord
            current_coord = increase_y(current_coord, -1)

    def indexes_to_local_coord(self, i, j, sampling_used):
        return i * self.default_precision * sampling_used, j * self.default_precision * sampling_used

    def compute_variance_map(self, sampling=5, blur_size=3):
        hmap = self.height_map
        return np.array([[np.nanvar(hmap[max(i - blur_size, 0): min(i + blur_size, hmap.shape[0]),
                                    max(j - blur_size, 0): min(j + blur_size, hmap.shape[1])].flatten()) for
                          j in range(0, hmap.shape[1], sampling)] for i in range(0, hmap.shape[0], sampling)])

    def coord_relative_to_absolute(self, x, z):
        return x + self.build_area.begin.x, z + self.build_area.begin.z

    def coord_absolute_to_relative(self, x, z):
        return x - self.build_area.begin.x, z - self.build_area.begin.z

    def coord2d_to_ground_coord(self, x, z):
        return tuple(map(int, (x, self.height_map[tuple(map(int, self.coord_absolute_to_relative(x, z)))], z)))

    @staticmethod
    def sample_array2d(array2d, sampling):
        return array2d[::sampling, ::sampling]

    @staticmethod
    def generate_decay_matrix(size):
        center = (size - 1) / 2
        x, y = np.indices((size, size))
        distance = np.sqrt((x - center) ** 2 + (y - center) ** 2)
        normalized_values = (np.max(distance) - distance) / np.max(distance)
        return normalized_values

    @staticmethod
    def get_lowest_indices_1d(array, k):
        return array.argpartition(k)[:k]

    @staticmethod
    def get_lowest_indices_2d(array2d, k) -> np.array:
        return np.column_stack(np.unravel_index(array2d.flatten().argpartition(k)[:k], array2d.shape))

    @staticmethod
    def get_highest_index_2d(array2d: np.array) -> np.array:
        return np.unravel_index(array2d.argmax(), array2d.shape)

    @staticmethod
    def normalize_2d_array_sum(array, max_val):
        row_sums = array.max(axis=1)
        return (array / row_sums[:, np.newaxis]) * max_val

    @staticmethod
    def oppose_values(array2d: np.array):
        max_val = array2d.max()
        return - array2d + max_val

    def get_flatness_score(self, sampling, blur, factor):
        return self.oppose_values(self.normalize_2d_array_sum(self.compute_variance_map(sampling, blur), 1)) * factor

    def get_centerness_score(self, shape, factor):
        return self.generate_decay_matrix(shape[0]) * factor

    def get_height_score(self, sampling, factor):
        return self.normalize_2d_array_sum(self.sample_array2d(self.height_map, sampling), factor)

    @staticmethod
    def convolut_map(_map, sampling, blur, convolut_fct):
        return np.array([[convolut_fct(_map[max(i - blur, 0): min(i + blur, _map.shape[0]),
                          max(j - blur, 0): min(j + blur, _map.shape[1])].flatten()) for
                   j in range(0, _map.shape[1], sampling)] for i in range(0, _map.shape[0], sampling)])

    def get_occupation_score(self, sampling, blur):
        _map = self.occupation_map
        return self.convolut_map(_map, sampling, blur, np.min)

    def get_bonus_score(self, sampling, blur, factor):
        return self.convolut_map(self.bonus_map, sampling, blur, np.sum) * factor

    def occupy_area(self, i, j, sampling, radius):
        i *= sampling
        j *= sampling
        self.occupation_map[max(i - radius, 0): min(i + radius, self.occupation_map.shape[0]),
        max(j - radius, 0): min(j + radius, self.occupation_map.shape[1])] = 0

    def show_steep_map(self, blocks, sampling, blur):
        palette_size = len(blocks)
        steep_map = self.normalize_2d_array_sum(self.get_flatness_score(blur, sampling, 1), palette_size)

        def get_associated_block(value):
            index = int(value)
            if index > palette_size - 1:
                return blocks[palette_size - 1]
            return blocks[index]

        for i in range(steep_map.shape[0]):
            for j in range(steep_map.shape[1]):
                x, z = self.coord_relative_to_absolute(i, j)
                self.editor.placeBlock(self.coord2d_to_ground_coord(x, z), get_associated_block(steep_map[i, j]))

    @staticmethod
    def iterate_over_2d_map(map2d):
        for i in range(map2d.shape[0]):
            for j in range(map2d.shape[1]):
                yield i, j

    def yield_surface_coords(self):
        for i, j in self.iterate_over_2d_map(self.height_map):
            yield i, self.height_map[(i, j)], j

    def occupy_coordinate(self, x, z):
        self.occupation_map[self.coord_absolute_to_relative(x, z)] = 0

    def get_score_map(self, radius, sampling, flatness_factor, height_factor, centerness_factor, bonus_factor, allow_next_to_occupied_zone):
        height_score = self.get_height_score(sampling, height_factor)
        return height_score \
            * self.get_centerness_score(height_score.shape, centerness_factor) \
            * self.get_flatness_score(sampling, radius, flatness_factor) \
            * self.get_occupation_score(sampling, radius if allow_next_to_occupied_zone else 2 * radius) \
            * self.get_exclusion_score(height_score.shape, int(radius / sampling)) \
            * self.get_bonus_score(sampling, sampling, bonus_factor)

    def add_bonus_on_area(self, indexes, radius, bonus):
        i, j = indexes
        for a in range(max(0, i - radius), min(self.bonus_map.shape[0], i + radius)):
            for b in range(max(0, j - radius), min(self.bonus_map.shape[1], j + radius)):
                self.bonus_map[a, b] *= bonus

    def debug_occupation_area(self):
        for i in range(self.occupation_map.shape[0]):
            for j in range(self.occupation_map.shape[1]):
                x, z = self.coord_relative_to_absolute(i, j)
                block = Block("lime_stained_glass") if self.occupation_map[i, j] else Block("red_stained_glass")
                self.editor.placeBlock(self.coord2d_to_ground_coord(x, z), block)

    def get_build_coordinates_2d(self, radius, sampling=None, flatness_factor=1, height_factor=1, centerness_factor=1,
                                 bonus_factor=1,
                                 min_score=.1, allow_next_to_occupied_zone=False, apply_bonus=None):
        if sampling is None:
            sampling = radius

        score_map = self.get_score_map(radius, sampling, flatness_factor, height_factor, centerness_factor, bonus_factor,
                                       allow_next_to_occupied_zone)
        i, j = self.get_highest_index_2d(score_map)
        if score_map[i, j] < min_score:
            raise NoValidPositionException("No valid position found")
        if apply_bonus:
            self.add_bonus_on_area((i, j), int(1.1 * radius), 5)
        # self.occupy_area(i, j, sampling, radius)
        # self.debug_occupation_area()
        return self.coord_relative_to_absolute(*self.indexes_to_local_coord(i, j, sampling))

    def occupy_on_place(self, place_function):
        def new_place_function(coord_iter):
            coord_list = list(coord_iter)
            for coord in coord_list:
                if not self.build_area.contains(coord):
                    continue
                self.occupation_map[self.coord_absolute_to_relative(coord[0], coord[2])] = 0
            place_function(coord_list)

        return new_place_function

    @staticmethod
    def coord2d_neighbors(coord2d, directions):
        for d in directions:
            yield coord2d[0] + d[0], coord2d[1] + d[1]

    def fill_graph(self):
        self.graph = nx.Graph()

        for coord in self.yield_surface_coords():
            coord = self.coord_relative_to_absolute(coord[0], coord[2])
            self.graph.add_node(coord)

        for coordinates in self.graph.nodes.keys():
            for directions, factor in [(directions_ortho, 1), (directions_diag, 2)]:
                for coord in self.coord2d_neighbors(coordinates, directions):
                    if coord in self.graph.nodes.keys():
                        self.graph.add_edge(coordinates, coord, weight=(100 + (abs(
                            self.height_map[self.coord_absolute_to_relative(*coord)] - self.height_map[
                                self.coord_absolute_to_relative(*coordinates)]) * 10) ** 2) * factor)

    def compute_roads(self, start, end) -> bool:
        if self.graph is None:
            self.fill_graph()

        try:
            if len(start) == 1:
                path = nx.dijkstra_path(self.graph, start, end)
            else:
                path = nx.multi_source_dijkstra(self.graph, start, end)[1]

        except nx.NetworkXException:
            print("No path found !")
            return False
        for coord in path:
            self.editor.placeBlock(self.coord2d_to_ground_coord(*coord), Block("emerald_block"))

        # Update weights to use the roads
        for c1, c2 in zip(path[:-2], path[1:]):
            if self.graph.has_edge(c1, c2):
                self.graph[c1][c2]['weight'] *= .5

    @staticmethod
    def get_exclusion_score(shape, radius):
        exclusion = np.ones(shape)
        exclusion[:radius, :] = 0
        exclusion[:, :radius] = 0
        exclusion[:, -radius:] = 0
        exclusion[-radius:, :] = 0
        return exclusion

    def random_point_on_map(self, point_amount, excluded_center, excluded_radius, try_amount=None):
        if try_amount is None:
            try_amount = 2 * point_amount

        max_x, max_z = self.build_area.size[0], self.build_area.size[2]
        correct_points = 0
        tries = 0
        while correct_points < point_amount and tries < try_amount:
            x, z = self.coord_relative_to_absolute(random.randint(0, max_x), random.randint(0, max_z))
            if not coord_in_area((x, z), excluded_center, excluded_radius):
                correct_points += 1
                yield x, z

            tries += 1
