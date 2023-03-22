#!/usr/bin/env python3
# jimk: remote machines need the above line when building console scripts which will
# be installed on machines which also require python 2 in their path
# read the contents of your README file
from os import path

from setuptools import setup, find_packages

long_description_content_type = 'text/x-rst'
this_directory = path.abspath(path.dirname(__file__))
readme_doc = path.join(this_directory, 'README.md')
try:
    import pypandoc

    long_description = pypandoc.convert_file(readme_doc, 'rst')
except(IOError, ImportError):
    long_description = open(readme_doc).read()
    long_description_content_type = 'text/markdown'
console_scripts = ['manifestforwork = v_m_b.manifestBuilder:manifestShell',
                   'manifestFromS3 = v_m_b.manifestBuilder:manifestFromS3']

setup(version='1.2.9',
      name='bdrc-volume-manifest-builder',
      packages=find_packages(),
      url='https://github.com/buda-base/volume-manifest-builder/', license='', author='jimk',
      author_email='jimk@tbrc.org',
      description='Creates manifests for syncd works.',
      entry_points={'console_scripts': console_scripts},
      install_requires=['boto3', 'requests', 'lxml', 'pillow', 'botocore', 'boto',
                        'aiofiles', 'requests', 'bdrc-util'],
      python_requires='>=3.7',
      classifiers=["Programming Language :: Python :: 3", "License :: OSI Approved :: MIT License",
                   "Operating System :: OS Independent",
                   "Development Status :: 5 - Production/Stable"],
      long_description=long_description,
      long_description_content_type=long_description_content_type)
