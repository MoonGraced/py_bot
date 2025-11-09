from dataclasses import dataclass


@dataclass(frozen=True)
class Streamer:
    url: str
    nick: str
    status: str
