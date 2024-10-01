import hashlib
import json
import sys
from pathlib import Path
from typing import Annotated, Any, Literal

from bolinette.core.command import Argument
from bolinette.core.exceptions import BolinetteError


async def new_rsa_key(
    size: Annotated[Literal[512, 1024, 2048, 4096], Argument("option", "s")] = 2048,
    outdir: Annotated[str, Argument("option", "o")] = "env/keys",
    keyname: Annotated[str, Argument("option", "n")] = "sign",
    passphrase: Annotated[bytes | None, Argument("option", "p")] = None,
    jwk: Annotated[bool, Argument("option")] = False,
) -> None:
    try:
        import cryptography.hazmat.primitives.asymmetric.rsa as crypto_rsa
        import cryptography.hazmat.primitives.serialization as crypto_serial
        import jwt.algorithms
    except ImportError as err:
        raise BolinetteError("Library pyjwt is not available, make sure to install it") from err

    output_path = Path(outdir)
    if not output_path.exists():
        output_path.mkdir(parents=True)
    if not output_path.is_dir():
        raise BolinetteError(f"Output path {output_path} is not a directory")

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


async def new_encryption_key(
    algo: Annotated[
        Literal[
            "AESGCM",
            "ChaCha20Poly1305",
            "AESCCM",
            "AESSIV",
            "AESOCB3",
            "AESGCMSIV",
        ],
        Argument("option", "a"),
    ],
    size: Annotated[int | None, Argument("option", "s")] = None,
    outdir: Annotated[str, Argument("option", "o")] = "env/keys",
    keyname: Annotated[str, Argument("option", "n")] = "encrypt",
) -> int:
    try:
        import cryptography.hazmat.primitives.ciphers.aead as aead
    except ImportError as err:
        raise BolinetteError("Library pyjwt is not available, make sure to install it") from err
    match algo:
        case "AESGCM":
            if size is None:
                size = 128
            if size not in (128, 192, 256):
                print("size must be either 128, 192 or 256", file=sys.stderr)
                return 1
            key = aead.AESGCM.generate_key(size)
        case "ChaCha20Poly1305":
            if size is not None:
                print("size must not be specified for this algorithm", file=sys.stderr)
                return 1
            key = aead.ChaCha20Poly1305.generate_key()
        case "AESCCM":
            if size is None:
                size = 128
            if size not in (128, 192, 256):
                print("size must be either 128, 192 or 256", file=sys.stderr)
                return 1
            key = aead.AESCCM.generate_key(size)
        case "AESSIV":
            if size is None:
                size = 256
            if size not in (256, 384, 512):
                print("size must be either 256, 384 or 512", file=sys.stderr)
                return 1
            key = aead.AESCCM.generate_key(size)
        case "AESOCB3":
            if size is None:
                size = 128
            if size not in (128, 192, 256):
                print("size must be either 128, 192 or 256", file=sys.stderr)
                return 1
            key = aead.AESOCB3.generate_key(size)
        case "AESGCMSIV":
            if size is None:
                size = 128
            if size not in (128, 192, 256):
                print("size must be either 128, 192 or 256", file=sys.stderr)
                return 1
            key = aead.AESGCMSIV.generate_key(size)
    with open(Path(outdir) / f"{keyname}.aes", "wb") as f:
        f.write(key)
    return 0
