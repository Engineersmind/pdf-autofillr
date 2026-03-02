from setuptools import setup, find_packages

setup(
    name="pdf-mapper",
    version="1.0.0",
    description="Platform-agnostic PDF field extraction, mapping, embedding, and filling module",
    author="Engineersmind",
    author_email="team@engineersmind.com",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.9",
    install_requires=[
        # Core dependencies only - no cloud SDKs!
        # Populated from requirements.txt
    ],
    extras_require={
        "aws": [
            "boto3>=1.34.34",
            "botocore>=1.34.34",
        ],
        "azure": [
            "azure-storage-blob>=12.19.0",
            "azure-identity>=1.15.0",
        ],
        "gcp": [
            "google-cloud-storage>=2.14.0",
        ],
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.7.0",
            "flake8>=6.1.0",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
