"""
DroxAI Payment Fulfillment System - Setup Script
=================================================

Install with: pip install -e .
Or: python setup.py install

This script allows you to reinstall the entire payment fulfillment system
on a new machine or after a computer failure.
"""

from setuptools import setup, find_packages

with open("requirements_fulfillment.txt", "r") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

with open("FULFILLMENT_README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="droxai-payment-fulfillment",
    version="1.0.0",
    author="DroxAI LLC",
    author_email="droxai25@outlook.com",
    description="Payment fulfillment automation system for DroxAI products",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/moonrox420/ReviewReplyOrchestrator",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "": ["*.html", "*.md", "*.txt", "*.yml", "*.example"],
    },
    install_requires=requirements,
    python_requires=">=3.9",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Office/Business :: Financial",
    ],
    entry_points={
        "console_scripts": [
            "droxai-fulfillment=payment_orchestration.stripe_webhook:main",
        ],
    },
    project_urls={
        "Bug Tracker": "https://github.com/moonrox420/ReviewReplyOrchestrator/issues",
        "Documentation": "https://github.com/moonrox420/ReviewReplyOrchestrator/blob/main/FULFILLMENT_README.md",
        "Source Code": "https://github.com/moonrox420/ReviewReplyOrchestrator",
    },
)