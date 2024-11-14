from setuptools import setup, find_packages

setup(
    name="grid_creator",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "geopandas",
        "pandas",
        "pygmt",
        "rasterio",
        "xarray"
    ],
    entry_points={
        'console_scripts': [
            'grid_creator=grid_creator.__init__:main',
        ],
    },
)