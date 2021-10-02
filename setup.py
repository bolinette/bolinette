from bolinette.utils import files, paths
from setuptools import setup, find_packages

from bolinette import blnt


context = blnt.BolinetteContext(paths.join(paths.dirname(__file__), 'bolinette'))


def project_packages(module):
    return [m for m in find_packages() if m.startswith(module)]


setup(
    name='Bolinette',
    packages=project_packages('bolinette'),
    include_package_data=True,
    version=context.manifest['version'],
    license='MIT',
    description='An asynchronous Python web framework',
    long_description=files.read_file(context.root_path('README.md')),
    long_description_content_type='text/markdown',
    author='Pierre Chat',
    author_email='pierrechat@outlook.com',
    url='https://github.com/TheCaptainCat/bolinette',
    keywords=['Bolinette', 'Web', 'Framework', 'Async'],
    install_requires=files.read_requirements(context.root_path()),
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.9',
    ],
    setup_requires=[
        'wheel'
    ],
    entry_points = {
        'console_scripts': ['blnt=bolinette.__main__:main'],
    }
)
