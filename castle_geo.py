import math
import random
import time
from typing import Union

from gdpc import Editor, Box, Block


def placeGradient(editor: Editor, iterator, comp, size, blocks: list[Block]):
    block_amount = len(blocks)
    thickness = size / block_amount

    fun = lambda x, idx: math.sin(x * random.randint(1, 5) * 10) * math.sin(x * 100) * thickness + (idx * thickness) + 5

    def get_block(position):
        for i in range(block_amount):
            if fun(position[0] + position[2], i) > position[1] - comp:
                return i
        return block_amount - 1

    for position in iterator:

        i = get_block(position)
        editor.placeBlock(position, blocks[i])


def placeGradientBox(editor: Editor, box: Box, blocks: list[Block]) -> None:
    placeGradient(editor, box.shell, box.begin[1], box.size[1], blocks)

