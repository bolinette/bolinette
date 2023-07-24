from setuptools import find_namespace_packages, setup

from bolinette.core.utils import FileUtils, PathUtils
from bolinette.data import __version__

paths = PathUtils()
files = FileUtils(paths)


def project_packages(module: str) -> list[str]:
    return [m for m in find_namespace_packages() if m.startswith(module)]


setup(
    name="bolinette-data",
    packages=project_packages("bolinette.data"),
    include_package_data=True,
    version=__version__,
    license="MIT",
    description="The Bolinette data package, an async data management framework, based on bolinette and SQLAlchemy",
    long_description=files.read_file(paths.root_path("README.md")),
    long_description_content_type="text/markdown",
    author="Pierre Chat",
    author_email="pierrechat@outlook.com",
    url="https://github.com/bolinette/bolinette",
    keywords=["Bolinette", "Framework", "ORM", "Data Management"],
    install_requires=files.read_requirements(paths.root_path(), name="requirements.data.txt"),
    package_data={"bolinette.data": ["py.typed"]},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.11",
    ],
    setup_requires=["wheel"],
)
