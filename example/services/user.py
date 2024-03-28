from bolinette.core.injection import injectable
from bolinette.core.injection.decorators import init_method


@injectable()
class UserService:
    @init_method
    def _init_service(self) -> None: ...
