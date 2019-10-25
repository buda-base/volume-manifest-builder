#!/usr/bin/env python3
# jimk: remote machines need the above line when building console scripts which will
# be installed on machines which also require python 2 in their path
# read the contents of your README file
from os import path

from setuptools import setup, find_packages

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

console_scripts = ['manifestforwork = v_m_t.manifestforwork:manifestShell',
                   'manifestFromS3 = v_m_t.manifestforwork:manifestFromS3']
setup(name='volume-manifest-tool', version='1.0a3', packages=find_packages(),
      url='https://github.com/buda-base/volume-manifest-tool/', license='', author='jimk', author_email='jimk@tbrc.org',
      description='Creates manifests for syncd works.', entry_points={'console_scripts': console_scripts},
      install_requires=['boto3', 'requests', 'lxml', 'pillow', 's3transfer', 'botocore', 'boto'],
      long_description=long_description, long_description_content_type='text/markdown')
