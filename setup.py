import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="consmodel",
    version="0.1.9",
    author="Blaž Dobravec",
    author_email="blaz@dobravec.si",
    description=
    "The library aims to provide a simple way to create individual consumer loads, generation.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/blazdob/consmodel",
    project_urls={
        "Bug Tracker": "https://github.com/blazdob/consmodel/issue",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    packages=setuptools.find_packages(),
    install_requires=[
        'setuptools>=42', 'retry_requests>=2.0.0', 'openmeteo_requests>=1.1.0',
        'requests_cache>=1.1.0', 'pvlib>=0.9.1', 'pandas>=1.5.2',
        'numpy>=1.22.4', 'tzfpy>=0.15.1', 'meteostat>=1.6.5', 'scipy>=1.10.0',
        'hplib==1.9'
    ],
    python_requires=">=3.6")
