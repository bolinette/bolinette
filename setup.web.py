from pathlib import Path

from setuptools import setup

from bolinette.core import __version__
from bolinette.core.utils.packaging import project_packages, read_file, read_requirements

cwd = Path.cwd()

setup(
    name="bolinette-web",
    packages=project_packages("bolinette.web"),
    include_package_data=True,
    version=__version__,
    license="MIT",
    description="The Bolinette web package, an async Http and Websocket framework, based on bolinette and aiohttp",
    long_description=read_file(cwd / "README.md"),
    long_description_content_type="text/markdown",
    author="Pierre Chat",
    author_email="pierrechat@outlook.com",
    url="https://github.com/bolinette/bolinette",
    keywords=["Bolinette", "Framework", "Http", "Websocket"],
    install_requires=read_requirements(cwd / "requirements.web.txt"),
    package_data={"bolinette.web": ["py.typed"]},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.11",
    ],
    setup_requires=["wheel"],
)
