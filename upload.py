from typing import List, TypedDict, Union


class ImageSize(TypedDict):

    size: int
    blob: bytes
    format: str


class Upload(TypedDict):

    id: str
    name: str
    type: str
    author: str
    blob: bytes
    sizes: Union[List[ImageSize], None]
