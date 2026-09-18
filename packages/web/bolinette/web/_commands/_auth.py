import hashlib
import json
from pathlib import Path
from typing import Annotated, Any, Literal

from bolinette.core.commands import CommandOption
from bolinette.core.exceptions import BolinetteError, InitError

_MISSING_LIBRARY = "Library pyjwt is not available, install bolinette-web[auth]"

type EncryptionAlgorithm = Literal["AESGCM", "ChaCha20Poly1305", "AESCCM", "AESSIV", "AESOCB3", "AESGCMSIV"]

_ALLOWED_SIZES: dict[str, tuple[int, ...]] = {
    "AESGCM": (128, 192, 256),
    "AESCCM": (128, 192, 256),
    "AESOCB3": (128, 192, 256),
    "AESGCMSIV": (128, 192, 256),
    "AESSIV": (256, 384, 512),
}


def _prepare_outdir(outdir: str) -> Path:
    output_path = Path(outdir)
    if not output_path.exists():
        output_path.mkdir(parents=True)
    if not output_path.is_dir():
        raise BolinetteError(f"Output path {output_path} is not a directory")
    return output_path


def _generate_rsa_key(size: int, outdir: str, keyname: str, passphrase: bytes | None, jwk: bool) -> None:
    try:
        import jwt.algorithms
        from cryptography.hazmat.primitives import serialization as crypto_serial
        from cryptography.hazmat.primitives.asymmetric import rsa as crypto_rsa
    except ImportError as err:
        raise InitError(_MISSING_LIBRARY) from err

    output_path = _prepare_outdir(outdir)

    private_key = crypto_rsa.generate_private_key(public_exponent=65537, key_size=size)
    private_bytes = private_key.private_bytes(
        crypto_serial.Encoding.PEM,
        crypto_serial.PrivateFormat.PKCS8,
        crypto_serial.BestAvailableEncryption(passphrase) if passphrase else crypto_serial.NoEncryption(),
    )
    keyhash = hashlib.blake2s(private_bytes).hexdigest()
    with open(output_path / f"{keyname}.pem", "wb") as priv_key_f:
        priv_key_f.write(private_bytes)

    public_key = private_key.public_key()
    public_bytes = public_key.public_bytes(
        crypto_serial.Encoding.PEM,
        crypto_serial.PublicFormat.SubjectPublicKeyInfo,
    )
    with open(output_path / f"{keyname}.pem.pub", "wb") as pub_key_f:
        pub_key_f.write(public_bytes)

    if jwk:
        private_jwk: dict[str, Any] = jwt.algorithms.RSAAlgorithm.to_jwk(private_key, as_dict=True)
        private_jwk = {"kid": keyhash, **private_jwk}
        with open(output_path / f"{keyname}.private.jwk.json", "w") as jwk_priv_f:
            jwk_priv_f.write(json.dumps(private_jwk, indent=2, separators=(",", ": ")))
        public_jwk: dict[str, Any] = jwt.algorithms.RSAAlgorithm.to_jwk(public_key, as_dict=True)
        public_jwk = {"kid": keyhash, **public_jwk}
        with open(output_path / f"{keyname}.public.jwk.json", "w") as jwk_pub_f:
            jwk_pub_f.write(json.dumps(public_jwk, indent=2, separators=(",", ": ")))


def _checked_size(algo: str, size: int | None, default: int) -> int:
    allowed = _ALLOWED_SIZES[algo]
    if size is None:
        return default
    if size not in allowed:
        raise BolinetteError(f"Key size for {algo} must be one of {', '.join(str(s) for s in allowed)}")
    return size


def _generate_encryption_key(algo: EncryptionAlgorithm, size: int | None, outdir: str, keyname: str) -> None:
    try:
        from cryptography.hazmat.primitives.ciphers import aead
    except ImportError as err:
        raise InitError(_MISSING_LIBRARY) from err

    key: bytes
    match algo:
        case "AESGCM":
            key = aead.AESGCM.generate_key(_checked_size(algo, size, 128))
        case "ChaCha20Poly1305":
            if size is not None:
                raise BolinetteError("Key size must not be specified for ChaCha20Poly1305")
            key = aead.ChaCha20Poly1305.generate_key()
        case "AESCCM":
            key = aead.AESCCM.generate_key(_checked_size(algo, size, 128))
        case "AESSIV":
            key = aead.AESSIV.generate_key(_checked_size(algo, size, 256))
        case "AESOCB3":
            key = aead.AESOCB3.generate_key(_checked_size(algo, size, 128))
        case "AESGCMSIV":
            key = aead.AESGCMSIV.generate_key(_checked_size(algo, size, 128))

    output_path = _prepare_outdir(outdir)
    with open(output_path / f"{keyname}.aes", "wb") as f:
        f.write(key)


async def new_rsa_key(
    size: Annotated[Literal[2048, 3072, 4096], CommandOption("s")] = 2048,
    outdir: Annotated[str, CommandOption("o")] = "env/keys",
    keyname: Annotated[str, CommandOption("n")] = "sign",
    passphrase: Annotated[bytes | None, CommandOption("p")] = None,
    jwk: Annotated[bool, CommandOption()] = False,
) -> None:
    _generate_rsa_key(size, outdir, keyname, passphrase, jwk)


async def new_encryption_key(
    algo: Annotated[EncryptionAlgorithm, CommandOption("a")],
    size: Annotated[int | None, CommandOption("s")] = None,
    outdir: Annotated[str, CommandOption("o")] = "env/keys",
    keyname: Annotated[str, CommandOption("n")] = "encrypt",
) -> None:
    _generate_encryption_key(algo, size, outdir, keyname)
