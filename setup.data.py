from pathlib import Path

from setuptools import setup

from bolinette.core import __version__
from bolinette.core.utils.packaging import project_packages, read_file, read_requirements

cwd = Path.cwd()

setup(
    name="bolinette-data",
    packages=project_packages("bolinette.data"),
    include_package_data=True,
    version=__version__,
    license="MIT",
    description="The Bolinette data package, an async data management framework, based on bolinette and SQLAlchemy",
    long_description=read_file(cwd / "README.md"),
    long_description_content_type="text/markdown",
    author="Pierre Chat",
    author_email="pierrechat@outlook.com",
    url="https://github.com/bolinette/bolinette",
    keywords=["Bolinette", "Framework", "ORM", "Data Management"],
    install_requires=read_requirements(cwd / "requirements.data.txt"),
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
