from setuptools import setup, find_namespace_packages

from bolinette.ext.web import __version__
from bolinette.utils import PathUtils, FileUtils


paths = PathUtils()
files = FileUtils(paths)


def project_packages(module) -> list[str]:
    return [m for m in find_namespace_packages() if m.startswith(module)]


setup(
    name="bolinette-web",
    packages=project_packages("bolinette.web"),
    include_package_data=True,
    version=__version__,
    license="MIT",
    description="The Bolinette web package, an async REST API and Websocket framework, based on bolinette, bolinette-data and aiohttp",
    long_description=files.read_file(paths.root_path("README.md")),
    long_description_content_type="text/markdown",
    author="Pierre Chat",
    author_email="pierrechat@outlook.com",
    url="https://github.com/bolinette/bolinette",
    keywords=["Bolinette", "Framework", "REST API", "Websocket"],
    install_requires=files.read_requirements(
        paths.root_path(), name="requirements.web.txt"
    ),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.11",
    ],
    setup_requires=["wheel"],
)
