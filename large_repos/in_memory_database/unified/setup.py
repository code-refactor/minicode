from setuptools import setup

setup(
    name="unified-in_memory_database",
    version="0.1.0",
    description="Unified libraries for in_memory_database with original package names preserved",
    packages=["common", "vectordb", "syncdb"],
    python_requires=">=3.10",
)
