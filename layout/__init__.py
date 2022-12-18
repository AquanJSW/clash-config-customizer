from typing import Sequence, Union
from .arguments import parse_args
from .layout import set_layout, Layout


def get_layout(init_args: Union[None, Sequence[str]] = None):
    args = parse_args(init_args=init_args)
    set_layout(args=args)
    return Layout
