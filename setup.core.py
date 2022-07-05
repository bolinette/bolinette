from setuptools import setup, find_packages

from bolinette.core import Context
from bolinette.core.utils import files, paths


context = Context(paths.join(paths.dirname(__file__), 'bolinette', 'core'))


def project_packages(module):
    return [m for m in find_packages() if m.startswith(module)]


setup(
    name='bolinette',
    packages=project_packages('bolinette'),
    include_package_data=True,
    version=context.manifest['version'],
    license='MIT',
    description='The Bolinette core package, an inversion of control framework',
    long_description=files.read_file(context.root_path('README.md')),
    long_description_content_type='text/markdown',
    author='Pierre Chat',
    author_email='pierrechat@outlook.com',
    url='https://github.com/TheCaptainCat/bolinette',
    keywords=['Bolinette', 'Framework', 'IoC', 'Dependency Injection'],
    install_requires=files.read_requirements(context.root_path()),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.10',
    ],
    setup_requires=[
        'wheel'
    ],
    entry_points = {
        'console_scripts': ['blnt=bolinette.__main__:main'],
    }
)
