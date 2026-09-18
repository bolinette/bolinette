"""Configuration loading from files and OS variables, and typed configuration sections."""

from pathlib import Path

import pydantic
import pytest
from escondite import Cache
from soupape import AsyncInjector, ServiceCollection

from bolinette.core import CoreExtension, startup
from bolinette.core.configuration import (
    BaseConfiguration,
    ConfigSection,
    Configuration,
    ConfigurationOptions,
    CoreConfigSection,
    config_section,
    resolve_config_section,
)
from bolinette.core.exceptions import ConfigurationError, InitError
from bolinette.core.mapping import BolinetteModel
from tests.core.conftest import AppFactory


@config_section("app")
class AppSection(BolinetteModel):
    name: str = "default"
    port: int = 8000
    nested: dict[str, str] | None = None


class NotASection(BolinetteModel):
    pass


def _write(env_folder: Path, name: str, content: str) -> None:
    (env_folder / name).write_text(content)


async def _configuration(base: BaseConfiguration | None = None) -> Configuration:
    services = ServiceCollection()
    services.add_singleton(ConfigurationOptions, lambda: ConfigurationOptions())
    services.add_singleton(Configuration)
    if base is not None:
        services.add_singleton(BaseConfiguration, lambda: base)
    async with AsyncInjector(services) as injector:
        return await injector.require(Configuration)


async def _section[T: BolinetteModel](section_type: type[T]) -> ConfigSection[T]:
    services = ServiceCollection()
    services.add_singleton(ConfigurationOptions, lambda: ConfigurationOptions())
    services.add_singleton(Configuration)
    services.add_singleton(resolve_config_section)
    async with AsyncInjector(services) as injector:
        return await injector.require(ConfigSection[section_type])


class TestProfile:
    async def test_default_profile(self, env_folder: Path) -> None:
        """Without a `.profile` file the profile is `development`."""
        config = await _configuration()

        assert config.profile == "development"

    async def test_profile_from_file(self, env_folder: Path) -> None:
        """The first line of `env/.profile` selects the profile."""
        _write(env_folder, ".profile", "production\nignored\n")

        config = await _configuration()

        assert config.profile == "production"

    async def test_no_env_folder(self, tmp_cwd: Path) -> None:
        """A missing `env/` folder yields an empty configuration."""
        config = await _configuration()

        assert config.profile == "development"
        assert config.config == {}


class TestFiles:
    async def test_env_toml_is_loaded(self, env_folder: Path) -> None:
        """`env.toml` sections are loaded as nested dictionaries."""
        _write(env_folder, "env.toml", '[app]\nname = "from-env"\n')

        config = await _configuration()

        assert config.config == {"app": {"name": "from-env"}}

    async def test_profile_file_overrides_env_toml(self, env_folder: Path) -> None:
        """`env.<profile>.toml` overrides keys from `env.toml` and keeps the others."""
        _write(env_folder, "env.toml", '[app]\nname = "base"\nport = 1\n')
        _write(env_folder, "env.development.toml", '[app]\nname = "dev"\n')

        config = await _configuration()

        assert config.config == {"app": {"name": "dev", "port": 1}}

    async def test_local_file_overrides_profile_file(self, env_folder: Path) -> None:
        """`env.local.<profile>.toml` has the highest precedence among files."""
        _write(env_folder, "env.toml", '[app]\nname = "base"\n')
        _write(env_folder, "env.development.toml", '[app]\nname = "dev"\n')
        _write(env_folder, "env.local.development.toml", '[app]\nname = "local"\n')

        config = await _configuration()

        assert config.config["app"]["name"] == "local"

    async def test_other_profile_files_are_ignored(self, env_folder: Path) -> None:
        """Files of another profile are not read."""
        _write(env_folder, ".profile", "test")
        _write(env_folder, "env.development.toml", '[app]\nname = "dev"\n')
        _write(env_folder, "env.test.toml", '[app]\nname = "test"\n')

        config = await _configuration()

        assert config.config["app"]["name"] == "test"

    async def test_sections_are_merged(self, env_folder: Path) -> None:
        """Different files can contribute different sections."""
        _write(env_folder, "env.toml", '[app]\nname = "base"\n')
        _write(env_folder, "env.development.toml", "[core]\ndebug = true\n")

        config = await _configuration()

        assert config.config == {"app": {"name": "base"}, "core": {"debug": True}}


class TestOsVariables:
    async def test_prefixed_variables_are_loaded(self, env_folder: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """`BLNT_<SECTION>__<KEY>` variables populate the matching section, lower-cased."""
        monkeypatch.setenv("BLNT_APP__NAME", "from-os")

        config = await _configuration()

        assert config.config["app"]["name"] == "from-os"

    async def test_deeper_paths(self, env_folder: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Extra `__` separators create nested dictionaries."""
        monkeypatch.setenv("BLNT_APP__NESTED__KEY", "value")

        config = await _configuration()

        assert config.config["app"]["nested"] == {"key": "value"}

    async def test_unprefixed_variables_are_ignored(self, env_folder: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Variables without the `BLNT_` prefix are not read."""
        monkeypatch.setenv("APP__NAME", "nope")

        config = await _configuration()

        assert "app" not in config.config

    async def test_files_override_os_variables(self, env_folder: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Values from files take precedence over OS variables."""
        monkeypatch.setenv("BLNT_APP__NAME", "from-os")
        _write(env_folder, "env.toml", '[app]\nname = "from-file"\n')

        config = await _configuration()

        assert config.config["app"]["name"] == "from-file"

    async def test_conflicting_variables_raise(self, env_folder: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """A variable that is both a value and a parent of other values is an error."""
        monkeypatch.setenv("BLNT_APP__NESTED", "value")
        monkeypatch.setenv("BLNT_APP__NESTED__KEY", "value")

        with pytest.raises(ConfigurationError, match="conflicts"):
            await _configuration()


class TestEnvFolderOption:
    async def test_core_extension_env_folder(self, make_app: AppFactory, cache: Cache, tmp_path: Path) -> None:
        """`CoreExtension(env_folder=...)` reads the configuration from that folder instead of `cwd/env`."""
        folder = tmp_path / "elsewhere"
        folder.mkdir()
        _write(folder, "env.toml", '[app]\nname = "from-option"\n')
        seen: list[Configuration] = []

        @startup(cache=cache)
        async def init(config: Configuration) -> None:
            seen.append(config)

        blnt = await make_app([CoreExtension(env_folder=folder)])
        await blnt.startup()

        assert seen[0].config["app"]["name"] == "from-option"


class TestBaseConfig:
    async def test_base_config_is_lowest_precedence(self, env_folder: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """An `BaseConfiguration` provides defaults that every other source overrides."""
        base = BaseConfiguration({"app": {"name": "base", "port": 1}, "other": {"key": "kept"}})
        monkeypatch.setenv("BLNT_APP__NAME", "from-os")

        config = await _configuration(base)

        assert config.config == {"app": {"name": "from-os", "port": 1}, "other": {"key": "kept"}}


class TestSections:
    def test_environment_decorator_forms(self) -> None:
        """`environment` works both as `@config_section(name)` and as `config_section(cls, name)`."""

        class Direct(BolinetteModel):
            pass

        assert config_section(Direct, "direct") is Direct

        @config_section("decorated")
        class Decorated(BolinetteModel):
            pass

        assert Decorated.__name__ == "Decorated"

    def test_environment_invalid_arguments_raise(self) -> None:
        """Any other argument shape is a programming error."""
        with pytest.raises(TypeError):
            config_section()  # pyright: ignore[reportCallIssue]

    async def test_section_is_validated_from_config(self, env_folder: Path) -> None:
        """A section model is filled from the matching configuration section."""
        _write(env_folder, "env.toml", '[app]\nname = "svc"\nport = 9000\n')

        section = await _section(AppSection)

        assert section.name == "app"
        assert section.type is AppSection
        assert section.value == AppSection(name="svc", port=9000)

    async def test_missing_section_uses_defaults(self, env_folder: Path) -> None:
        """A section absent from the configuration is built from the model defaults."""
        section = await _section(AppSection)

        assert section.value == AppSection()

    async def test_os_values_are_coerced(self, env_folder: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """String values from OS variables are converted to the field type."""
        monkeypatch.setenv("BLNT_APP__PORT", "8080")

        section = await _section(AppSection)

        assert section.value.port == 8080

    async def test_invalid_value_raises(self, env_folder: Path) -> None:
        """A value that does not fit the model raises a validation error."""
        _write(env_folder, "env.toml", '[app]\nport = "not-a-port"\n')

        with pytest.raises(pydantic.ValidationError):
            await _section(AppSection)

    async def test_undecorated_type_raises(self, env_folder: Path) -> None:
        """Requiring a section for a model without `@config_section` is reported."""
        with pytest.raises(InitError, match="not a configuration section"):
            await _section(NotASection)

    async def test_core_section_defaults(self, env_folder: Path) -> None:
        """The core section is registered by the core extension with safe defaults."""
        config_section(CoreConfigSection, "core")

        section = await _section(CoreConfigSection)

        assert section.value.debug is False
        assert section.value.logging is None

    async def test_core_section_logging_config(self, env_folder: Path) -> None:
        """Logging entries are discriminated on their `type` field."""
        _write(
            env_folder,
            "env.toml",
            "[[core.logging]]\n"
            'type = "stderr"\n'
            'level = "DEBUG"\n'
            "color = true\n"
            "[[core.logging]]\n"
            'type = "file"\n'
            'level = "INFO"\n'
            'path = "logs/app.log"\n',
        )
        config_section(CoreConfigSection, "core")

        section = await _section(CoreConfigSection)

        assert section.value.logging is not None
        assert [c.type for c in section.value.logging] == ["stderr", "file"]
