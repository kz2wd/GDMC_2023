import math
import random
from operator import sub, truediv, mul, add


def circle_around(center: tuple[int, int], radius: int, amount_of_points: int):
    angle_offset = random.random() * 2 * math.pi
    for i in range(amount_of_points):
        angle = i * 2 * math.pi / amount_of_points + angle_offset
        yield math.cos(angle) * radius + center[0], math.sin(angle) * radius + center[1]


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
