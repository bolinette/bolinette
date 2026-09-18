from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BlntAuthOptions:
    controller_path: str = "auth"
    route_path: str = ""
