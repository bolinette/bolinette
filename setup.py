from bolinette_common import files, paths
from setuptools import setup, find_packages

from bolinette import core


context = core.BolinetteContext(paths.dirname(__file__), None)


def project_packages(module):
    return [m for m in find_packages() if m.startswith(module)]


setup(
    name='Bolinette',
    packages=project_packages('bolinette'),
    include_package_data=True,
    version=files.read_version(context.root_path()),
    license='MIT',
    description='Bolinette, a web framework built on top of Flask',
    long_description=files.read_file(context.root_path('README.md')),
    long_description_content_type='text/markdown',
    author='Pierre Chat',
    author_email='pierrechat@outlook.com',
    url='https://github.com/TheCaptainCat/bolinette',
    keywords=['Flask', 'Bolinette', 'Web', 'Framework'],
    install_requires=files.read_requirements(context.root_path()),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.8',
    ],
    setup_requires=[
        'wheel'
    ]
)
