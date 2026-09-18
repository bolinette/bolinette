import json
import sys
from pathlib import Path

import pytest

from bolinette.core import Bolinette
from bolinette.core.commands.exceptions import CommandHelpError, CommandUsageError
from bolinette.core.exceptions import BolinetteError, InitError
from bolinette.web._commands._auth import new_encryption_key, new_rsa_key
from tests.web.conftest import AppFactory

SIZES = {"AESGCM": 16, "ChaCha20Poly1305": 32, "AESCCM": 16, "AESSIV": 32, "AESOCB3": 16, "AESGCMSIV": 16}


async def _run(blnt: Bolinette, *args: str) -> int | None:
    return await blnt.run_command(list(args))


class TestNewRsaKey:
    async def test_default_output(self, make_app: AppFactory, tmp_cwd: Path) -> None:
        blnt = await make_app()

        assert await _run(blnt, "auth", "new", "rsa", "-s", "2048") is None

        assert (tmp_cwd / "env" / "keys" / "sign.pem").exists()
        assert (tmp_cwd / "env" / "keys" / "sign.pem.pub").exists()

    async def test_custom_directory_and_name(self, make_app: AppFactory, tmp_cwd: Path) -> None:
        blnt = await make_app()

        await _run(blnt, "auth", "new", "rsa", "-s", "2048", "-o", "keys", "-n", "mine")

        assert sorted(p.name for p in (tmp_cwd / "keys").iterdir()) == ["mine.pem", "mine.pem.pub"]

    async def test_jwk_files(self, make_app: AppFactory, tmp_cwd: Path) -> None:
        blnt = await make_app()

        await _run(blnt, "auth", "new", "rsa", "-s", "2048", "-o", "keys", "--jwk")

        private = json.loads((tmp_cwd / "keys" / "sign.private.jwk.json").read_text())
        public = json.loads((tmp_cwd / "keys" / "sign.public.jwk.json").read_text())
        assert private["kty"] == "RSA"
        assert private["kid"] == public["kid"]

    async def test_passphrase_encrypts_the_private_key(self, make_app: AppFactory, tmp_cwd: Path) -> None:
        blnt = await make_app()

        await _run(blnt, "auth", "new", "rsa", "-s", "2048", "-o", "keys", "-p", "secret")

        assert b"ENCRYPTED PRIVATE KEY" in (tmp_cwd / "keys" / "sign.pem").read_bytes()

    async def test_an_existing_file_as_outdir_is_rejected(self, make_app: AppFactory, tmp_cwd: Path) -> None:
        (tmp_cwd / "keys").write_text("not a directory")
        blnt = await make_app()

        with pytest.raises(BolinetteError, match="is not a directory"):
            await _run(blnt, "auth", "new", "rsa", "-s", "2048", "-o", "keys")

    async def test_the_smallest_offered_size_works(self, make_app: AppFactory, tmp_cwd: Path) -> None:
        blnt = await make_app()

        await _run(blnt, "auth", "new", "rsa", "-s", "2048", "-o", "keys")

        assert (tmp_cwd / "keys" / "sign.pem").exists()

    async def test_an_invalid_size_is_a_usage_error(self, make_app: AppFactory) -> None:
        blnt = await make_app()

        with pytest.raises(CommandUsageError):
            await _run(blnt, "auth", "new", "rsa", "-s", "123")


class TestNewEncryptionKey:
    @pytest.mark.parametrize("algo", list(SIZES))
    async def test_every_algorithm_with_its_default_size(self, make_app: AppFactory, tmp_cwd: Path, algo: str) -> None:
        blnt = await make_app()

        await _run(blnt, "auth", "new", "encrypt", "-a", algo, "-o", "keys")

        assert (tmp_cwd / "keys" / "encrypt.aes").stat().st_size == SIZES[algo]

    @pytest.mark.parametrize(
        ("algo", "size", "expected"),
        [
            ("AESGCM", "256", 32),
            ("AESCCM", "192", 24),
            ("AESOCB3", "256", 32),
            ("AESGCMSIV", "256", 32),
            ("AESSIV", "512", 64),
        ],
    )
    async def test_explicit_sizes(
        self, make_app: AppFactory, tmp_cwd: Path, algo: str, size: str, expected: int
    ) -> None:
        blnt = await make_app()

        await _run(blnt, "auth", "new", "encrypt", "-a", algo, "-s", size, "-o", "keys")

        assert (tmp_cwd / "keys" / "encrypt.aes").stat().st_size == expected

    @pytest.mark.parametrize(
        ("algo", "size"),
        [("AESGCM", "100"), ("AESCCM", "512"), ("AESOCB3", "8"), ("AESGCMSIV", "384"), ("AESSIV", "128")],
    )
    async def test_invalid_sizes_are_rejected(self, make_app: AppFactory, algo: str, size: str) -> None:
        blnt = await make_app()

        with pytest.raises(BolinetteError, match="Key size for"):
            await _run(blnt, "auth", "new", "encrypt", "-a", algo, "-s", size, "-o", "keys")

    async def test_chacha_rejects_a_size(self, make_app: AppFactory) -> None:
        blnt = await make_app()

        with pytest.raises(BolinetteError, match="must not be specified"):
            await _run(blnt, "auth", "new", "encrypt", "-a", "ChaCha20Poly1305", "-s", "128", "-o", "keys")

    async def test_custom_name(self, make_app: AppFactory, tmp_cwd: Path) -> None:
        blnt = await make_app()

        await _run(blnt, "auth", "new", "encrypt", "-a", "AESGCM", "-o", "keys", "-n", "mine")

        assert (tmp_cwd / "keys" / "mine.aes").exists()

    async def test_an_unknown_algorithm_is_a_usage_error(self, make_app: AppFactory) -> None:
        blnt = await make_app()

        with pytest.raises(CommandUsageError):
            await _run(blnt, "auth", "new", "encrypt", "-a", "Nope")

    async def test_a_missing_algorithm_is_a_usage_error(self, make_app: AppFactory) -> None:
        blnt = await make_app()

        with pytest.raises(CommandUsageError):
            await _run(blnt, "auth", "new", "encrypt")

    async def test_help(self, make_app: AppFactory) -> None:
        blnt = await make_app()

        with pytest.raises(CommandHelpError) as raised:
            await _run(blnt, "auth", "new", "encrypt", "--help")

        assert raised.value.code == 0
        assert "--algo" in raised.value.message


class TestMissingLibrary:
    async def test_rsa_without_pyjwt(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setitem(sys.modules, "jwt.algorithms", None)

        with pytest.raises(InitError, match=r"bolinette-web\[auth\]"):
            await new_rsa_key(size=2048)

    async def test_encrypt_without_cryptography(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setitem(sys.modules, "cryptography.hazmat.primitives.ciphers", None)

        with pytest.raises(InitError, match=r"bolinette-web\[auth\]"):
            await new_encryption_key(algo="AESGCM")
