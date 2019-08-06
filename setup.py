from distutils.core import setup

setup(
    name='Bolinette',
    packages=[
        'bolinette',
        'bolinette.controllers',
        'bolinette.models',
        'bolinette.services'
    ],
    version='0.0.4',
    license='MIT',
    description='Bolinette, a web framework built on top of Flask',
    author='Pierre Chat',
    author_email='pierrechat89@hotmail.fr',
    url='https://github.com/TheCaptainCat/bolinette',
    keywords=['Flask', 'Bolinette', 'Web', 'Framework'],
    install_requires=[
        'Flask==1.1.1',
        'Flask-Bcrypt==0.7.1',
        'Flask-JWT-Extended==3.21.0',
        'Flask-Script==2.0.6',
        'Flask-SQLAlchemy==2.4.0',
        'PyJWT==1.7.1'
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.7',
    ],
)
