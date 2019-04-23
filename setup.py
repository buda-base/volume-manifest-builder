from setuptools import setup

setup(name='volume-manifest-tool', version='1.0', packages=[''],
    url='https://github.com/buda-base/volume-manifest-tool/', license='', author='jimk/eroux', author_email='',
    description='Creates manifests for syncd works.',
      entry_points={'console_scripts': ['manifestforwork = manifestforwork:manifestShell']}
      )
