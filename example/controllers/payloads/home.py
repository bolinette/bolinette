from dataclasses import dataclass


@dataclass(init=False)
class HomeHelloPayload:
    firstname: str
    lastname: str
    age: int
