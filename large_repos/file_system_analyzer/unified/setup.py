from setuptools import setup

setup(
    name="unified-file_system_analyzer",
    version="0.1.0",
    description="Unified libraries for file_system_analyzer with original package names preserved",
    packages=["common", "file_system_analyzer_db_admin", "file_system_analyzer"],
    python_requires=">=3.10",
)
