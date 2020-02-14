from setuptools import setup, find_packages


def project_packages(module):
    return [m for m in find_packages() if m.startswith(module)]


setup(
    name='Bolinette',
    packages=project_packages('bolinette'),
    include_package_data=True,
    version='0.1.7',
    license='MIT',
    description='Bolinette, a web framework built on top of Flask',
    author='Pierre Chat',
    author_email='pierrechat89@hotmail.fr',
    url='https://github.com/TheCaptainCat/bolinette',
    keywords=['Flask', 'Bolinette', 'Web', 'Framework'],
    install_requires=[
        'Bolinette-CLI==0.1.5',
        'dicttoxml==1.7.4',
        'Flask==1.1.1',
        'Flask-Bcrypt==0.7.1',
        'Flask-Cors==3.0.8',
        'Flask-JWT-Extended==3.24.1',
        'Flask-SQLAlchemy==2.4.1',
        'htmlmin==0.1.12',
        'PyJWT==1.7.1',
        'pytest==5.3.2',
        'SQLAlchemy==1.3.12',
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
