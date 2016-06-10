# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from setuptools import setup, find_packages

setup(
    name='pyjomap',
    version='0.1dev',
    packages=find_packages(),
    license='Apache License 2.0',
    long_description="Pythonic JSON & other object mapper",
    install_requires=[
        "genty==1.3.2"
    ],
    entry_points={
        "console_scripts": {
            "unit": "unittest.__main__:main"
        }
    }
)
