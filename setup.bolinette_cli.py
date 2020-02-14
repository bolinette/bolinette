from setuptools import setup, find_packages

import bolinette_cli


def project_packages(module):
    return [m for m in find_packages() if m.startswith(module)]


setup(
    name='Bolinette-CLI',
    packages=project_packages('bolinette_cli.'),
    include_package_data=True,
    version=bolinette_cli.cli_version,
    license='MIT',
    description='The Bolinette CLI, useful commands for your Bolinette API',
    author='Pierre Chat',
    author_email='pierrechat89@hotmail.fr',
    url='https://github.com/TheCaptainCat/bolinette',
    keywords=['Flask', 'Bolinette', 'Web', 'Framework'],
    install_requires=[
        'inflect==4.0.0',
        'Jinja2==2.10.3',
        'pydash==4.7.6',
        'twine==3.1.1',
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
    ],
    entry_points={
        'console_scripts': [
            'blnt=bolinette.cli:main'
        ]
    },
)
