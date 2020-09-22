#!/usr/bin/env python3
# jimk: remote machines need the above line when building console scripts which will
# be installed on machines which also require python 2 in their path
from setuptools import setup, find_packages

console_scripts = ['manifestforwork = v_m_b.manifestBuilder:manifestShell',
                   'manifestFromS3 = v_m_b.manifestBuilder:manifestFromS3']
setup(version='1.0.4.dev5',
      name='bdrc-volume-manifest-builder',
      packages=find_packages(),
      url='https://github.com/buda-base/volume-manifest-builder/', license='', author='jimk',
      author_email='jimk@tbrc.org',
      description='Creates manifests for syncd works.',
      entry_points={'console_scripts': console_scripts},
      install_requires=['boto3', 'requests', 'lxml', 'pillow', 'botocore',
                        'aiofiles', 'requests'],
      python_requires='>=3.7',
      classifiers=["Programming Language :: Python :: 3", "License :: OSI Approved :: MIT License",
                   "Operating System :: OS Independent",
                   "Development Status :: 5 - Production/Stable"])
