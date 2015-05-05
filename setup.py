from setuptools import setup, find_packages


setup(name='tilegen',
      author='Victor Ng',
      description='Generate obfuscated offline geolocation tiles',
      url="http://github.com/crankycoder/offline_geo",
      version='0.5',
      license='MPL 2.0',
      packages=find_packages(exclude=['tests']))
