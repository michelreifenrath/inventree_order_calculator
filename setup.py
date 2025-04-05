import setuptools

# Read the contents of README file
from pathlib import Path
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

# Read the contents of requirements.txt
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setuptools.setup(
    name="inventree-order-calculator",
    version="0.1.0", # Match version in plugin.py
    author="Cline (AI Assistant)", # Or your name/org
    author_email="user@example.com", # Replace with actual email
    description="InvenTree plugin: BOM Order Calculator",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords="inventree inventory bom calculator plugin",
    url="<plugin-repo-url>", # Optional: URL to the plugin's repository
    license="MIT",
    packages=setuptools.find_packages(),
    install_requires=requirements, # Install dependencies from requirements.txt
    setup_requires=[
        "wheel",
        "setuptools",
    ],
    python_requires=">=3.9",
    entry_points={
        "inventree_plugins": [
            "OrderCalculatorPlugin = order_calculator.plugin:OrderCalculatorPlugin"
        ]
    },
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Framework :: Django",
        "Framework :: Django :: 4.2", # Adjust based on target InvenTree Django version
    ],
)
