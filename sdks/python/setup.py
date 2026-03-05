from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="pdf-autofiller-sdk",
    version="1.0.0",
    description="Python SDK for PDF Autofiller API (Mapper Module)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Engineersmind",
    author_email="team@engineersmind.com",
    url="https://github.com/Engineersmind/pdf-autofillr",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "httpx>=0.26.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "black>=23.12.0",
            "mypy>=1.8.0",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="pdf autofiller mapper sdk api",
    project_urls={
        "Documentation": "https://github.com/Engineersmind/pdf-autofillr/tree/main/docs",
        "Source": "https://github.com/Engineersmind/pdf-autofillr",
        "Tracker": "https://github.com/Engineersmind/pdf-autofillr/issues",
    },
)
