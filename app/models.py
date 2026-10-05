from typing import TypedDict


class Chapter(TypedDict):
    path: str
    content: str


type Chapters = list[Chapter]
