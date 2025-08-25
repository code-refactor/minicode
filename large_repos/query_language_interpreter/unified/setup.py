from setuptools import setup

setup(
    name="unified-query_language_interpreter",
    version="0.1.0",
    description="Unified libraries for query_language_interpreter with original package names preserved",
    packages=["common", "legal_discovery_interpreter", "privacy_query_interpreter"],
    python_requires=">=3.10",
)
