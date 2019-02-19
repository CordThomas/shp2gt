from setuptools import setup

def readme():
      with open('README.rst') as f:
            return f.read()

setup(name='shp2gt',
      version='0.1.1',
      description='Shapefile to GT Converter',
      long_description=readme(),
      classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.5',
        'Topic :: Scientific/Engineering :: GIS',
      ],
      keywords='graph-tool shapefile esri linestring network analysis',
      url='https://github.com/CordThomas/shp2gt',
      author='Cord Thomas',
      author_email='cord.thomas@gmail.com',
      license='MIT',
      packages=['shp2gt'],
      zip_safe=False)
