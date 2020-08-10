#!/usr/bin/env python3
# jimk: remote machines need the above line when building console scripts which will
# be installed on machines which also require python 2 in their path
from setuptools import setup, find_packages

console_scripts = ['manifestforwork = v_m_b.manifestforwork:manifestShell',
                   'manifestFromS3 = v_m_b.manifestforwork:manifestFromS3']
setup(name='volume-manifest-builder', version='1.0.3', packages=find_packages(),
      url='https://github.com/buda-base/volume-manifest-builder/', license='', author='jimk',
      author_email='jimk@tbrc.org',
      description='Creates manifests for syncd works.', entry_points={'console_scripts': console_scripts},
      install_requires=['boto3', 'requests', 'lxml', 'pillow', 's3transfer', 'botocore'], python_requires='>=3.6',
      classifiers=["Programming Language :: Python :: 3", "License :: OSI Approved :: MIT License",
                   "Operating System :: MacOS :: MacOS X", "Operating System :: OS Independent",
                   "Development Status :: 5 - Production/Stable"])
