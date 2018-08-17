import setuptools

with open("README.md", "r") as f:
    long_description = f.read()

setuptools.setup(
    name="servblr",
    version="0.0.2",
    license="MIT",
    author="y1n0",
    author_email="y1n0@pm.me",
    install_requires=["pycurl"],
    description="A Tumblr instant messages wrapper in Python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/y1n0/servblr",
    packages=setuptools.find_packages(),
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
)