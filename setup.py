from setuptools import setup, find_packages

setup(
    name="netemulator",
    version="0.1.0",
    description="Continuous Internet Testbed for AppNeta",
    author="AppNeta Engineering",
    author_email="engineering@appneta.com",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        line.strip()
        for line in open("requirements.txt")
        if line.strip() and not line.startswith("#")
    ],
    entry_points={
        "console_scripts": [
            "netemulator=netemulator.cli:cli",
            "netemulator-api=netemulator.control.api:main",
            "netemulator-scheduler=netemulator.control.scheduler:main",
            "netemulator-dashboard=netemulator.observability.dashboard:main",
        ]
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: System :: Networking",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)

