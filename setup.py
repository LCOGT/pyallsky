#!/usr/bin/env python

from setuptools import setup

setup(
    name = 'pyallsky',
    version = '2.0.2',
    description = 'Python Control of SBIG AllSky 340/340C Camera',
    url = 'https://github.com/LCOGT/pyallsky',
    author = 'Las Cumbres Observatory Software Team',
    author_email = 'softies@lco.global',
    license = 'LGPL',
    packages = ['pyallsky'],
    python_requires = '>=3.10',
    install_requires = [
        'colour-demosaicing~=0.2.5',
        'matplotlib~=3.9.0',
        'daemonize~=2.5.0',
        'fitsio~=1.2.4',
        'numpy<2',
        'pillow>=8.3.2',
        'pyephem~=3.7.7.0',
        'pyserial~=3.5',
    ],
    scripts = [
        'bin/allsky_capture_image',
        'bin/allsky_check_communications',
        'bin/allsky_get_version',
        'bin/allsky_heater_control',
        'bin/allsky_set_baudrate',
        'bin/allsky_scheduler',
        'bin/allsky_shutter_control',
    ],
    zip_safe = False
)
