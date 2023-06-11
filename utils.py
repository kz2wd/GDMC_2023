import math
import random
from operator import sub, truediv, mul, add


def circle_around(center: tuple[int, int], radius: int, amount_of_points: int):
    angle_offset = random.random() * 2 * math.pi
    for i in range(amount_of_points):
        angle = i * 2 * math.pi / amount_of_points + angle_offset
        yield int(math.cos(angle) * radius + center[0]), int(math.sin(angle) * radius + center[1])


def increase_y(coord, increase):
    return coord[0], coord[1] + increase, coord[2]


def with_y(coord, y):
    return coord[0], y, coord[2]


def get_norm(coord):
    return math.sqrt(sum(map(lambda x: x*x, coord)))


def coord_scalar_op(coord, scalar):
    return lambda op: tuple(map(lambda u: op(u, scalar), coord))


def coord_scalar_div(coord, scalar):
    return coord_scalar_op(coord, scalar)(truediv)


def coord_scalar_mul(coord, scalar):
    return coord_scalar_op(coord, scalar)(mul)


def coords_operation(coord1, coord2):
    return lambda op: tuple(map(op, coord1, coord2))


def coords_sub(coord1, coord2):
    return coords_operation(coord1, coord2)(sub)


def coords_add(coord1, coord2):
    return coords_operation(coord1, coord2)(add)


def coord_int(coord):
    return tuple(map(int, coord))


def get_normalized_direction(coord1, coord2):
    direction = coords_sub(coord1, coord2)
    return coord_normalize(direction)


def coord_normalize(vector):
    return coord_scalar_div(vector, get_norm(vector))


def perpendicular_vector(vector):
    x, y, z = vector
    return -z, y, x


def shift_on_side(vector, shift_length):
    return coord_scalar_mul(coord_normalize(perpendicular_vector(vector)), shift_length)


def coord_in_area(coord, center, radius):
    if len(coord) == 2:
        return center[0] - radius <= coord[0] <= center[0] + radius \
            and center[1] - radius <= coord[1] <= center[1] + radius
    if len(coord) == 3:
        return coord_in_area((coord[0], coord[2]), center, radius)
    return False


def coord3d_list_to_2d(coords):
    return list(map(lambda c: (c[0], c[2]), coords))
