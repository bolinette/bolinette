from pathlib import Path

from setuptools import setup

from bolinette.core import __version__
from bolinette.core.utils.packaging import project_packages, read_file, read_requirements

cwd = Path.cwd()

setup(
    name="bolinette",
    packages=project_packages("bolinette.core"),
    include_package_data=True,
    version=__version__,
    license="MIT",
    description="The Bolinette core package, an inversion of control framework",
    long_description=read_file(cwd / "README.md"),
    long_description_content_type="text/markdown",
    author="Pierre Chat",
    author_email="pierrechat@outlook.com",
    url="https://github.com/bolinette/bolinette",
    keywords=["Bolinette", "Framework", "IoC", "Dependency Injection"],
    install_requires=read_requirements(cwd / "requirements.core.txt"),
    package_data={"bolinette.core": ["py.typed"]},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.11",
    ],
    setup_requires=["wheel"],
    entry_points={
        "console_scripts": ["blnt=bolinette.core.__main__:main"],
    },
)
