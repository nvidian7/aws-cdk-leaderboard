import setuptools


with open("README.md") as fp:
    long_description = fp.read()


setuptools.setup(
    name="hx_leaderboard",
    version="1.0.0",

    description="Simple Leaderboard Service",
    long_description=long_description,
    long_description_content_type="text/markdown",

    author="styx",

    install_requires=[
        "aws-cdk.core==1.54.0",
    ],

    python_requires=">=3.7",

    classifiers=[
        "Development Status :: 4 - Beta",

        "Intended Audience :: Developers",

        "License :: OSI Approved :: Apache Software License",

        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",

        "Topic :: Software Development :: Code Generators",
        "Topic :: Utilities",

        "Typing :: Typed",
    ],
)
