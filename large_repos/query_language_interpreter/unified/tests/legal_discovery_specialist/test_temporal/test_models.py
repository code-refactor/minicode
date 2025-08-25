"""Tests for the temporal management models."""

import pytest
from datetime import datetime, date, timedelta
from legal_discovery_interpreter.temporal.models import (
    TimeUnit,
    TimePeriod,
    TimeframeType,
    LegalTimeframe,
    TimeframeCatalog,
    DateNormalizationFormat
)


def test_time_period():
    """Test creating and using time periods."""
    # Days
    period = TimePeriod(amount=10, unit=TimeUnit.DAYS)
    assert period.amount == 10
    assert period.unit == TimeUnit.DAYS
    assert period.to_timedelta() == timedelta(days=10)
    
    # Weeks
    period = TimePeriod(amount=2, unit=TimeUnit.WEEKS)
    assert period.amount == 2
    assert period.unit == TimeUnit.WEEKS
    assert period.to_timedelta() == timedelta(weeks=2)
    
    # Months (approximate)
    period = TimePeriod(amount=3, unit=TimeUnit.MONTHS)
    assert period.amount == 3
    assert period.unit == TimeUnit.MONTHS
    assert period.to_timedelta() == timedelta(days=3 * 30)
    
    # Years (approximate)
    period = TimePeriod(amount=2, unit=TimeUnit.YEARS)
    assert period.amount == 2
    assert period.unit == TimeUnit.YEARS
    assert period.to_timedelta() == timedelta(days=2 * 365)


def test_legal_timeframe():
    """Test creating and using legal timeframes."""
    # Timeframe with period
    timeframe = LegalTimeframe(
        timeframe_id="sol_contract",
        name="Contract Statute of Limitations",
        description="Statute of limitations for written contracts",
        timeframe_type=TimeframeType.STATUTE_OF_LIMITATIONS,
        period=TimePeriod(amount=6, unit=TimeUnit.YEARS),
        jurisdiction="NY",
        legal_reference="N.Y. C.P.L.R. § 213"
    )
    
    assert timeframe.timeframe_id == "sol_contract"
    assert timeframe.name == "Contract Statute of Limitations"
    assert timeframe.description == "Statute of limitations for written contracts"
    assert timeframe.timeframe_type == TimeframeType.STATUTE_OF_LIMITATIONS
    assert timeframe.period.amount == 6
    assert timeframe.period.unit == TimeUnit.YEARS
    assert timeframe.jurisdiction == "NY"
    assert timeframe.legal_reference == "N.Y. C.P.L.R. § 213"
    
    # Timeframe with fixed dates
    start_date = datetime(2020, 1, 1)
    end_date = datetime(2020, 12, 31)
    
    timeframe = LegalTimeframe(
        timeframe_id="discovery_period",
        name="Discovery Period",
        timeframe_type=TimeframeType.DISCOVERY_PERIOD,
        start_date=start_date,
        end_date=end_date
    )
    
    assert timeframe.timeframe_id == "discovery_period"
    assert timeframe.name == "Discovery Period"
    assert timeframe.timeframe_type == TimeframeType.DISCOVERY_PERIOD
    assert timeframe.start_date == start_date
    assert timeframe.end_date == end_date
    assert timeframe.period is None


def test_legal_timeframe_calculate_dates():
    """Test calculating dates from a legal timeframe."""
    # Timeframe with period
    timeframe = LegalTimeframe(
        timeframe_id="sol_contract",
        name="Contract Statute of Limitations",
        timeframe_type=TimeframeType.STATUTE_OF_LIMITATIONS,
        period=TimePeriod(amount=6, unit=TimeUnit.YEARS)
    )
    
    # Calculate with reference date
    reference_date = datetime(2020, 1, 1)
    dates = timeframe.calculate_dates(reference_date)
    
    assert 'start' in dates
    assert 'end' in dates
    assert dates['start'] == reference_date
    assert dates['end'] == reference_date + timedelta(days=6 * 365)
    
    # Timeframe with fixed dates
    start_date = datetime(2020, 1, 1)
    end_date = datetime(2020, 12, 31)
    
    timeframe = LegalTimeframe(
        timeframe_id="discovery_period",
        name="Discovery Period",
        timeframe_type=TimeframeType.DISCOVERY_PERIOD,
        start_date=start_date,
        end_date=end_date
    )
    
    # Calculate without reference date
    dates = timeframe.calculate_dates()
    
    assert 'start' in dates
    assert 'end' in dates
    assert dates['start'] == start_date
    assert dates['end'] == end_date


def test_timeframe_catalog():
    """Test creating and using a timeframe catalog."""
    catalog = TimeframeCatalog()
    
    assert len(catalog.timeframes) == 0
    
    # Create timeframes
    timeframe1 = LegalTimeframe(
        timeframe_id="sol_contract",
        name="Contract Statute of Limitations",
        timeframe_type=TimeframeType.STATUTE_OF_LIMITATIONS,
        period=TimePeriod(amount=6, unit=TimeUnit.YEARS),
        jurisdiction="NY"
    )
    
    timeframe2 = LegalTimeframe(
        timeframe_id="sol_tort",
        name="Tort Statute of Limitations",
        timeframe_type=TimeframeType.STATUTE_OF_LIMITATIONS,
        period=TimePeriod(amount=3, unit=TimeUnit.YEARS),
        jurisdiction="NY"
    )
    
    timeframe3 = LegalTimeframe(
        timeframe_id="discovery_period",
        name="Discovery Period",
        timeframe_type=TimeframeType.DISCOVERY_PERIOD,
        start_date=datetime(2020, 1, 1),
        end_date=datetime(2020, 12, 31)
    )
    
    # Add timeframes to catalog
    catalog.add_timeframe(timeframe1)
    catalog.add_timeframe(timeframe2)
    catalog.add_timeframe(timeframe3)
    
    assert len(catalog.timeframes) == 3
    assert catalog.count_timeframes() == 3
    
    # Get a timeframe
    tf = catalog.get_timeframe("sol_contract")
    assert tf is not None
    assert tf.timeframe_id == "sol_contract"
    assert tf.name == "Contract Statute of Limitations"
    
    # Get timeframes by type
    statutes = catalog.get_timeframes_by_type(TimeframeType.STATUTE_OF_LIMITATIONS)
    assert len(statutes) == 2
    assert statutes[0].timeframe_id in ["sol_contract", "sol_tort"]
    assert statutes[1].timeframe_id in ["sol_contract", "sol_tort"]
    
    # Get timeframes by jurisdiction
    ny_timeframes = catalog.get_timeframes_by_jurisdiction("NY")
    assert len(ny_timeframes) == 2
    assert ny_timeframes[0].timeframe_id in ["sol_contract", "sol_tort"]
    assert ny_timeframes[1].timeframe_id in ["sol_contract", "sol_tort"]


def test_date_normalization_format():
    """Test creating and using date normalization formats."""
    format = DateNormalizationFormat(
        name="ISO",
        regex_pattern=r'\d{4}-\d{2}-\d{2}',
        strptime_format="%Y-%m-%d",
        description="ISO date format (YYYY-MM-DD)"
    )
    
    assert format.name == "ISO"
    assert format.regex_pattern == r'\d{4}-\d{2}-\d{2}'
    assert format.strptime_format == "%Y-%m-%d"
    assert format.description == "ISO date format (YYYY-MM-DD)"