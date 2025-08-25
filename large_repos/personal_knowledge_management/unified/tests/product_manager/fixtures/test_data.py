"""
Test data fixtures for ProductMind tests.
"""
import datetime
import os
from uuid import uuid4
from collections import defaultdict

import pytest

from productmind.models import (
    Alternative,
    Competitor,
    CompetitiveFeature,
    Decision,
    Feature,
    Feedback,
    FeedbackCluster,
    MarketGap,
    Perspective,
    Priority,
    Sentiment,
    SourceType,
    Stakeholder,
    StakeholderRelationship,
    StakeholderType,
    StrategicGoal,
    Theme
)


@pytest.fixture
def temp_data_dir(tmpdir):
    """Create temporary data directory for tests."""
    data_dir = tmpdir.mkdir("test_data")
    feedback_dir = data_dir.mkdir("feedback")
    clusters_dir = data_dir.mkdir("clusters")
    themes_dir = data_dir.mkdir("themes")
    features_dir = data_dir.mkdir("features")
    strategic_goals_dir = data_dir.mkdir("strategic_goals")
    competitors_dir = data_dir.mkdir("competitors")
    competitive_features_dir = data_dir.mkdir("competitive_features")
    market_gaps_dir = data_dir.mkdir("market_gaps")
    decisions_dir = data_dir.mkdir("decisions")
    stakeholders_dir = data_dir.mkdir("stakeholders")
    perspectives_dir = data_dir.mkdir("perspectives")
    stakeholder_relationships_dir = data_dir.mkdir("stakeholder_relationships")
    
    yield str(data_dir)


@pytest.fixture
def feedback_samples():
    """Generate sample feedback items."""
    return [
        Feedback(
            id=uuid4(),
            content="I love the new dashboard layout. It's much easier to find what I need now.",
            source=SourceType.SURVEY,
            source_id="survey-123",
            customer_id="user-456",
            customer_segment="Enterprise",
            sentiment=Sentiment.POSITIVE,
            created_at=datetime.datetime.now() - datetime.timedelta(days=5),
            themes=["Dashboard", "UX", "Navigation"]
        ),
        Feedback(
            id=uuid4(),
            content="The export function is broken. I can't export my reports to PDF anymore.",
            source=SourceType.SUPPORT_TICKET,
            source_id="ticket-789",
            customer_id="user-101",
            customer_segment="Small Business",
            sentiment=Sentiment.NEGATIVE,
            created_at=datetime.datetime.now() - datetime.timedelta(days=3),
            themes=["Export", "PDF", "Reports"]
        ),
        Feedback(
            id=uuid4(),
            content="Would be great to have keyboard shortcuts for common actions.",
            source=SourceType.INTERVIEW,
            source_id="interview-202",
            customer_id="user-303",
            customer_segment="Enterprise",
            sentiment=Sentiment.NEUTRAL,
            created_at=datetime.datetime.now() - datetime.timedelta(days=7),
            themes=["Keyboard Shortcuts", "Productivity"]
        ),
        Feedback(
            id=uuid4(),
            content="The mobile version is frustrating to use. Buttons are too small and navigation is confusing.",
            source=SourceType.APP_REVIEW,
            source_id="review-404",
            customer_segment="Small Business",
            sentiment=Sentiment.NEGATIVE,
            created_at=datetime.datetime.now() - datetime.timedelta(days=10),
            themes=["Mobile", "UX", "Navigation"]
        ),
        Feedback(
            id=uuid4(),
            content="Love the new notification system! It helps me stay on top of important updates.",
            source=SourceType.SURVEY,
            source_id="survey-505",
            customer_id="user-606",
            customer_segment="Enterprise",
            sentiment=Sentiment.POSITIVE,
            created_at=datetime.datetime.now() - datetime.timedelta(days=2),
            themes=["Notifications", "Updates"]
        ),
        Feedback(
            id=uuid4(),
            content="The dashboard is cluttered and overwhelming. Too much information at once.",
            source=SourceType.INTERVIEW,
            source_id="interview-707",
            customer_id="user-808",
            customer_segment="Small Business",
            sentiment=Sentiment.NEGATIVE,
            created_at=datetime.datetime.now() - datetime.timedelta(days=6),
            themes=["Dashboard", "UX", "Information Overload"]
        ),
        Feedback(
            id=uuid4(),
            content="Would like better filtering options in the reports section.",
            source=SourceType.SURVEY,
            source_id="survey-909",
            customer_id="user-1010",
            customer_segment="Enterprise",
            sentiment=Sentiment.NEUTRAL,
            created_at=datetime.datetime.now() - datetime.timedelta(days=8),
            themes=["Reports", "Filtering"]
        ),
        Feedback(
            id=uuid4(),
            content="The export function worked great for me. I was able to export reports in multiple formats.",
            source=SourceType.SUPPORT_TICKET,
            source_id="ticket-1111",
            customer_id="user-1212",
            customer_segment="Enterprise",
            sentiment=Sentiment.POSITIVE,
            created_at=datetime.datetime.now() - datetime.timedelta(days=4),
            themes=["Export", "Reports", "Formats"]
        ),
        Feedback(
            id=uuid4(),
            content="Mobile app crashes whenever I try to open the reports section.",
            source=SourceType.APP_REVIEW,
            source_id="review-1313",
            sentiment=Sentiment.NEGATIVE,
            created_at=datetime.datetime.now() - datetime.timedelta(days=9),
            themes=["Mobile", "Reports", "Crashes"]
        ),
        Feedback(
            id=uuid4(),
            content="Keyboard shortcuts would make my workflow so much faster. Please add this!",
            source=SourceType.SURVEY,
            source_id="survey-1414",
            customer_id="user-1515",
            customer_segment="Small Business",
            sentiment=Sentiment.NEUTRAL,
            created_at=datetime.datetime.now() - datetime.timedelta(days=7),
            themes=["Keyboard Shortcuts", "Productivity"]
        )
    ]


@pytest.fixture
def theme_samples():
    """Generate sample themes."""
    return [
        Theme(
            id=uuid4(),
            name="Dashboard",
            description="Feedback related to the dashboard design and functionality",
            keywords=["layout", "organize", "metrics", "visualization"],
            frequency=15,
            impact_score=7.5,
            sentiment_distribution={
                Sentiment.POSITIVE: 8,
                Sentiment.NEUTRAL: 3,
                Sentiment.NEGATIVE: 4,
                Sentiment.MIXED: 0
            },
            feedback_ids=[str(uuid4()) for _ in range(15)]
        ),
        Theme(
            id=uuid4(),
            name="Mobile Experience",
            description="Feedback related to mobile app usability",
            keywords=["mobile", "app", "smartphone", "tablet", "responsive"],
            frequency=12,
            impact_score=8.2,
            sentiment_distribution={
                Sentiment.POSITIVE: 3,
                Sentiment.NEUTRAL: 2,
                Sentiment.NEGATIVE: 7,
                Sentiment.MIXED: 0
            },
            feedback_ids=[str(uuid4()) for _ in range(12)]
        ),
        Theme(
            id=uuid4(),
            name="Reports",
            description="Feedback related to reporting functionality",
            keywords=["export", "pdf", "csv", "data", "visualization"],
            frequency=18,
            impact_score=9.1,
            sentiment_distribution={
                Sentiment.POSITIVE: 6,
                Sentiment.NEUTRAL: 5,
                Sentiment.NEGATIVE: 6,
                Sentiment.MIXED: 1
            },
            feedback_ids=[str(uuid4()) for _ in range(18)]
        ),
        Theme(
            id=uuid4(),
            name="Keyboard Shortcuts",
            description="Feedback requesting keyboard shortcuts for common actions",
            keywords=["keyboard", "shortcuts", "productivity", "efficiency"],
            frequency=7,
            impact_score=6.4,
            sentiment_distribution={
                Sentiment.POSITIVE: 0,
                Sentiment.NEUTRAL: 7,
                Sentiment.NEGATIVE: 0,
                Sentiment.MIXED: 0
            },
            feedback_ids=[str(uuid4()) for _ in range(7)]
        ),
        Theme(
            id=uuid4(),
            name="Notifications",
            description="Feedback about notification system and alerts",
            keywords=["notifications", "alerts", "updates", "real-time"],
            frequency=10,
            impact_score=5.8,
            sentiment_distribution={
                Sentiment.POSITIVE: 6,
                Sentiment.NEUTRAL: 2,
                Sentiment.NEGATIVE: 2,
                Sentiment.MIXED: 0
            },
            feedback_ids=[str(uuid4()) for _ in range(10)]
        )
    ]


@pytest.fixture
def cluster_samples():
    """Generate sample feedback clusters."""
    return [
        FeedbackCluster(
            id=1,
            name="Dashboard Issues",
            description="Feedback related to dashboard problems",
            centroid=[0.1, 0.2, 0.3, 0.4],
            feedback_ids=[str(uuid4()) for _ in range(8)],
            themes=["Dashboard", "UX", "Information Overload"],
            sentiment_distribution={
                Sentiment.POSITIVE: 2,
                Sentiment.NEUTRAL: 1,
                Sentiment.NEGATIVE: 5,
                Sentiment.MIXED: 0
            }
        ),
        FeedbackCluster(
            id=2,
            name="Mobile App Problems",
            description="Issues with mobile application",
            centroid=[0.2, 0.3, 0.4, 0.5],
            feedback_ids=[str(uuid4()) for _ in range(10)],
            themes=["Mobile", "Crashes", "UX"],
            sentiment_distribution={
                Sentiment.POSITIVE: 1,
                Sentiment.NEUTRAL: 2,
                Sentiment.NEGATIVE: 7,
                Sentiment.MIXED: 0
            }
        ),
        FeedbackCluster(
            id=3,
            name="Report Functionality",
            description="Feedback about reports and exports",
            centroid=[0.3, 0.4, 0.5, 0.6],
            feedback_ids=[str(uuid4()) for _ in range(12)],
            themes=["Reports", "Export", "PDF", "Filtering"],
            sentiment_distribution={
                Sentiment.POSITIVE: 4,
                Sentiment.NEUTRAL: 3,
                Sentiment.NEGATIVE: 4,
                Sentiment.MIXED: 1
            }
        ),
        FeedbackCluster(
            id=4,
            name="Productivity Enhancements",
            description="Suggestions for productivity features",
            centroid=[0.4, 0.5, 0.6, 0.7],
            feedback_ids=[str(uuid4()) for _ in range(6)],
            themes=["Keyboard Shortcuts", "Productivity", "Efficiency"],
            sentiment_distribution={
                Sentiment.POSITIVE: 1,
                Sentiment.NEUTRAL: 5,
                Sentiment.NEGATIVE: 0,
                Sentiment.MIXED: 0
            }
        )
    ]


@pytest.fixture
def strategic_goal_samples():
    """Generate sample strategic goals."""
    return [
        StrategicGoal(
            id=uuid4(),
            name="Enterprise Market Growth",
            description="Increase market share in enterprise segment by 15% this year",
            priority=Priority.CRITICAL,
            metrics=["Enterprise revenue", "Enterprise customer count", "Enterprise retention rate"]
        ),
        StrategicGoal(
            id=uuid4(),
            name="Mobile Experience Enhancement",
            description="Improve mobile user experience to match desktop satisfaction scores",
            priority=Priority.HIGH,
            metrics=["Mobile app rating", "Mobile usage time", "Mobile conversion rate"]
        ),
        StrategicGoal(
            id=uuid4(),
            name="Reporting Capabilities Expansion",
            description="Expand reporting capabilities to meet competitive benchmarks",
            priority=Priority.HIGH,
            metrics=["Report export count", "Report types used", "Reporting satisfaction score"]
        ),
        StrategicGoal(
            id=uuid4(),
            name="User Efficiency Improvement",
            description="Improve user workflow efficiency to reduce time-to-value",
            priority=Priority.MEDIUM,
            metrics=["Time to complete common tasks", "Feature usage frequency", "User productivity score"]
        ),
        StrategicGoal(
            id=uuid4(),
            name="Small Business Segment Retention",
            description="Improve small business customer retention by 10%",
            priority=Priority.MEDIUM,
            metrics=["Small business churn rate", "Small business renewal rate", "Small business satisfaction score"]
        )
    ]


@pytest.fixture
def feature_samples(strategic_goal_samples):
    """Generate sample features with strategic goal alignment."""
    goals = strategic_goal_samples
    
    return [
        Feature(
            id=uuid4(),
            name="Dashboard Customization",
            description="Allow users to customize dashboard layout and metrics",
            status="proposed",
            priority=Priority.HIGH,
            effort_estimate=7.0,
            value_estimate=8.5,
            risk_level=4.0,
            dependencies=[],
            themes=["Dashboard", "UX", "Customization"],
            strategic_alignment={
                str(goals[0].id): 8.0,  # Enterprise Market Growth
                str(goals[3].id): 7.5,  # User Efficiency Improvement
                str(goals[4].id): 6.0   # Small Business Segment Retention
            },
            feedback_ids=[str(uuid4()) for _ in range(12)]
        ),
        Feature(
            id=uuid4(),
            name="Mobile App Redesign",
            description="Complete redesign of mobile app with responsive UI",
            status="proposed",
            priority=Priority.CRITICAL,
            effort_estimate=9.0,
            value_estimate=9.0,
            risk_level=6.0,
            dependencies=[],
            themes=["Mobile", "UX", "Design"],
            strategic_alignment={
                str(goals[0].id): 7.0,  # Enterprise Market Growth
                str(goals[1].id): 9.5,  # Mobile Experience Enhancement
                str(goals[4].id): 8.0   # Small Business Segment Retention
            },
            feedback_ids=[str(uuid4()) for _ in range(15)]
        ),
        Feature(
            id=uuid4(),
            name="Advanced Report Builder",
            description="Drag-and-drop report builder with advanced filtering",
            status="proposed",
            priority=Priority.HIGH,
            effort_estimate=8.0,
            value_estimate=8.0,
            risk_level=5.0,
            dependencies=[],
            themes=["Reports", "Filtering", "Customization"],
            strategic_alignment={
                str(goals[0].id): 9.0,  # Enterprise Market Growth
                str(goals[2].id): 9.0,  # Reporting Capabilities Expansion
                str(goals[3].id): 7.0   # User Efficiency Improvement
            },
            feedback_ids=[str(uuid4()) for _ in range(10)]
        ),
        Feature(
            id=uuid4(),
            name="Keyboard Shortcut System",
            description="Configurable keyboard shortcuts for all major actions",
            status="proposed",
            priority=Priority.MEDIUM,
            effort_estimate=4.0,
            value_estimate=6.0,
            risk_level=2.0,
            dependencies=[],
            themes=["Keyboard Shortcuts", "Productivity"],
            strategic_alignment={
                str(goals[0].id): 5.0,  # Enterprise Market Growth
                str(goals[3].id): 9.0,  # User Efficiency Improvement
                str(goals[4].id): 4.0   # Small Business Segment Retention
            },
            feedback_ids=[str(uuid4()) for _ in range(7)]
        ),
        Feature(
            id=uuid4(),
            name="PDF Export Enhancement",
            description="Improved PDF export with custom branding and formatting",
            status="proposed",
            priority=Priority.MEDIUM,
            effort_estimate=5.0,
            value_estimate=7.0,
            risk_level=3.0,
            dependencies=[],
            themes=["Reports", "Export", "PDF"],
            strategic_alignment={
                str(goals[0].id): 7.0,  # Enterprise Market Growth
                str(goals[2].id): 8.5,  # Reporting Capabilities Expansion
                str(goals[4].id): 6.0   # Small Business Segment Retention
            },
            feedback_ids=[str(uuid4()) for _ in range(8)]
        ),
        Feature(
            id=uuid4(),
            name="Smart Notifications",
            description="AI-powered notifications with user preference learning",
            status="proposed",
            priority=Priority.HIGH,
            effort_estimate=8.0,
            value_estimate=8.0,
            risk_level=7.0,
            dependencies=[],
            themes=["Notifications", "AI", "Personalization"],
            strategic_alignment={
                str(goals[0].id): 8.0,  # Enterprise Market Growth
                str(goals[1].id): 6.0,  # Mobile Experience Enhancement
                str(goals[3].id): 8.0   # User Efficiency Improvement
            },
            feedback_ids=[str(uuid4()) for _ in range(9)]
        )
    ]


@pytest.fixture
def competitor_samples():
    """Generate sample competitors."""
    return [
        Competitor(
            id=uuid4(),
            name="DataViz Pro",
            description="Enterprise analytics platform with advanced visualization",
            website="https://datavizpro.example.com",
            market_share=0.25,
            target_segments=["Enterprise", "Mid-Market"],
            strengths=["Data visualization", "Enterprise integration", "Customization"],
            weaknesses=["Mobile experience", "Price point", "Learning curve"],
            feature_comparison={
                "Advanced reporting": True,
                "Mobile app": True,
                "Custom dashboards": True,
                "AI-powered insights": True,
                "Keyboard shortcuts": False,
                "PDF export": True
            },
            price_points={
                "Basic": 20.0,
                "Professional": 50.0,
                "Enterprise": 100.0
            }
        ),
        Competitor(
            id=uuid4(),
            name="QuickInsight",
            description="User-friendly analytics for small businesses",
            website="https://quickinsight.example.com",
            market_share=0.15,
            target_segments=["Small Business", "Startups"],
            strengths=["Ease of use", "Affordable", "Quick setup"],
            weaknesses=["Limited advanced features", "Scalability", "Customization"],
            feature_comparison={
                "Advanced reporting": False,
                "Mobile app": True,
                "Custom dashboards": False,
                "AI-powered insights": False,
                "Keyboard shortcuts": True,
                "PDF export": True
            },
            price_points={
                "Basic": 10.0,
                "Professional": 25.0,
                "Business": 40.0
            }
        ),
        Competitor(
            id=uuid4(),
            name="EnterpriseMetrics",
            description="Full-featured analytics suite for large organizations",
            website="https://enterprisemetrics.example.com",
            market_share=0.30,
            target_segments=["Enterprise", "Government"],
            strengths=["Feature completeness", "Security", "Integration capabilities"],
            weaknesses=["User experience", "Implementation time", "Cost"],
            feature_comparison={
                "Advanced reporting": True,
                "Mobile app": True,
                "Custom dashboards": True,
                "AI-powered insights": True,
                "Keyboard shortcuts": True,
                "PDF export": True
            },
            price_points={
                "Professional": 80.0,
                "Enterprise": 150.0,
                "Government": 120.0
            }
        ),
        Competitor(
            id=uuid4(),
            name="MobileFirst",
            description="Mobile-focused analytics platform",
            website="https://mobilefirst.example.com",
            market_share=0.10,
            target_segments=["Small Business", "Mid-Market"],
            strengths=["Mobile experience", "Real-time data", "Notifications"],
            weaknesses=["Desktop experience", "Advanced reporting", "Data integration"],
            feature_comparison={
                "Advanced reporting": False,
                "Mobile app": True,
                "Custom dashboards": True,
                "AI-powered insights": True,
                "Keyboard shortcuts": False,
                "PDF export": False
            },
            price_points={
                "Basic": 15.0,
                "Premium": 35.0,
                "Business": 60.0
            }
        )
    ]


@pytest.fixture
def competitive_feature_samples(competitor_samples):
    """Generate sample competitive features."""
    competitors = competitor_samples
    
    return [
        CompetitiveFeature(
            id=uuid4(),
            name="Advanced reporting",
            description="Advanced reporting capabilities with custom metrics",
            category="Reporting",
            importance=9.0,
            our_implementation="Basic report builder with limited customization",
            our_rating=6.5,
            competitor_implementations={
                str(competitors[0].id): "Comprehensive report builder with custom formulas",
                str(competitors[1].id): "Basic reporting with templates",
                str(competitors[2].id): "Enterprise reporting suite with advanced analytics",
                str(competitors[3].id): "Simple mobile-optimized reports"
            },
            competitor_ratings={
                str(competitors[0].id): 8.5,
                str(competitors[1].id): 5.0,
                str(competitors[2].id): 9.0,
                str(competitors[3].id): 4.0
            }
        ),
        CompetitiveFeature(
            id=uuid4(),
            name="Mobile app",
            description="Mobile application for on-the-go analytics",
            category="Mobile",
            importance=8.0,
            our_implementation="Basic mobile app with limited functionality",
            our_rating=5.0,
            competitor_implementations={
                str(competitors[0].id): "Comprehensive mobile app with most desktop features",
                str(competitors[1].id): "Simple but effective mobile app",
                str(competitors[2].id): "Full-featured but complex mobile app",
                str(competitors[3].id): "Outstanding mobile-first experience"
            },
            competitor_ratings={
                str(competitors[0].id): 7.0,
                str(competitors[1].id): 6.5,
                str(competitors[2].id): 6.0,
                str(competitors[3].id): 9.5
            }
        ),
        CompetitiveFeature(
            id=uuid4(),
            name="Custom dashboards",
            description="User-customizable dashboards with widgets",
            category="Dashboard",
            importance=8.5,
            our_implementation="Limited dashboard customization options",
            our_rating=6.0,
            competitor_implementations={
                str(competitors[0].id): "Highly customizable dashboards with advanced widgets",
                str(competitors[1].id): "Simple dashboard customization",
                str(competitors[2].id): "Enterprise dashboard system with sharing",
                str(competitors[3].id): "Mobile-optimized custom dashboards"
            },
            competitor_ratings={
                str(competitors[0].id): 9.0,
                str(competitors[1].id): 5.5,
                str(competitors[2].id): 8.5,
                str(competitors[3].id): 7.0
            }
        ),
        CompetitiveFeature(
            id=uuid4(),
            name="AI-powered insights",
            description="Machine learning insights and recommendations",
            category="AI",
            importance=7.5,
            our_implementation=None,
            our_rating=None,
            competitor_implementations={
                str(competitors[0].id): "Advanced AI analytics with pattern recognition",
                str(competitors[1].id): None,
                str(competitors[2].id): "Enterprise AI with predictive analytics",
                str(competitors[3].id): "Mobile-focused AI notifications"
            },
            competitor_ratings={
                str(competitors[0].id): 8.0,
                str(competitors[1].id): None,
                str(competitors[2].id): 9.0,
                str(competitors[3].id): 7.0
            }
        ),
        CompetitiveFeature(
            id=uuid4(),
            name="Keyboard shortcuts",
            description="Keyboard shortcuts for power users",
            category="Productivity",
            importance=6.0,
            our_implementation=None,
            our_rating=None,
            competitor_implementations={
                str(competitors[0].id): None,
                str(competitors[1].id): "Basic keyboard shortcuts",
                str(competitors[2].id): "Comprehensive keyboard shortcut system",
                str(competitors[3].id): None
            },
            competitor_ratings={
                str(competitors[0].id): None,
                str(competitors[1].id): 7.0,
                str(competitors[2].id): 8.5,
                str(competitors[3].id): None
            }
        ),
        CompetitiveFeature(
            id=uuid4(),
            name="PDF export",
            description="Export reports and dashboards to PDF",
            category="Export",
            importance=7.0,
            our_implementation="Basic PDF export without formatting options",
            our_rating=5.5,
            competitor_implementations={
                str(competitors[0].id): "Advanced PDF export with branding",
                str(competitors[1].id): "Simple PDF export",
                str(competitors[2].id): "Enterprise PDF reporting with scheduling",
                str(competitors[3].id): None
            },
            competitor_ratings={
                str(competitors[0].id): 8.0,
                str(competitors[1].id): 6.0,
                str(competitors[2].id): 9.0,
                str(competitors[3].id): None
            }
        )
    ]


@pytest.fixture
def market_gap_samples(competitor_samples):
    """Generate sample market gaps."""
    competitors = competitor_samples
    
    return [
        MarketGap(
            id=uuid4(),
            name="AI-powered insights for small businesses",
            description="Simplified AI insights accessible to smaller organizations",
            size_estimate=0.15,
            opportunity_score=8.5,
            related_feedback=[str(uuid4()) for _ in range(5)],
            competing_solutions=[str(competitors[0].id), str(competitors[2].id), str(competitors[3].id)]
        ),
        MarketGap(
            id=uuid4(),
            name="Mobile reporting with offline capabilities",
            description="Reports accessible offline on mobile devices",
            size_estimate=0.20,
            opportunity_score=7.8,
            related_feedback=[str(uuid4()) for _ in range(7)],
            competing_solutions=[str(competitors[3].id)]
        ),
        MarketGap(
            id=uuid4(),
            name="User-friendly keyboard shortcuts",
            description="Intuitive keyboard shortcuts with visual guides",
            size_estimate=0.10,
            opportunity_score=6.5,
            related_feedback=[str(uuid4()) for _ in range(6)],
            competing_solutions=[str(competitors[1].id), str(competitors[2].id)]
        )
    ]


@pytest.fixture
def decision_samples():
    """Generate sample decisions with alternatives."""
    alt1_id = uuid4()
    alt2_id = uuid4()
    alt3_id = uuid4()
    
    return [
        Decision(
            id=uuid4(),
            title="Mobile App Platform Selection",
            description="Decision on which technology stack to use for mobile app rebuild",
            context="Our current mobile app has poor reviews and limited functionality. We need to rebuild it with modern technology.",
            problem_statement="Select the best technology platform for rebuilding our mobile app to improve user experience and maintainability.",
            decision_date=datetime.datetime.now() - datetime.timedelta(days=60),
            decision_maker="Sarah Chen, VP of Product",
            chosen_alternative=str(alt2_id),
            alternatives=[
                Alternative(
                    id=uuid4(),
                    name="Native Development",
                    description="Develop separate iOS and Android apps with Swift and Kotlin",
                    pros=["Best performance", "Full access to device features", "Best UX"],
                    cons=["Higher development cost", "Duplicate effort", "Separate codebases to maintain"],
                    estimated_cost=120000,
                    estimated_benefit=90000,
                    estimated_risk=0.3,
                    score=7.5
                ),
                Alternative(
                    id=alt2_id,
                    name="React Native",
                    description="Cross-platform development with React Native",
                    pros=["Single codebase", "Faster development", "Good performance", "Large community"],
                    cons=["Occasional native bridge issues", "Some platform-specific code still needed"],
                    estimated_cost=80000,
                    estimated_benefit=85000,
                    estimated_risk=0.4,
                    score=8.2
                ),
                Alternative(
                    id=uuid4(),
                    name="Progressive Web App",
                    description="Web-based app with offline capabilities",
                    pros=["Lowest development cost", "No app store approvals", "Single codebase"],
                    cons=["Limited device features", "Lower performance", "Less integrated experience"],
                    estimated_cost=50000,
                    estimated_benefit=60000,
                    estimated_risk=0.5,
                    score=6.8
                )
            ],
            rationale="React Native provides the best balance of development efficiency, performance, and user experience. While native development would provide slightly better performance, the cost and maintenance benefits of a single codebase are substantial. The team also has stronger React skills.",
            success_criteria=[
                "Mobile app store rating improves to 4.5+",
                "Development completed within 4 months",
                "90% feature parity with desktop version",
                "Crash rate below 0.5%"
            ],
            related_decisions=[],
            related_feedback=[str(uuid4()) for _ in range(10)],
            related_features=[str(uuid4()) for _ in range(2)],
            status="decided",
            outcome_assessment="Implementation was successful. App store rating improved to 4.7 within 3 months of launch. Development was completed in 4.5 months, slightly over schedule but within acceptable range."
        ),
        Decision(
            id=uuid4(),
            title="Dashboard Redesign Approach",
            description="Decision on approach for redesigning the main dashboard",
            context="User feedback indicates the dashboard is cluttered and difficult to navigate. We need to improve the user experience.",
            problem_statement="Determine the best approach to redesign the dashboard to improve user satisfaction and productivity.",
            decision_date=datetime.datetime.now() - datetime.timedelta(days=45),
            decision_maker="Marcus Johnson, Product Manager",
            chosen_alternative=str(alt3_id),
            alternatives=[
                Alternative(
                    id=uuid4(),
                    name="Incremental Improvements",
                    description="Make targeted improvements to existing dashboard",
                    pros=["Lower risk", "Quicker implementation", "Less user adjustment"],
                    cons=["Limited improvement potential", "Constrained by current design"],
                    estimated_cost=40000,
                    estimated_benefit=50000,
                    estimated_risk=0.2,
                    score=6.5
                ),
                Alternative(
                    id=uuid4(),
                    name="Template-Based Redesign",
                    description="Offer several pre-designed templates for users to choose from",
                    pros=["Balance of customization and guidance", "Moderate development effort"],
                    cons=["May not satisfy all use cases", "Increased complexity"],
                    estimated_cost=65000,
                    estimated_benefit=75000,
                    estimated_risk=0.3,
                    score=7.3
                ),
                Alternative(
                    id=alt3_id,
                    name="Full Customization",
                    description="Fully customizable drag-and-drop dashboard builder",
                    pros=["Maximum flexibility", "Competitive advantage", "Addresses diverse needs"],
                    cons=["Highest development cost", "Complexity for new users", "Longer timeline"],
                    estimated_cost=90000,
                    estimated_benefit=110000,
                    estimated_risk=0.4,
                    score=8.1
                )
            ],
            rationale="While the fully customizable approach has higher initial cost and risk, it provides the greatest long-term value and competitive advantage. User research showed strong preference for customization, and this approach aligns with our strategic goal of improving user efficiency.",
            success_criteria=[
                "User satisfaction with dashboard increases by 30%",
                "Time to find key information decreases by 25%",
                "90% of users customize their dashboard within first month"
            ],
            related_decisions=[],
            related_feedback=[str(uuid4()) for _ in range(8)],
            related_features=[str(uuid4()) for _ in range(1)],
            status="decided"
        )
    ]


@pytest.fixture
def stakeholder_samples():
    """Generate sample stakeholders."""
    return [
        Stakeholder(
            id=uuid4(),
            name="Michael Rodriguez",
            title="Chief Technology Officer",
            department="Engineering",
            type=StakeholderType.EXECUTIVE,
            influence_level=0.9,
            perspectives=[],
            interests=["Architecture", "Technology strategy", "Performance", "Security"]
        ),
        Stakeholder(
            id=uuid4(),
            name="Sarah Chen",
            title="VP of Product",
            department="Product",
            type=StakeholderType.PRODUCT,
            influence_level=0.8,
            perspectives=[],
            interests=["User experience", "Feature prioritization", "Market trends", "Competitive strategy"]
        ),
        Stakeholder(
            id=uuid4(),
            name="Marcus Johnson",
            title="Product Manager",
            department="Product",
            type=StakeholderType.PRODUCT,
            influence_level=0.6,
            perspectives=[],
            interests=["Dashboard design", "Reporting features", "User workflows"]
        ),
        Stakeholder(
            id=uuid4(),
            name="Priya Patel",
            title="Engineering Manager",
            department="Engineering",
            type=StakeholderType.ENGINEERING,
            influence_level=0.7,
            perspectives=[],
            interests=["Technical feasibility", "Development timeline", "Code quality", "Architecture"]
        ),
        Stakeholder(
            id=uuid4(),
            name="Jason Kim",
            title="UX Designer",
            department="Design",
            type=StakeholderType.DESIGN,
            influence_level=0.5,
            perspectives=[],
            interests=["User experience", "Interface design", "Accessibility", "Mobile design"]
        ),
        Stakeholder(
            id=uuid4(),
            name="Lisa Washington",
            title="Director of Sales",
            department="Sales",
            type=StakeholderType.SALES,
            influence_level=0.7,
            perspectives=[],
            interests=["Customer acquisition", "Competitive features", "Sales enablement"]
        ),
        Stakeholder(
            id=uuid4(),
            name="Carlos Mendez",
            title="Customer Success Manager",
            department="Customer Success",
            type=StakeholderType.CUSTOMER_SUCCESS,
            influence_level=0.6,
            perspectives=[],
            interests=["Onboarding", "Customer training", "Feature adoption", "User satisfaction"]
        ),
        Stakeholder(
            id=uuid4(),
            name="Emma Thompson",
            title="Marketing Director",
            department="Marketing",
            type=StakeholderType.MARKETING,
            influence_level=0.7,
            perspectives=[],
            interests=["Market positioning", "Feature messaging", "Competitive differentiation"]
        )
    ]


@pytest.fixture
def perspective_samples(stakeholder_samples):
    """Generate sample perspectives from stakeholders."""
    stakeholders = stakeholder_samples
    
    # Update stakeholder perspectives with returned perspective IDs
    perspectives = [
        Perspective(
            id=uuid4(),
            topic="Mobile App Redesign",
            content="We should prioritize performance and native feel in the mobile redesign.",
            priority=Priority.HIGH,
            influence_level=0.8,
            agreement_level=0.7,
            stakeholder_id=stakeholders[0].id  # CTO
        ),
        Perspective(
            id=uuid4(),
            topic="Mobile App Redesign",
            content="Cross-platform development will give us the best time-to-market advantages.",
            priority=Priority.CRITICAL,
            influence_level=0.9,
            agreement_level=0.9,
            stakeholder_id=stakeholders[1].id  # VP of Product
        ),
        Perspective(
            id=uuid4(),
            topic="Mobile App Redesign",
            content="User experience must be the top priority regardless of implementation approach.",
            priority=Priority.HIGH,
            influence_level=0.7,
            agreement_level=0.8,
            stakeholder_id=stakeholders[4].id  # UX Designer
        ),
        Perspective(
            id=uuid4(),
            topic="Dashboard Customization",
            content="Full customization will require significant engineering resources and may delay other priorities.",
            priority=Priority.MEDIUM,
            influence_level=0.8,
            agreement_level=0.4,
            stakeholder_id=stakeholders[3].id  # Engineering Manager
        ),
        Perspective(
            id=uuid4(),
            topic="Dashboard Customization",
            content="Customization is a top request from enterprise customers and will help close deals.",
            priority=Priority.HIGH,
            influence_level=0.7,
            agreement_level=0.9,
            stakeholder_id=stakeholders[5].id  # Director of Sales
        ),
        Perspective(
            id=uuid4(),
            topic="Dashboard Customization",
            content="We should focus on creating smart defaults rather than overwhelming users with options.",
            priority=Priority.MEDIUM,
            influence_level=0.6,
            agreement_level=0.5,
            stakeholder_id=stakeholders[6].id  # Customer Success Manager
        ),
        Perspective(
            id=uuid4(),
            topic="Reporting Capabilities",
            content="Advanced reporting capabilities are essential for enterprise customers and competitive parity.",
            priority=Priority.HIGH,
            influence_level=0.8,
            agreement_level=0.8,
            stakeholder_id=stakeholders[1].id  # VP of Product
        ),
        Perspective(
            id=uuid4(),
            topic="Reporting Capabilities",
            content="Report builder should prioritize template-based approaches for ease of use.",
            priority=Priority.MEDIUM,
            influence_level=0.6,
            agreement_level=0.7,
            stakeholder_id=stakeholders[2].id  # Product Manager
        ),
        Perspective(
            id=uuid4(),
            topic="Reporting Capabilities",
            content="Export formats and scheduling should be the focus for initial reporting improvements.",
            priority=Priority.MEDIUM,
            influence_level=0.7,
            agreement_level=0.6,
            stakeholder_id=stakeholders[6].id  # Customer Success Manager
        )
    ]
    
    # Update stakeholders with perspective IDs
    stakeholder_perspectives = defaultdict(list)
    for perspective in perspectives:
        sid = str(perspective.stakeholder_id)
        stakeholder_perspectives[sid].append(perspective.id)

    for stakeholder in stakeholders:
        sid = str(stakeholder.id)
        if sid in stakeholder_perspectives:
            stakeholder.perspectives = stakeholder_perspectives[sid]
    
    return perspectives


@pytest.fixture
def stakeholder_relationship_samples(stakeholder_samples):
    """Generate sample stakeholder relationships."""
    stakeholders = stakeholder_samples
    
    return [
        StakeholderRelationship(
            id=uuid4(),
            stakeholder1_id=stakeholders[0].id,  # CTO
            stakeholder2_id=stakeholders[1].id,  # VP of Product
            relationship_type="Peer",
            alignment_level=0.7,
            notes="Good working relationship with some disagreements on technical priorities"
        ),
        StakeholderRelationship(
            id=uuid4(),
            stakeholder1_id=stakeholders[1].id,  # VP of Product
            stakeholder2_id=stakeholders[2].id,  # Product Manager
            relationship_type="Manager-Report",
            alignment_level=0.9,
            notes="Strong alignment on product direction"
        ),
        StakeholderRelationship(
            id=uuid4(),
            stakeholder1_id=stakeholders[0].id,  # CTO
            stakeholder2_id=stakeholders[3].id,  # Engineering Manager
            relationship_type="Manager-Report",
            alignment_level=0.8,
            notes="Well-aligned on technical direction"
        ),
        StakeholderRelationship(
            id=uuid4(),
            stakeholder1_id=stakeholders[2].id,  # Product Manager
            stakeholder2_id=stakeholders[4].id,  # UX Designer
            relationship_type="Cross-functional",
            alignment_level=0.7,
            notes="Generally aligned but some tension on design priorities"
        ),
        StakeholderRelationship(
            id=uuid4(),
            stakeholder1_id=stakeholders[1].id,  # VP of Product
            stakeholder2_id=stakeholders[5].id,  # Director of Sales
            relationship_type="Cross-functional",
            alignment_level=0.6,
            notes="Some disagreement on feature priorities vs. sales needs"
        ),
        StakeholderRelationship(
            id=uuid4(),
            stakeholder1_id=stakeholders[2].id,  # Product Manager
            stakeholder2_id=stakeholders[6].id,  # Customer Success Manager
            relationship_type="Cross-functional",
            alignment_level=0.8,
            notes="Strong collaboration on customer needs"
        ),
        StakeholderRelationship(
            id=uuid4(),
            stakeholder1_id=stakeholders[5].id,  # Director of Sales
            stakeholder2_id=stakeholders[7].id,  # Marketing Director
            relationship_type="Peer",
            alignment_level=0.9,
            notes="Very strong alignment on go-to-market strategy"
        )
    ]