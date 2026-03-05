"""
PDF AutoFiller Plugins Package Setup
"""

from setuptools import setup, find_packages

setup(
    name="pdf-autofiller-plugins",
    version="0.1.0",
    description="Plugin framework for PDF AutoFiller",
    long_description=open("README.md").read() if os.path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    author="PDF AutoFiller Team",
    author_email="team@pdf-autofiller.com",
    url="https://github.com/Engineersmind/pdf-autofillr",
    packages=find_packages(exclude=["tests", "examples"]),
    python_requires=">=3.9",
    install_requires=[
        # No dependencies - pure Python!
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "mypy>=1.0.0",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
    keywords="pdf plugin framework extensible",
    project_urls={
        "Documentation": "https://github.com/Engineersmind/pdf-autofillr/tree/main/docs",
        "Source": "https://github.com/Engineersmind/pdf-autofillr",
        "Tracker": "https://github.com/Engineersmind/pdf-autofillr/issues",
    },
)

import os
