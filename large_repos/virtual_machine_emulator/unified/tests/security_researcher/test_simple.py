"""
A simple test to verify the package is installed correctly.
"""

def test_import():
    """Test that the package can be imported."""
    import secure_vm
    assert secure_vm.__version__ == "0.1.0"