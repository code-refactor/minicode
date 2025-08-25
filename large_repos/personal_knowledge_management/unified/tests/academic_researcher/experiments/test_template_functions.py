"""Tests for experiment template functions."""

import os
import shutil
import tempfile
from pathlib import Path

import pytest
import yaml

from researchbrain.experiments.templates import (
    get_template, list_templates, create_template,
    apply_template, create_default_templates, TEMPLATE_DIR
)


class TestTemplatesFunctions:
    """Test individual template functions."""

    @pytest.fixture
    def temp_template_dir(self):
        """Create a temporary template directory."""
        original_template_dir = TEMPLATE_DIR
        temp_dir = Path(tempfile.mkdtemp())
        
        # Override the global TEMPLATE_DIR
        import researchbrain.experiments.templates
        researchbrain.experiments.templates.TEMPLATE_DIR = temp_dir
        
        yield temp_dir
        
        # Restore original and clean up
        researchbrain.experiments.templates.TEMPLATE_DIR = original_template_dir
        shutil.rmtree(temp_dir)
    
    def test_create_default_templates(self, temp_template_dir):
        """Test that default templates are created correctly."""
        create_default_templates()
        
        # Verify template files exist
        template_files = list(temp_template_dir.glob("*.yaml"))
        assert len(template_files) > 0
        
        # Check specific templates
        assert (temp_template_dir / "behavioral_experiment.yaml").exists()
        assert (temp_template_dir / "neuroimaging_experiment.yaml").exists()
    
    def test_list_templates(self, temp_template_dir):
        """Test listing templates."""
        # Create default templates first since the directory is empty
        create_default_templates()
        
        # Now list templates
        templates = list_templates()
        assert len(templates) > 0
        assert "behavioral_experiment" in templates
        
        # Add a custom template
        custom_template = {
            "name": "Custom Template",
            "fields": [],
            "output_format": {}
        }
        with open(temp_template_dir / "custom_template.yaml", "w") as f:
            yaml.dump(custom_template, f)
        
        # Should include the new template
        templates = list_templates()
        assert "custom_template" in templates
    
    def test_get_template(self, temp_template_dir):
        """Test retrieving templates."""
        create_default_templates()
        
        # Get existing template
        template = get_template("behavioral_experiment")
        assert template is not None
        assert template["name"] == "Behavioral Experiment"
        
        # Test partial name matching
        template = get_template("behavior")
        assert template is not None
        assert "Behavioral" in template["name"]
        
        # Test non-existent template
        template = get_template("nonexistent_template")
        assert template is None
    
    def test_create_template(self, temp_template_dir):
        """Test creating a new template."""
        test_template = {
            "name": "Test Template",
            "description": "A test template",
            "fields": [
                {
                    "name": "title",
                    "type": "string",
                    "required": True
                }
            ],
            "output_format": {
                "title": "{{ title }}"
            }
        }
        
        # Create the template
        result = create_template("test_template", test_template)
        assert result is True
        
        # Verify it was created
        assert (temp_template_dir / "test_template.yaml").exists()
        
        # Load and verify content
        with open(temp_template_dir / "test_template.yaml", "r") as f:
            loaded = yaml.safe_load(f)
        
        assert loaded["name"] == "Test Template"
        assert loaded["fields"][0]["name"] == "title"
    
    def test_apply_template(self, temp_template_dir):
        """Test applying values to a template."""
        test_template = {
            "name": "Test Template",
            "fields": [
                {
                    "name": "title",
                    "required": True
                },
                {
                    "name": "optional_field",
                    "required": False,
                    "default": "Default Value"
                }
            ],
            "output_format": {
                "title": "{{ title }}",
                "description": "Template with {{ title }} and {{ optional_field }}",
                "nested": {
                    "field1": "Nested {{ title }}",
                    "field2": "Static text"
                }
            }
        }
        
        # Test with all values provided
        values = {
            "title": "Test Title",
            "optional_field": "Custom Value"
        }
        
        result = apply_template(test_template, values)
        assert result is not None
        assert result["title"] == "Test Title"
        assert result["description"] == "Template with Test Title and Custom Value"
        assert result["nested"]["field1"] == "Nested Test Title"
        assert result["nested"]["field2"] == "Static text"
        
        # Test with missing optional field (should use default)
        values = {
            "title": "Test Title"
        }
        
        result = apply_template(test_template, values)
        assert result is not None
        assert result["description"] == "Template with Test Title and Default Value"
        
        # Test with missing required field
        values = {
            "optional_field": "Only Optional"
        }
        
        result = apply_template(test_template, values)
        assert result is None
        
        # Test with invalid template (missing required keys)
        invalid_template = {
            "name": "Invalid Template"
            # Missing fields and output_format
        }
        
        result = apply_template(invalid_template, values)
        assert result is None