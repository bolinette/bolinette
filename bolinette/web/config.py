class BlntAuthProps:
    def __init__(self, ctrl_path: str, route_path: str) -> None:
        self.ctrl_path = ctrl_path
        self.route_path = route_path


class WebConfig:
    def __init__(self) -> None:
        self.use_sockets = False
        self.blnt_auth: BlntAuthProps | None = None
