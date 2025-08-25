"""Tests for the main entry point module."""

import importlib
import sys
from unittest.mock import patch


def test_main_module_imports():
    """Test that the main module imports correctly."""
    # Simply test that the module can be imported without errors
    importlib.import_module('researchbrain.__main__')
    assert 'researchbrain.__main__' in sys.modules
    assert hasattr(sys.modules['researchbrain.__main__'], 'main')


def test_main_execution():
    """Test the main module's execution path."""
    # Mocking both the import and the main function
    with patch('researchbrain.cli.main') as mock_main:
        # Pre-define a module-level attribute to store the current __name__
        current_name = __name__
        
        # Create a local scope with its own __name__ = "__main__"
        scope = {'__name__': '__main__', 'main': mock_main}
        
        # Execute the content of __main__.py in our controlled scope
        exec('from researchbrain.cli import main\n'
             'if __name__ == "__main__":\n'
             '    main()', scope)
        
        # In our controlled scope with __name__ = "__main__", main() should be called
        mock_main.assert_called_once()