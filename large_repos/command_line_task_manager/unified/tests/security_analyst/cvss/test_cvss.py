"""Tests for the CVSS Calculator module."""

import time
import pytest
from pydantic import ValidationError

from securetask.utils.validation import ValidationError as CustomValidationError
from securetask.cvss.calculator import (
    CVSSVector, CVSSCalculator, AttackVector, AttackComplexity,
    PrivilegesRequired, UserInteraction, Scope, Impact, SeverityRating
)


def test_cvss_vector_validation():
    """Test that CVSS vector validation works correctly."""
    # Valid vector
    vector = CVSSVector(
        attack_vector="N",
        attack_complexity="L",
        privileges_required="N",
        user_interaction="N",
        scope="U",
        confidentiality="H",
        integrity="H",
        availability="H"
    )
    
    assert vector.attack_vector == "N"
    assert vector.attack_complexity == "L"
    
    # Invalid attack vector
    with pytest.raises(CustomValidationError):
        CVSSVector(
            attack_vector="X",  # Invalid
            attack_complexity="L",
            privileges_required="N",
            user_interaction="N",
            scope="U",
            confidentiality="H",
            integrity="H",
            availability="H"
        )
    
    # Invalid scope
    with pytest.raises(CustomValidationError):
        CVSSVector(
            attack_vector="N",
            attack_complexity="L",
            privileges_required="N",
            user_interaction="N",
            scope="X",  # Invalid
            confidentiality="H",
            integrity="H",
            availability="H"
        )


def test_cvss_vector_string_conversion():
    """Test conversion between vector objects and vector strings."""
    # Create a vector
    vector = CVSSVector(
        attack_vector="N",
        attack_complexity="L",
        privileges_required="N",
        user_interaction="N",
        scope="U",
        confidentiality="H",
        integrity="H",
        availability="H"
    )
    
    # Convert to vector string
    vector_string = vector.to_vector_string()
    
    # Should match expected format
    assert vector_string == "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
    
    # Convert back to vector
    parsed_vector = CVSSVector.from_vector_string(vector_string)
    
    # Should match original values
    assert parsed_vector.attack_vector == vector.attack_vector
    assert parsed_vector.attack_complexity == vector.attack_complexity
    assert parsed_vector.privileges_required == vector.privileges_required
    assert parsed_vector.user_interaction == vector.user_interaction
    assert parsed_vector.scope == vector.scope
    assert parsed_vector.confidentiality == vector.confidentiality
    assert parsed_vector.integrity == vector.integrity
    assert parsed_vector.availability == vector.availability
    
    # Test with temporal metrics
    vector_with_temporal = CVSSVector(
        attack_vector="N",
        attack_complexity="L",
        privileges_required="N",
        user_interaction="N",
        scope="U",
        confidentiality="H",
        integrity="H",
        availability="H",
        exploit_code_maturity="F",
        remediation_level="O",
        report_confidence="C"
    )
    
    temporal_string = vector_with_temporal.to_vector_string()
    
    # Should include temporal metrics
    assert "E:F" in temporal_string
    assert "RL:O" in temporal_string
    assert "RC:C" in temporal_string
    
    # Convert back
    parsed_temporal = CVSSVector.from_vector_string(temporal_string)
    
    assert parsed_temporal.exploit_code_maturity == "F"
    assert parsed_temporal.remediation_level == "O"
    assert parsed_temporal.report_confidence == "C"
    
    # Invalid vector string
    with pytest.raises(CustomValidationError):
        CVSSVector.from_vector_string("CVSS:3.1/InvalidVector")
        
    # Incomplete vector string
    with pytest.raises(CustomValidationError):
        CVSSVector.from_vector_string("CVSS:3.1/AV:N/AC:L")  # Missing required metrics


def test_cvss_score_calculation():
    """Test CVSS score calculation against official examples."""
    # Example 1: Critical severity (AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H) = 9.8
    vector1 = CVSSVector(
        attack_vector="N",
        attack_complexity="L",
        privileges_required="N",
        user_interaction="N",
        scope="U",
        confidentiality="H",
        integrity="H",
        availability="H"
    )
    
    score1, severity1 = CVSSCalculator.calculate_score(vector1)
    
    assert score1 == 9.8
    assert severity1 == SeverityRating.CRITICAL.value
    
    # Example 2: High severity (AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N) = 7.5
    vector2 = CVSSVector(
        attack_vector="N",
        attack_complexity="L",
        privileges_required="N",
        user_interaction="N",
        scope="U",
        confidentiality="H",
        integrity="N",
        availability="N"
    )
    
    score2, severity2 = CVSSCalculator.calculate_score(vector2)
    
    assert score2 == 7.5
    assert severity2 == SeverityRating.HIGH.value
    
    # Example 3: Medium severity (AV:L/AC:H/PR:L/UI:R/S:U/C:H/I:N/A:N) = 4.2
    vector3 = CVSSVector(
        attack_vector="L",
        attack_complexity="H",
        privileges_required="L",
        user_interaction="R",
        scope="U",
        confidentiality="H",
        integrity="N",
        availability="N"
    )
    
    score3, severity3 = CVSSCalculator.calculate_score(vector3)
    
    assert score3 == 4.2
    assert severity3 == SeverityRating.MEDIUM.value
    
    # Example 4: Low severity (AV:P/AC:H/PR:H/UI:R/S:U/C:L/I:N/A:N) = 1.6
    vector4 = CVSSVector(
        attack_vector="P",
        attack_complexity="H",
        privileges_required="H",
        user_interaction="R",
        scope="U",
        confidentiality="L",
        integrity="N",
        availability="N"
    )
    
    score4, severity4 = CVSSCalculator.calculate_score(vector4)
    
    assert score4 == 1.6
    assert severity4 == SeverityRating.LOW.value
    
    # Example 5: None severity (AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:N/A:N) = 0.0
    vector5 = CVSSVector(
        attack_vector="N",
        attack_complexity="L",
        privileges_required="L",
        user_interaction="N",
        scope="U",
        confidentiality="N",
        integrity="N",
        availability="N"
    )
    
    score5, severity5 = CVSSCalculator.calculate_score(vector5)
    
    assert score5 == 0.0
    assert severity5 == SeverityRating.NONE.value


def test_cvss_calculation_with_scope_change():
    """Test CVSS calculation with scope change."""
    # Example with Scope = Changed (AV:N/AC:L/PR:L/UI:N/S:C/C:H/I:H/A:H) = 9.9
    vector = CVSSVector(
        attack_vector="N",
        attack_complexity="L",
        privileges_required="L",
        user_interaction="N",
        scope="C",
        confidentiality="H",
        integrity="H",
        availability="H"
    )
    
    score, severity = CVSSCalculator.calculate_score(vector)
    
    assert score == 9.9
    assert severity == SeverityRating.CRITICAL.value
    
    # Scope change affects privilege required values
    # AV:N/AC:L/PR:H/UI:N/S:C/C:H/I:H/A:H = 9.1
    vector2 = CVSSVector(
        attack_vector="N",
        attack_complexity="L",
        privileges_required="H",
        user_interaction="N",
        scope="C",
        confidentiality="H",
        integrity="H",
        availability="H"
    )
    
    score2, severity2 = CVSSCalculator.calculate_score(vector2)
    
    assert score2 == 9.1
    assert severity2 == SeverityRating.CRITICAL.value
    
    # Same vector but with Scope = Unchanged
    # AV:N/AC:L/PR:H/UI:N/S:U/C:H/I:H/A:H = 7.2
    vector3 = CVSSVector(
        attack_vector="N",
        attack_complexity="L",
        privileges_required="H",
        user_interaction="N",
        scope="U",
        confidentiality="H",
        integrity="H",
        availability="H"
    )
    
    score3, severity3 = CVSSCalculator.calculate_score(vector3)
    
    assert score3 == 7.2
    assert severity3 == SeverityRating.HIGH.value


def test_cvss_calculation_with_temporal_metrics():
    """Test CVSS calculation with temporal metrics."""
    # Base vector: AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H = 9.8 (Critical)
    base_vector = CVSSVector(
        attack_vector="N",
        attack_complexity="L",
        privileges_required="N",
        user_interaction="N",
        scope="U",
        confidentiality="H",
        integrity="H",
        availability="H"
    )
    
    base_score, _ = CVSSCalculator.calculate_score(base_vector)
    assert base_score == 9.8
    
    # Add temporal metrics (E:P/RL:T/RC:R)
    temporal_vector = CVSSVector(
        attack_vector="N",
        attack_complexity="L",
        privileges_required="N",
        user_interaction="N",
        scope="U",
        confidentiality="H",
        integrity="H",
        availability="H",
        exploit_code_maturity="P",  # Proof-of-Concept
        remediation_level="T",      # Temporary Fix
        report_confidence="R"       # Reasonable
    )
    
    temporal_score, _ = CVSSCalculator.calculate_score(temporal_vector)
    
    # Temporal score should be lower than base score
    assert temporal_score < base_score
    
    # Highest temporal effect (E:H/RL:U/RC:C) should equal base score
    max_temporal_vector = CVSSVector(
        attack_vector="N",
        attack_complexity="L",
        privileges_required="N",
        user_interaction="N",
        scope="U",
        confidentiality="H",
        integrity="H",
        availability="H",
        exploit_code_maturity="H",  # High
        remediation_level="U",      # Unavailable
        report_confidence="C"       # Confirmed
    )
    
    max_temporal_score, _ = CVSSCalculator.calculate_score(max_temporal_vector)
    assert max_temporal_score == base_score


def test_cvss_vector_string_parsing():
    """Test parsing of CVSS vector strings."""
    # Parse vector string
    vector_string = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
    metrics = CVSSCalculator.parse_vector_string(vector_string)
    
    assert metrics["AV"] == "N"
    assert metrics["AC"] == "L"
    assert metrics["PR"] == "N"
    assert metrics["UI"] == "N"
    assert metrics["S"] == "U"
    assert metrics["C"] == "H"
    assert metrics["I"] == "H"
    assert metrics["A"] == "H"
    
    # Parse vector with temporal metrics
    temporal_string = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H/E:F/RL:O/RC:C"
    temporal_metrics = CVSSCalculator.parse_vector_string(temporal_string)
    
    assert temporal_metrics["E"] == "F"
    assert temporal_metrics["RL"] == "O"
    assert temporal_metrics["RC"] == "C"
    
    # Validate vector string
    assert CVSSCalculator.validate_vector_string(vector_string) == True
    assert CVSSCalculator.validate_vector_string(temporal_string) == True
    
    # Invalid vector string
    assert CVSSCalculator.validate_vector_string("CVSS:3.1/InvalidVector") == False
    assert CVSSCalculator.validate_vector_string("CVSS:3.1/AV:N/AC:L") == False
    assert CVSSCalculator.validate_vector_string("CVSS:3.1/AV:X/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H") == False


def test_cvss_performance():
    """Test CVSS calculation performance."""
    # Create test vectors
    vectors = [
        # Critical
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        # High
        "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H",
        # Medium
        "CVSS:3.1/AV:N/AC:H/PR:L/UI:R/S:U/C:H/I:L/A:L",
        # Low
        "CVSS:3.1/AV:L/AC:H/PR:H/UI:R/S:U/C:L/I:N/A:N",
        # None
        "CVSS:3.1/AV:N/AC:L/PR:H/UI:N/S:U/C:N/I:N/A:N"
    ]
    
    # Test performance for each vector
    for vector_string in vectors:
        start_time = time.time()
        score, severity = CVSSCalculator.calculate_score(vector_string)
        execution_time = time.time() - start_time
        
        # Assert performance is under 50ms per calculation
        assert execution_time < 0.05, f"CVSS calculation took {execution_time*1000:.2f}ms, should be <50ms"
    
    # Test batch performance (1000 calculations)
    batch_size = 1000
    start_time = time.time()
    
    for _ in range(batch_size):
        # Use first vector for batch test
        CVSSCalculator.calculate_score(vectors[0])
        
    total_time = time.time() - start_time
    
    # According to requirements: CVSS calculations must process at least 1000 scores per second
    calc_per_second = batch_size / total_time
    assert calc_per_second >= 1000, f"Performance: {calc_per_second:.2f} calculations/second, should be ≥1000"
    
    print(f"CVSS Performance: {calc_per_second:.2f} calculations/second")


def test_cvss_edge_cases():
    """Test CVSS calculation edge cases and invalid combinations."""
    # Edge case: Zero impact (C:N/I:N/A:N)
    zero_impact = CVSSVector(
        attack_vector="N",
        attack_complexity="L",
        privileges_required="N",
        user_interaction="N",
        scope="U",
        confidentiality="N",
        integrity="N",
        availability="N"
    )
    
    score, severity = CVSSCalculator.calculate_score(zero_impact)
    assert score == 0.0
    assert severity == SeverityRating.NONE.value
    
    # Edge case: Physical attack vector with network impact
    edge_case1 = CVSSVector(
        attack_vector="P",  # Physical
        attack_complexity="H",
        privileges_required="H",
        user_interaction="R",
        scope="C",  # Changed
        confidentiality="H",
        integrity="H",
        availability="H"
    )
    
    # Should still calculate without errors
    score1, _ = CVSSCalculator.calculate_score(edge_case1)
    assert score1 > 0
    
    # Test with invalid metric combinations from a string
    # The validation happens when creating the object, so we need to test parse methods
    with pytest.raises(CustomValidationError):
        CVSSVector.from_vector_string("CVSS:3.1/AV:Q/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H")
        
    # Test with metrics missing
    with pytest.raises(CustomValidationError):
        CVSSVector.from_vector_string("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H")  # Missing A