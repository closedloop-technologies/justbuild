from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="LFG: Chat Assisted Programming Tools",
    version="0.1.0",
    author="Sean Kruzel @ Closedloop Technologies",
    author_email="sean@closedloop.lech",
    description="A tool to help developers resolve code conflicts using AI.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/closedloop-technologies/letsgo-sh",
    packages=find_packages(),
    install_requires=[
        "typer",
        "openai",
        "python-dotenv",
    ],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "lfg=lfg.main:app",
        ],
    },
)
