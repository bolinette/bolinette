from distutils.core import setup

setup(
    name='Flasque',
    packages=['flasque'],
    version='0.0.1',
    license='MIT',
    description='TYPE YOUR DESCRIPTION HERE',
    author='Pierre Chat',
    author_email='pierrechat89@hotmail.fr',
    url='https://github.com/user/reponame',
    download_url='https://github.com/user/reponame/archive/v_01.tar.gz',
    keywords=['Flask', 'Flasque', 'Web', 'Framework'],
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
