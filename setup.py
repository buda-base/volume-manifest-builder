#!/usr/bin/env python3
# jimk: remote machines need the above line when building console scripts which will
# be installed on machines which also require python 2 in their path
from setuptools import setup, find_packages

console_scripts = ['manifestforwork = v_m_t.manifestforwork:manifestShell',
                   'manifestFromS3 = v_m_t.manifestforwork:manifestFromS3']
setup(name='volume-manifest-tool', version='1.0.1b2', packages=find_packages(),
      url='https://github.com/buda-base/volume-manifest-tool/', license='', author='jimk', author_email='jimk@tbrc.org',
      description='Creates manifests for syncd works.', entry_points={'console_scripts': console_scripts},
      install_requires=['boto3', 'requests', 'lxml', 'pillow', 's3transfer', 'botocore'], python_requires='>=3.6',
      classifiers=["Programming Language :: Python :: 3", "License :: OSI Approved :: MIT License",
                   "Operating System :: MacOS :: MacOS X", "Operating System :: OS Independent",
                   "Development Status :: 5 - Released"])
