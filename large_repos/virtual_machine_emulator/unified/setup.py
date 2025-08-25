from setuptools import setup

setup(
    name="unified-virtual_machine_emulator",
    version="0.1.0",
    description="Unified libraries for virtual_machine_emulator with original package names preserved",
    packages=["common", "vm_emulator", "secure_vm"],
    python_requires=">=3.10",
)
