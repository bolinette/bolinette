from setuptools import setup, find_packages

from bolinette import env
from bolinette.utils import fs


def project_packages(module):
    return [m for m in find_packages() if m.startswith(module)]


setup(
    name='Bolinette',
    packages=project_packages('bolinette'),
    include_package_data=True,
    version=fs.read_version(env.root_path()),
    license='MIT',
    description='Bolinette, a web framework built on top of Flask',
    author='Pierre Chat',
    author_email='pierrechat89@hotmail.fr',
    url='https://github.com/TheCaptainCat/bolinette',
    keywords=['Flask', 'Bolinette', 'Web', 'Framework'],
    install_requires=[
        'aiohttp==3.6.2',
        'aiohttp-cors==0.7.0',
        'bcrypt==3.1.7',
        'pytz==2019.3',
        'PyJWT==1.7.1',
        'pytest==5.4.1',
        'pytest-aiohttp==0.3.0',
        'PyYAML==5.3.1',
        'requests==2.23.0',
        'SQLAlchemy==1.3.15',
        'twine==3.1.1'
    ],
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
