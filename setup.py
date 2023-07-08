from setuptools import find_packages, setup

setup(
    name="hackbc9419ab11eebe56",
    version="0.0.11",
    packages=find_packages(),
    install_requires=[
        "lxml",
        "exorde_data",
        "aiohttp",
        "beautifulsoup4>=4.11",
        "python_dateutil>=2.8"
    ],
    extras_require={"dev": ["pytest", "pytest-cov", "pytest-asyncio"]},
)
