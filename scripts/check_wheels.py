import sys
import zipfile
from pathlib import Path

NAMESPACE = "bolinette"
CORE_MODULE = "core"


def module_of(dist_name: str) -> str | None:
    if dist_name == NAMESPACE:
        return CORE_MODULE
    prefix = f"{NAMESPACE}_"
    if dist_name.startswith(prefix):
        return dist_name.removeprefix(prefix)
    return None


def check_wheel(wheel: Path) -> list[str]:
    dist_name = wheel.name.split("-")[0]
    module = module_of(dist_name)
    if module is None:
        return [f"{wheel.name}: distribution name is neither '{NAMESPACE}' nor '{NAMESPACE}_<module>'"]
    expected_root = f"{NAMESPACE}/{module}/"

    errors: list[str] = []
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
    if f"{NAMESPACE}/__init__.py" in names:
        errors.append(f"{wheel.name}: ships '{NAMESPACE}/__init__.py', which breaks the namespace package")
    if not any(name.startswith(expected_root) for name in names):
        errors.append(f"{wheel.name}: does not contain '{expected_root}'")
    for name in names:
        if name == f"{NAMESPACE}/":
            continue
        if name.startswith(f"{NAMESPACE}/") and not name.startswith(expected_root):
            errors.append(f"{wheel.name}: contains '{name}', which belongs to another package")
    return errors


def main(dist_dir: str) -> int:
    wheels = sorted(Path(dist_dir).glob("*.whl"))
    if not wheels:
        print(f"No wheels found in {dist_dir}", file=sys.stderr)
        return 1
    errors = [error for wheel in wheels for error in check_wheel(wheel)]
    for error in errors:
        print(error, file=sys.stderr)
    if not errors:
        print(f"{len(wheels)} wheels checked: {', '.join(w.name for w in wheels)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "dist"))
