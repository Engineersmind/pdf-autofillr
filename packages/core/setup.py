from setuptools import setup, find_packages

setup(
    name="pdf-autofiller-core",
    version="1.0.0",
    description="Core shared interfaces and utilities for PDF Autofiller modules",
    long_description=open("README.md").read() if open("README.md").read() else "Core package",
    long_description_content_type="text/markdown",
    author="Engineersmind",
    author_email="team@engineersmind.com",
    url="https://github.com/Engineersmind/pdf-autofillr",
    packages=find_packages(),
    python_requires=">=3.9",
    
    # NO DEPENDENCIES - Only abstract interfaces!
    install_requires=[
        # Absolutely minimal dependencies
    ],
    
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.12.0",
            "flake8>=7.0.0",
            "mypy>=1.8.0",
        ],
    },
    
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    
    keywords="pdf autofiller core interfaces utilities",
    
    project_urls={
        "Documentation": "https://github.com/Engineersmind/pdf-autofillr/tree/main/docs",
        "Source": "https://github.com/Engineersmind/pdf-autofillr",
        "Tracker": "https://github.com/Engineersmind/pdf-autofillr/issues",
    },
)
