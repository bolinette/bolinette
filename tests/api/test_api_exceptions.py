from bolinette.api.exceptions import ApiError
from bolinette.core.exceptions import BolinetteError, ParameterError


class Ctrl:
    pass


class Entity:
    pass


class TestApiError:
    def test_a_bare_message(self) -> None:
        err = ApiError("boom")

        assert err.message == "boom"
        assert isinstance(err, BolinetteError)
        assert isinstance(err, ParameterError)

    def test_the_controller_is_prefixed(self) -> None:
        err = ApiError("boom", controller=Ctrl)

        assert err.message == f"Controller {Ctrl}, boom"

    def test_the_route_is_prefixed(self) -> None:
        err = ApiError("boom", route="get_all")

        assert err.message == "Route 'get_all', boom"

    def test_the_entity_is_prefixed(self) -> None:
        err = ApiError("boom", entity=Entity)

        assert err.message == f"Entity {Entity}, boom"

    def test_every_parameter_keeps_its_order(self) -> None:
        err = ApiError("boom", controller=Ctrl, route="get_all", entity=Entity)

        assert err.message == f"Controller {Ctrl}, Route 'get_all', Entity {Entity}, boom"
        assert str(err) == err.message
