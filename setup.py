"""
Setup script for WhatsApp Sales Agent Pro
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("config/requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="whatsapp-sales-agent-pro",
    version="1.0.0",
    author="Mohamed Shamil",
    author_email="mrmshamil1786@gmail.com",
    description="An intelligent WhatsApp sales agent powered by Google Gemini AI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/shamil3923/ERP_Recommendation_Widget-",
    project_urls={
        "Bug Tracker": "https://github.com/shamil3923/ERP_Recommendation_Widget-/issues",
        "Documentation": "https://github.com/shamil3923/ERP_Recommendation_Widget-/blob/main/README.md",
        "Source Code": "https://github.com/shamil3923/ERP_Recommendation_Widget-",
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Communications :: Chat",
        "Topic :: Office/Business :: Financial",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=0.991",
        ],
        "test": [
            "pytest>=7.0.0",
            "pytest-mock>=3.10.0",
            "requests-mock>=1.10.0",
        ],
        "docs": [
            "sphinx>=5.0.0",
            "sphinx-rtd-theme>=1.2.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "whatsapp-sales-agent=whatsapp_integration:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.md", "*.txt", "*.yml", "*.yaml"],
    },
    keywords="whatsapp, sales, agent, ai, chatbot, currency, conversion, gemini",
    zip_safe=False,
)
