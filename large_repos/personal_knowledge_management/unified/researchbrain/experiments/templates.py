"""Experiment template functionality for ResearchBrain."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from jinja2 import Template


TEMPLATE_DIR = Path(__file__).parent / "template_definitions"


def get_template(template_name: str) -> Optional[Dict[str, Any]]:
    """Get an experiment template by name.
    
    Args:
        template_name: Name of the template to retrieve.
        
    Returns:
        Template definition dictionary if found, None otherwise.
    """
    if not TEMPLATE_DIR.exists():
        TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
        # Create default templates
        create_default_templates()
    
    template_path = TEMPLATE_DIR / f"{template_name}.yaml"
    if not template_path.exists():
        # Try as a partial match
        for file_path in TEMPLATE_DIR.glob("*.yaml"):
            if template_name.lower() in file_path.stem.lower():
                template_path = file_path
                break
        else:
            return None
    
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template = yaml.safe_load(f)
        return template
    except (yaml.YAMLError, IOError):
        return None


def list_templates() -> List[str]:
    """List all available experiment templates.
    
    Returns:
        List of template names.
    """
    if not TEMPLATE_DIR.exists():
        TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
        create_default_templates()
    
    return [file_path.stem for file_path in TEMPLATE_DIR.glob("*.yaml")]


def create_template(template_name: str, template_definition: Dict[str, Any]) -> bool:
    """Create a new experiment template.
    
    Args:
        template_name: Name for the new template.
        template_definition: Template definition dictionary.
        
    Returns:
        True if successful, False otherwise.
    """
    if not TEMPLATE_DIR.exists():
        TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    
    template_path = TEMPLATE_DIR / f"{template_name}.yaml"
    
    try:
        with open(template_path, "w", encoding="utf-8") as f:
            yaml.dump(template_definition, f, default_flow_style=False, sort_keys=False)
        return True
    except (yaml.YAMLError, IOError):
        return False


def apply_template(template: Dict[str, Any], values: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Apply values to an experiment template.
    
    Args:
        template: Template definition dictionary.
        values: Values to apply to the template.
        
    Returns:
        Completed experiment data dictionary if successful, None otherwise.
    """
    if "fields" not in template or "output_format" not in template:
        return None
    
    # Validate required fields
    required_fields = [field["name"] for field in template["fields"] if field.get("required")]
    for field_name in required_fields:
        if field_name not in values:
            return None
    
    # Prepare template variables
    template_vars = {}
    for field in template["fields"]:
        field_name = field["name"]
        if field_name in values:
            template_vars[field_name] = values[field_name]
        elif "default" in field:
            template_vars[field_name] = field["default"]
    
    # Apply Jinja2 templates to output format
    output_format = template["output_format"]
    result = {}

    for key, value in output_format.items():
        if isinstance(value, str):
            # Apply template to string value
            jinja_template = Template(value)
            result[key] = jinja_template.render(**template_vars)
        elif isinstance(value, dict):
            # Handle nested dictionaries by applying templates to values
            result[key] = {}
            for sub_key, sub_value in value.items():
                if isinstance(sub_value, str):
                    jinja_template = Template(sub_value)
                    result[key][sub_key] = jinja_template.render(**template_vars)
                else:
                    result[key][sub_key] = sub_value
        else:
            # Copy non-string values as is
            result[key] = value
    
    return result


def create_default_templates() -> None:
    """Create default experiment templates."""
    # Behavioral experiment template
    behavioral_template = {
        "name": "Behavioral Experiment",
        "description": "Template for behavioral experiments with human or animal subjects",
        "fields": [
            {
                "name": "title",
                "type": "string",
                "description": "Title of the experiment",
                "required": True
            },
            {
                "name": "hypothesis",
                "type": "string",
                "description": "Main hypothesis being tested",
                "required": True
            },
            {
                "name": "participants",
                "type": "string",
                "description": "Description of participants or subjects",
                "required": True
            },
            {
                "name": "independent_variables",
                "type": "string",
                "description": "Independent variables being manipulated",
                "required": True
            },
            {
                "name": "dependent_variables",
                "type": "string",
                "description": "Dependent variables being measured",
                "required": True
            },
            {
                "name": "control_condition",
                "type": "string",
                "description": "Description of control condition",
                "required": False
            },
            {
                "name": "procedure",
                "type": "string",
                "description": "Step-by-step experimental procedure",
                "required": True
            },
            {
                "name": "analysis_plan",
                "type": "string",
                "description": "Statistical analysis plan",
                "required": False,
                "default": "To be determined based on initial results."
            }
        ],
        "output_format": {
            "title": "{{ title }}",
            "hypothesis": "{{ hypothesis }}",
            "methodology": """# Behavioral Experiment Methodology

## Participants
{{ participants }}

## Design
Independent Variables: {{ independent_variables }}
Dependent Variables: {{ dependent_variables }}
{% if control_condition %}Control Condition: {{ control_condition }}{% endif %}

## Procedure
{{ procedure }}

## Analysis Plan
{{ analysis_plan }}""",
            "variables": {
                "participants": "{{ participants }}",
                "independent_vars": "{{ independent_variables }}",
                "dependent_vars": "{{ dependent_variables }}"
            },
            "status": "planned"
        }
    }
    
    # Neuroimaging experiment template
    neuroimaging_template = {
        "name": "Neuroimaging Experiment",
        "description": "Template for fMRI, EEG, or other neuroimaging experiments",
        "fields": [
            {
                "name": "title",
                "type": "string",
                "description": "Title of the experiment",
                "required": True
            },
            {
                "name": "hypothesis",
                "type": "string",
                "description": "Main hypothesis being tested",
                "required": True
            },
            {
                "name": "imaging_modality",
                "type": "string",
                "description": "Imaging modality (fMRI, EEG, MEG, etc.)",
                "required": True
            },
            {
                "name": "participants",
                "type": "string",
                "description": "Description of participants",
                "required": True
            },
            {
                "name": "task_design",
                "type": "string",
                "description": "Detailed description of experimental task",
                "required": True
            },
            {
                "name": "regions_of_interest",
                "type": "string",
                "description": "Brain regions of primary interest",
                "required": False
            },
            {
                "name": "acquisition_parameters",
                "type": "string",
                "description": "Technical parameters for data acquisition",
                "required": True
            },
            {
                "name": "preprocessing",
                "type": "string",
                "description": "Data preprocessing pipeline",
                "required": True
            },
            {
                "name": "analysis_plan",
                "type": "string",
                "description": "Data analysis approach",
                "required": True
            }
        ],
        "output_format": {
            "title": "{{ title }}",
            "hypothesis": "{{ hypothesis }}",
            "methodology": """# Neuroimaging Experiment Methodology

## Imaging Modality
{{ imaging_modality }}

## Participants
{{ participants }}

## Task Design
{{ task_design }}

{% if regions_of_interest %}## Regions of Interest
{{ regions_of_interest }}{% endif %}

## Acquisition Parameters
{{ acquisition_parameters }}

## Preprocessing
{{ preprocessing }}

## Analysis Plan
{{ analysis_plan }}""",
            "variables": {
                "modality": "{{ imaging_modality }}",
                "participants": "{{ participants }}",
                "roi": "{% if regions_of_interest %}{{ regions_of_interest }}{% else %}Not specified{% endif %}"
            },
            "status": "planned"
        }
    }
    
    # Molecular biology experiment template
    molecular_template = {
        "name": "Molecular Biology Experiment",
        "description": "Template for molecular biology laboratory experiments",
        "fields": [
            {
                "name": "title",
                "type": "string",
                "description": "Title of the experiment",
                "required": True
            },
            {
                "name": "hypothesis",
                "type": "string",
                "description": "Main hypothesis being tested",
                "required": True
            },
            {
                "name": "cell_line",
                "type": "string",
                "description": "Cell lines or model organisms used",
                "required": True
            },
            {
                "name": "reagents",
                "type": "string",
                "description": "Key reagents and materials",
                "required": True
            },
            {
                "name": "techniques",
                "type": "string",
                "description": "Techniques used (PCR, Western Blot, CRISPR, etc.)",
                "required": True
            },
            {
                "name": "controls",
                "type": "string",
                "description": "Positive and negative controls",
                "required": True
            },
            {
                "name": "protocol",
                "type": "string",
                "description": "Detailed experimental protocol",
                "required": True
            },
            {
                "name": "analysis",
                "type": "string",
                "description": "Data analysis methods",
                "required": True
            }
        ],
        "output_format": {
            "title": "{{ title }}",
            "hypothesis": "{{ hypothesis }}",
            "methodology": """# Molecular Biology Experiment Protocol

## Materials
Cell Line/Model: {{ cell_line }}

## Reagents
{{ reagents }}

## Techniques
{{ techniques }}

## Controls
{{ controls }}

## Protocol
{{ protocol }}

## Analysis
{{ analysis }}""",
            "variables": {
                "cell_line": "{{ cell_line }}",
                "techniques": "{{ techniques }}",
                "controls": "{{ controls }}"
            },
            "status": "planned"
        }
    }
    
    # Computational modeling experiment template
    computational_template = {
        "name": "Computational Modeling Experiment",
        "description": "Template for computational or simulation-based experiments",
        "fields": [
            {
                "name": "title",
                "type": "string",
                "description": "Title of the experiment",
                "required": True
            },
            {
                "name": "hypothesis",
                "type": "string",
                "description": "Main hypothesis being tested",
                "required": True
            },
            {
                "name": "model_type",
                "type": "string",
                "description": "Type of computational model",
                "required": True
            },
            {
                "name": "parameters",
                "type": "string",
                "description": "Key model parameters",
                "required": True
            },
            {
                "name": "input_data",
                "type": "string",
                "description": "Description of input data",
                "required": False
            },
            {
                "name": "algorithm",
                "type": "string",
                "description": "Algorithm or computational approach",
                "required": True
            },
            {
                "name": "validation",
                "type": "string",
                "description": "Validation and testing approach",
                "required": True
            },
            {
                "name": "software",
                "type": "string",
                "description": "Software and computing resources",
                "required": True
            }
        ],
        "output_format": {
            "title": "{{ title }}",
            "hypothesis": "{{ hypothesis }}",
            "methodology": """# Computational Modeling Methodology

## Model Type
{{ model_type }}

## Parameters
{{ parameters }}

{% if input_data %}## Input Data
{{ input_data }}{% endif %}

## Algorithm
{{ algorithm }}

## Validation Approach
{{ validation }}

## Software & Computing Resources
{{ software }}""",
            "variables": {
                "model_type": "{{ model_type }}",
                "parameters": "{{ parameters }}",
                "algorithm": "{{ algorithm }}",
                "software": "{{ software }}"
            },
            "status": "planned"
        }
    }
    
    # Create the default templates
    create_template("behavioral_experiment", behavioral_template)
    create_template("neuroimaging_experiment", neuroimaging_template)
    create_template("molecular_biology_experiment", molecular_template)
    create_template("computational_modeling_experiment", computational_template)