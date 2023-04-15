from typing import Callable, List, TypeVar, Union

T = TypeVar("T")


def list_find(list: List[T], fn: Callable[[T], bool]) -> Union[T, None]:
    for i, v in enumerate(list):
        if fn(v):
            return list[i]
