"""Tests for experiment templates."""

import os
import shutil
import tempfile
from pathlib import Path

import pytest
import yaml

from researchbrain.experiments.templates import (
    get_template, list_templates, create_template, apply_template,
    create_default_templates, TEMPLATE_DIR
)


class TestExperimentTemplates:
    """Tests for experiment templates functionality."""
    
    @pytest.fixture
    def temp_template_dir(self, monkeypatch):
        """Fixture that creates a temporary directory for templates."""
        temp_dir = tempfile.mkdtemp()
        
        # Monkeypatch the template directory
        monkeypatch.setattr("researchbrain.experiments.templates.TEMPLATE_DIR", Path(temp_dir))
        
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    def test_create_default_templates(self, temp_template_dir):
        """Test creating default templates."""
        # Create default templates
        create_default_templates()
        
        # Check that templates were created
        template_dir = Path(temp_template_dir)
        
        assert (template_dir / "behavioral_experiment.yaml").exists()
        assert (template_dir / "neuroimaging_experiment.yaml").exists()
        assert (template_dir / "molecular_biology_experiment.yaml").exists()
        assert (template_dir / "computational_modeling_experiment.yaml").exists()
        
        # Check content of one template
        with open(template_dir / "behavioral_experiment.yaml", "r") as f:
            template = yaml.safe_load(f)
        
        assert template["name"] == "Behavioral Experiment"
        assert "fields" in template
        assert "output_format" in template
    
    def test_get_template(self, temp_template_dir):
        """Test getting a template by name."""
        # Create default templates
        create_default_templates()
        
        # Get a template
        template = get_template("behavioral_experiment")
        
        assert template is not None
        assert template["name"] == "Behavioral Experiment"
        assert template["description"] == "Template for behavioral experiments with human or animal subjects"
        
        # Test partial match
        template = get_template("neuroimaging")
        
        assert template is not None
        assert template["name"] == "Neuroimaging Experiment"
        
        # Test nonexistent template
        template = get_template("nonexistent_template")
        
        assert template is None
    
    def test_list_templates(self, temp_template_dir):
        """Test listing available templates."""
        # Create default templates
        create_default_templates()
        
        # List templates
        templates = list_templates()
        
        assert "behavioral_experiment" in templates
        assert "neuroimaging_experiment" in templates
        assert "molecular_biology_experiment" in templates
        assert "computational_modeling_experiment" in templates
        assert len(templates) == 4
    
    def test_create_template(self, temp_template_dir):
        """Test creating a new template."""
        # Define a template
        template_definition = {
            "name": "Custom Template",
            "description": "A custom experiment template",
            "fields": [
                {
                    "name": "title",
                    "type": "string",
                    "description": "Experiment title",
                    "required": True
                },
                {
                    "name": "description",
                    "type": "string",
                    "description": "Experiment description",
                    "required": False
                }
            ],
            "output_format": {
                "title": "{{ title }}",
                "methodology": "{{ description }}",
                "status": "planned"
            }
        }
        
        # Create the template
        result = create_template("custom_template", template_definition)
        
        assert result is True
        
        # Check that the template was created
        template = get_template("custom_template")
        
        assert template is not None
        assert template["name"] == "Custom Template"
        assert len(template["fields"]) == 2
    
    def test_apply_template(self, temp_template_dir):
        """Test applying values to a template."""
        # Create a template
        template_definition = {
            "name": "Test Template",
            "description": "Template for testing",
            "fields": [
                {
                    "name": "title",
                    "type": "string",
                    "description": "Experiment title",
                    "required": True
                },
                {
                    "name": "participants",
                    "type": "string",
                    "description": "Participant description",
                    "required": True
                },
                {
                    "name": "optional_field",
                    "type": "string",
                    "description": "Optional field",
                    "required": False,
                    "default": "Default value"
                }
            ],
            "output_format": {
                "title": "{{ title }}",
                "methodology": "Participants: {{ participants }}",
                "variables": {
                    "participants": "{{ participants }}",
                    "optional": "{{ optional_field }}"
                },
                "status": "planned"
            }
        }
        
        create_template("test_template", template_definition)
        
        # Apply values to the template
        values = {
            "title": "Test Experiment",
            "participants": "30 healthy adults"
        }
        
        result = apply_template(template_definition, values)
        
        assert result is not None
        assert result["title"] == "Test Experiment"
        assert result["methodology"] == "Participants: 30 healthy adults"
        assert result["variables"]["participants"] == "30 healthy adults"
        assert result["variables"]["optional"] == "Default value"  # Default value used
        assert result["status"] == "planned"
        
        # Test with all fields provided
        values = {
            "title": "Test Experiment",
            "participants": "30 healthy adults",
            "optional_field": "Custom value"
        }
        
        result = apply_template(template_definition, values)
        
        assert result["variables"]["optional"] == "Custom value"  # Custom value used
        
        # Test with missing required field
        values = {
            "title": "Test Experiment"
            # Missing 'participants'
        }
        
        result = apply_template(template_definition, values)
        
        assert result is None  # Should return None if required fields are missing
    
    def test_template_validation(self, temp_template_dir):
        """Test template validation."""
        # Template without required fields
        invalid_template = {
            "name": "Invalid Template",
            "description": "Invalid template missing required sections"
            # Missing 'fields' and 'output_format'
        }
        
        # Apply values to the invalid template
        values = {"title": "Test"}
        
        result = apply_template(invalid_template, values)
        
        assert result is None