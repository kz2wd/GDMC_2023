import math
import random


def circle_around(center: tuple[int, int], radius: int, amount_of_points: int):
    angle_offset = random.random() * 2 * math.pi
    for i in range(amount_of_points):
        angle = i * 2 * math.pi / amount_of_points + angle_offset
        yield math.cos(angle) * radius + center[0], math.sin(angle) * radius + center[1]


def increase_y(coord, increase):
    return coord[0], coord[1] + increase, coord[2]
