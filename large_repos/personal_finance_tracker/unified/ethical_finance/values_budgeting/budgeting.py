"""Values-aligned budgeting for tracking personal expenses against ethical values."""

from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import date, datetime, timedelta
import time
from dataclasses import dataclass
import pandas as pd
import numpy as np

from ethical_finance.models import Transaction


@dataclass
class ValueCategory:
    """Definition of a values-based category for expenses."""
    
    id: str
    name: str
    description: str
    tags: List[str]
    alignment: str  # "aligned", "neutral", or "misaligned"
    impact_level: int  # 1-5, with 5 being highest impact
    alternatives: List[str]  # IDs of alternative categories


@dataclass
class ValueAlignment:
    """Alignment of a transaction with personal values."""
    
    transaction_id: str
    value_categories: List[str]
    alignment_score: float  # -1.0 to 1.0
    impact_level: int  # 1-5
    reasons: List[str]
    alternatives: List[Dict[str, Any]]


@dataclass
class SpendingAnalysisResult:
    """Result of analyzing spending patterns against values."""
    
    analysis_date: date
    period_start: date
    period_end: date
    total_spending: float
    spending_by_category: Dict[str, float]
    spending_by_alignment: Dict[str, float]
    high_impact_areas: List[Dict[str, Any]]
    improvement_opportunities: List[Dict[str, Any]]
    aligned_percentage: float
    consistency_score: float  # 0-100
    processing_time_ms: float = 0


class ValuesAlignedBudgeting:
    """System for categorizing and analyzing expenses according to ethical values."""
    
    def __init__(self, value_categories: List[ValueCategory]):
        """Initialize with a list of value categories.
        
        Args:
            value_categories: List of ValueCategory objects defining the values framework
        """
        self.categories = {cat.id: cat for cat in value_categories}
        
        # Build tag index for faster categorization
        self.tag_index = {}
        for cat_id, category in self.categories.items():
            for tag in category.tags:
                if tag not in self.tag_index:
                    self.tag_index[tag] = []
                self.tag_index[tag].append(cat_id)
    
    def categorize_transaction(self, transaction: Transaction) -> ValueAlignment:
        """Categorize a single transaction according to value alignment.
        
        Args:
            transaction: The transaction to categorize
            
        Returns:
            ValueAlignment object with categorization results
        """
        # Start with empty results
        value_categories = []
        reasons = []
        
        # Check for tag matches
        matched_tags = set()
        for tag in transaction.tags:
            tag_lower = tag.lower()
            if tag_lower in self.tag_index:
                matched_tags.add(tag_lower)
                value_categories.extend(self.tag_index[tag_lower])
        
        # Remove duplicates
        value_categories = list(set(value_categories))
        
        # If no categories matched, use the transaction category to guess
        if not value_categories:
            value_categories = self._suggest_categories_from_transaction(transaction)
            reasons.append(f"Categorized based on transaction description and category")
        else:
            reasons.append(f"Matched tags: {', '.join(matched_tags)}")
        
        # Calculate alignment score (average of matched categories)
        alignment_score = 0.0
        impact_level = 0
        
        if value_categories:
            alignment_values = []
            impact_values = []
            
            for cat_id in value_categories:
                category = self.categories[cat_id]
                
                # Convert alignment string to value
                if category.alignment == "aligned":
                    alignment_values.append(1.0)
                elif category.alignment == "neutral":
                    alignment_values.append(0.0)
                else:  # misaligned
                    alignment_values.append(-1.0)
                
                impact_values.append(category.impact_level)
            
            # Take average of alignment and maximum impact
            alignment_score = sum(alignment_values) / len(alignment_values)
            impact_level = max(impact_values)
        
        # Generate alternative suggestions for misaligned transactions
        alternatives = []
        if alignment_score < 0:
            # Get alternatives from the categories
            alternative_ids = set()
            for cat_id in value_categories:
                if cat_id in self.categories:
                    alternative_ids.update(self.categories[cat_id].alternatives)
            
            # Add alternative details
            for alt_id in alternative_ids:
                if alt_id in self.categories:
                    alt_category = self.categories[alt_id]
                    alternatives.append({
                        "category_id": alt_id,
                        "name": alt_category.name,
                        "description": alt_category.description
                    })
        
        return ValueAlignment(
            transaction_id=transaction.id,
            value_categories=value_categories,
            alignment_score=alignment_score,
            impact_level=impact_level,
            reasons=reasons,
            alternatives=alternatives
        )
    
    def batch_categorize_transactions(self, transactions: List[Transaction]) -> Dict[str, ValueAlignment]:
        """Categorize multiple transactions in batch.
        
        Args:
            transactions: List of transactions to categorize
            
        Returns:
            Dict mapping transaction IDs to their ValueAlignment results
        """
        start_time = time.time()
        results = {}
        
        for transaction in transactions:
            results[transaction.id] = self.categorize_transaction(transaction)
        
        total_time = time.time() - start_time
        print(f"Categorized {len(transactions)} transactions in {total_time:.2f} seconds")
        
        return results
    
    def analyze_spending_patterns(
        self,
        transactions: List[Transaction],
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> SpendingAnalysisResult:
        """Analyze spending patterns against value alignment.
        
        Args:
            transactions: List of transactions to analyze
            start_date: Optional start date to filter transactions
            end_date: Optional end date to filter transactions
            
        Returns:
            SpendingAnalysisResult with the analysis findings
        """
        start_time = time.time()
        
        # Filter transactions by date if specified
        filtered_transactions = transactions
        if start_date or end_date:
            filtered_transactions = []
            for tx in transactions:
                if start_date and tx.date < start_date:
                    continue
                if end_date and tx.date > end_date:
                    continue
                filtered_transactions.append(tx)
        
        # Use actual date range from transactions if not specified
        if not start_date or not end_date:
            dates = [tx.date for tx in filtered_transactions]
            actual_start = min(dates) if dates else date.today()
            actual_end = max(dates) if dates else date.today()
            
            if not start_date:
                start_date = actual_start
            if not end_date:
                end_date = actual_end
        
        # Calculate total spending
        total_spending = sum(tx.amount for tx in filtered_transactions)
        
        # Categorize all transactions
        categorized = self.batch_categorize_transactions(filtered_transactions)
        
        # Aggregate spending by category
        category_spending = {}
        for tx in filtered_transactions:
            tx_id = tx.id
            if tx_id in categorized:
                alignment = categorized[tx_id]
                for cat_id in alignment.value_categories:
                    if cat_id in category_spending:
                        category_spending[cat_id] += tx.amount
                    else:
                        category_spending[cat_id] = tx.amount
        
        # Aggregate spending by alignment
        alignment_spending = {
            "aligned": 0.0,
            "neutral": 0.0,
            "misaligned": 0.0,
            "uncategorized": 0.0
        }
        
        for tx in filtered_transactions:
            tx_id = tx.id
            
            if tx_id in categorized:
                alignment = categorized[tx_id]
                
                if not alignment.value_categories:
                    alignment_spending["uncategorized"] += tx.amount
                elif alignment.alignment_score > 0.3:
                    alignment_spending["aligned"] += tx.amount
                elif alignment.alignment_score < -0.3:
                    alignment_spending["misaligned"] += tx.amount
                else:
                    alignment_spending["neutral"] += tx.amount
            else:
                alignment_spending["uncategorized"] += tx.amount
        
        # Calculate aligned percentage
        aligned_percentage = 0.0
        if total_spending > 0:
            aligned_percentage = alignment_spending["aligned"] / total_spending
        
        # Identify high impact areas (largest spending in misaligned categories)
        high_impact_misaligned = []
        for cat_id, amount in sorted(category_spending.items(), key=lambda x: x[1], reverse=True):
            if cat_id in self.categories and self.categories[cat_id].alignment == "misaligned":
                high_impact_misaligned.append({
                    "category_id": cat_id,
                    "name": self.categories[cat_id].name,
                    "amount": amount,
                    "percentage": amount / total_spending if total_spending > 0 else 0,
                    "impact_level": self.categories[cat_id].impact_level
                })
        
        # Sort by impact level and then amount
        high_impact_misaligned.sort(key=lambda x: (x["impact_level"], x["amount"]), reverse=True)
        
        # Identify improvement opportunities
        improvement_opportunities = []
        
        # First, add high-impact misaligned categories
        for high_impact in high_impact_misaligned[:3]:  # Top 3
            category = self.categories[high_impact["category_id"]]
            alternatives = [self.categories[alt_id] for alt_id in category.alternatives 
                           if alt_id in self.categories]
            
            improvement_opportunities.append({
                "type": "reduce_misaligned",
                "category_id": high_impact["category_id"],
                "category_name": category.name,
                "amount": high_impact["amount"],
                "alternatives": [{"id": alt.id, "name": alt.name} for alt in alternatives],
                "priority": "high" if high_impact["impact_level"] >= 4 else "medium"
            })
        
        # Then, identify underrepresented aligned categories
        aligned_categories = [cat for cat_id, cat in self.categories.items() 
                             if cat.alignment == "aligned"]
        for category in aligned_categories:
            cat_amount = category_spending.get(category.id, 0)
            cat_percentage = cat_amount / total_spending if total_spending > 0 else 0
            
            # If spending in this aligned category is very low
            if cat_percentage < 0.05:
                improvement_opportunities.append({
                    "type": "increase_aligned",
                    "category_id": category.id,
                    "category_name": category.name,
                    "current_amount": cat_amount,
                    "suggested_actions": [
                        f"Allocate more to {category.name} activities",
                        f"Explore new {category.name} opportunities"
                    ],
                    "priority": "medium"
                })
        
        # Calculate consistency score (0-100)
        # Higher when spending aligns with values
        consistency_score = 0.0
        if total_spending > 0:
            aligned_weight = 1.0
            neutral_weight = 0.5
            misaligned_weight = 0.0
            uncategorized_weight = 0.25
            
            weighted_sum = (
                alignment_spending["aligned"] * aligned_weight +
                alignment_spending["neutral"] * neutral_weight +
                alignment_spending["misaligned"] * misaligned_weight +
                alignment_spending["uncategorized"] * uncategorized_weight
            )
            
            consistency_score = (weighted_sum / total_spending) * 100
        
        # Calculate processing time
        processing_time = (time.time() - start_time) * 1000
        
        return SpendingAnalysisResult(
            analysis_date=date.today(),
            period_start=start_date,
            period_end=end_date,
            total_spending=total_spending,
            spending_by_category=category_spending,
            spending_by_alignment=alignment_spending,
            high_impact_areas=high_impact_misaligned[:5],  # Top 5
            improvement_opportunities=improvement_opportunities[:5],  # Top 5
            aligned_percentage=aligned_percentage,
            consistency_score=consistency_score,
            processing_time_ms=processing_time
        )
    
    def suggest_alternative_vendors(
        self, 
        vendor: str,
        category: str,
        location: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Suggest alternative vendors that better align with ethical values.
        
        Args:
            vendor: The current vendor
            category: The transaction category
            location: Optional location context
            
        Returns:
            List of suggested alternative vendors
        """
        # This is a simplified implementation - in a real system, this would
        # connect to a database of ethical vendors or an API
        
        # Sample alternatives database (would be much more comprehensive in reality)
        alt_db = {
            "Groceries": [
                {"name": "Local Farmers Market", "alignment": "aligned", "impact": 5, 
                 "description": "Direct support for local farmers with sustainable practices"},
                {"name": "Community Co-op", "alignment": "aligned", "impact": 4,
                 "description": "Member-owned grocery focused on local and organic products"},
                {"name": "Whole Foods", "alignment": "neutral", "impact": 3,
                 "description": "Natural food chain with some sustainable practices"}
            ],
            "Coffee": [
                {"name": "Fair Trade Cafe", "alignment": "aligned", "impact": 5,
                 "description": "Independent cafe using fair trade, shade-grown coffee"},
                {"name": "Local Roastery", "alignment": "aligned", "impact": 4,
                 "description": "Locally owned business with ethical sourcing practices"}
            ],
            "Gas": [
                {"name": "Public Transit", "alignment": "aligned", "impact": 5,
                 "description": "Reduce carbon footprint by using public transportation"},
                {"name": "Electric Charging Station", "alignment": "aligned", "impact": 4,
                 "description": "Switch to electric vehicle and renewable energy"}
            ],
            "Clothing": [
                {"name": "Ethical Fashion Boutique", "alignment": "aligned", "impact": 5,
                 "description": "Sustainable clothing with transparent supply chain"},
                {"name": "Second-hand Store", "alignment": "aligned", "impact": 5,
                 "description": "Reduce waste by purchasing pre-owned clothing"},
                {"name": "Fair Trade Clothing", "alignment": "aligned", "impact": 4,
                 "description": "Clothing made with fair labor practices and sustainable materials"}
            ]
        }
        
        # Check if we have alternatives for this category
        if category in alt_db:
            # If a specific vendor was provided, filter out that vendor
            return [alt for alt in alt_db[category] if alt["name"].lower() != vendor.lower()]
        
        return []
    
    def _suggest_categories_from_transaction(self, transaction: Transaction) -> List[str]:
        """Suggest value categories based on transaction details.
        
        Args:
            transaction: The transaction to analyze
            
        Returns:
            List of suggested category IDs
        """
        matched_categories = set()
        
        # Check transaction category against value categories
        tx_category = transaction.category.lower()
        tx_vendor = transaction.vendor.lower()
        tx_description = transaction.description.lower() if transaction.description else ""
        
        # List of words to check in transaction details
        check_words = set()
        
        # Add words from transaction category, vendor, and description
        check_words.update(tx_category.split())
        check_words.update(tx_vendor.split())
        if tx_description:
            check_words.update(tx_description.split())
        
        # Remove common words that aren't useful for matching
        common_words = {"and", "the", "for", "with", "in", "at", "on", "by", "of", "to", "a"}
        check_words = check_words - common_words
        
        # Check each category for matches
        for cat_id, category in self.categories.items():
            # Check if category keywords match transaction details
            keyword_matches = False
            for tag in category.tags:
                tag_words = set(tag.lower().split())
                if not tag_words.isdisjoint(check_words):
                    keyword_matches = True
                    break
            
            # If keywords match, add this category
            if keyword_matches:
                matched_categories.add(cat_id)
        
        # Special case handling for common transaction types
        # Groceries
        if tx_category == "groceries":
            if any(vendor in tx_vendor for vendor in ["whole foods", "organic", "farmer", "local", "co-op"]):
                matched_categories.update(self._find_categories_by_alignment("aligned"))
            elif any(vendor in tx_vendor for vendor in ["supermarket", "market", "grocery"]):
                matched_categories.update(self._find_categories_by_alignment("neutral"))
        
        # Transportation
        if tx_category == "transportation":
            if any(word in tx_vendor + " " + tx_description for word in ["gas", "fuel", "diesel"]):
                matched_categories.update(self._find_categories_by_alignment("misaligned"))
            elif any(word in tx_vendor + " " + tx_description for word in ["transit", "bus", "train", "subway", "electric"]):
                matched_categories.update(self._find_categories_by_alignment("aligned"))
        
        # Return list of unique category IDs
        return list(matched_categories)
    
    def _find_categories_by_alignment(self, alignment: str) -> Set[str]:
        """Find categories with the specified alignment.
        
        Args:
            alignment: The alignment to search for
            
        Returns:
            Set of category IDs with the specified alignment
        """
        return {cat_id for cat_id, category in self.categories.items() 
                if category.alignment == alignment}
                
    def analyze_values_consistency_across_categories(
        self,
        transactions_by_category: Dict[str, List[Transaction]]
    ) -> Dict[str, Any]:
        """Analyze values consistency across different spending categories.
        
        Args:
            transactions_by_category: Dict mapping spending categories to lists of transactions
            
        Returns:
            Dict with analysis of values consistency across categories
        """
        # Initialize result structure
        result = {
            "category_alignment": {},
            "consistency_score": 0,
            "value_conflicts": [],
            "aligned_categories": [],
            "misaligned_categories": []
        }
        
        # Calculate alignment for each spending category
        for category, transactions in transactions_by_category.items():
            if not transactions:
                continue
                
            # Categorize all transactions in this category
            categorized = self.batch_categorize_transactions(transactions)
            
            # Calculate totals for this category
            total_amount = sum(tx.amount for tx in transactions)
            aligned_amount = 0
            neutral_amount = 0
            misaligned_amount = 0
            
            # Count aligned/neutral/misaligned transactions
            for tx in transactions:
                if tx.id in categorized:
                    alignment = categorized[tx.id]
                    if alignment.alignment_score > 0.3:
                        aligned_amount += tx.amount
                    elif alignment.alignment_score < -0.3:
                        misaligned_amount += tx.amount
                    else:
                        neutral_amount += tx.amount
            
            # Calculate overall alignment score for this category
            # Range from -1.0 (completely misaligned) to 1.0 (completely aligned)
            alignment_score = 0
            if total_amount > 0:
                alignment_score = (aligned_amount - misaligned_amount) / total_amount
            
            # Store category results
            result["category_alignment"][category] = {
                "alignment_score": alignment_score,
                "transaction_count": len(transactions),
                "total_amount": total_amount,
                "aligned_amount": aligned_amount,
                "neutral_amount": neutral_amount,
                "misaligned_amount": misaligned_amount,
                "aligned_percentage": (aligned_amount / total_amount * 100) if total_amount > 0 else 0,
                "misaligned_percentage": (misaligned_amount / total_amount * 100) if total_amount > 0 else 0
            }
            
            # Classify as aligned or misaligned overall
            if alignment_score > 0.3:
                result["aligned_categories"].append(category)
            elif alignment_score < -0.3:
                result["misaligned_categories"].append(category)
        
        # Identify value conflicts (categories with contradictory values)
        for cat1 in result["aligned_categories"]:
            for cat2 in result["misaligned_categories"]:
                # Check if these categories have significant spending
                if (result["category_alignment"][cat1]["total_amount"] > 100 and
                    result["category_alignment"][cat2]["total_amount"] > 100):
                    result["value_conflicts"].append({
                        "category1": cat1,
                        "category2": cat2,
                        "conflict_severity": abs(
                            result["category_alignment"][cat1]["alignment_score"] - 
                            result["category_alignment"][cat2]["alignment_score"]
                        ),
                        "combined_spending": (
                            result["category_alignment"][cat1]["total_amount"] +
                            result["category_alignment"][cat2]["total_amount"]
                        )
                    })
        
        # Sort conflicts by severity
        result["value_conflicts"].sort(key=lambda x: x["conflict_severity"], reverse=True)
        
        # Calculate overall consistency score (0-100)
        # Higher means more consistent values across categories
        if result["category_alignment"]:
            # Calculate the variance of alignment scores
            alignment_scores = [data["alignment_score"] for data in result["category_alignment"].values()]
            alignment_variance = np.var(alignment_scores) if len(alignment_scores) > 1 else 0
            
            # Calculate weighted average of alignment scores
            total_spending = sum(data["total_amount"] for data in result["category_alignment"].values())
            weighted_alignment = 0
            if total_spending > 0:
                for category, data in result["category_alignment"].items():
                    weight = data["total_amount"] / total_spending
                    weighted_alignment += data["alignment_score"] * weight
            
            # Combine weighted alignment (want higher) and variance (want lower)
            # Scale to 0-100
            variance_penalty = min(50, alignment_variance * 100)
            alignment_bonus = ((weighted_alignment + 1) / 2) * 100  # Convert -1...1 to 0...100
            
            result["consistency_score"] = max(0, min(100, alignment_bonus - variance_penalty))
        
        return result
        
    def analyze_values_drift_over_time(
        self,
        transactions: List[Transaction],
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """Detect values drift in spending patterns over time.
        
        Args:
            transactions: List of transactions to analyze
            start_date: Start date for the analysis period
            end_date: End date for the analysis period
            
        Returns:
            Dict with analysis of values drift over time
        """
        # Ensure transactions are sorted by date
        sorted_transactions = sorted(transactions, key=lambda tx: tx.date)
        
        # Group transactions by month
        transactions_by_month = {}
        
        for tx in sorted_transactions:
            if tx.date < start_date or tx.date > end_date:
                continue
                
            # Create a month key (YYYY-MM)
            month_key = tx.date.strftime("%Y-%m")
            
            if month_key not in transactions_by_month:
                transactions_by_month[month_key] = []
                
            transactions_by_month[month_key].append(tx)
        
        # Sort month keys chronologically
        month_keys = sorted(transactions_by_month.keys())
        
        # Analyze each month
        monthly_alignment = {}
        for month in month_keys:
            month_transactions = transactions_by_month[month]
            
            # Skip months with very few transactions
            if len(month_transactions) < 3:
                continue
                
            # Calculate alignment for this month
            categorized = self.batch_categorize_transactions(month_transactions)
            
            aligned_count = 0
            misaligned_count = 0
            neutral_count = 0
            
            aligned_amount = 0
            misaligned_amount = 0
            neutral_amount = 0
            total_spent = sum(tx.amount for tx in month_transactions)
            
            # Count alignment categories
            for tx in month_transactions:
                if tx.id in categorized:
                    alignment = categorized[tx.id]
                    
                    if alignment.alignment_score > 0.3:
                        aligned_count += 1
                        aligned_amount += tx.amount
                    elif alignment.alignment_score < -0.3:
                        misaligned_count += 1
                        misaligned_amount += tx.amount
                    else:
                        neutral_count += 1
                        neutral_amount += tx.amount
            
            total_count = aligned_count + misaligned_count + neutral_count
            
            # Calculate overall alignment score for this month
            alignment_score = 0
            if total_spent > 0:
                alignment_score = (aligned_amount - misaligned_amount) / total_spent
                
            # Store month analysis
            monthly_alignment[month] = {
                "alignment_score": alignment_score,
                "transaction_count": total_count,
                "total_spent": total_spent,
                "aligned_amount": aligned_amount,
                "misaligned_amount": misaligned_amount,
                "neutral_amount": neutral_amount,
                "aligned_percentage": (aligned_count / total_count * 100) if total_count > 0 else 0,
                "misaligned_percentage": (misaligned_count / total_count * 100) if total_count > 0 else 0,
                "neutral_percentage": (neutral_count / total_count * 100) if total_count > 0 else 0,
                "aligned_spending_percentage": (aligned_amount / total_spent * 100) if total_spent > 0 else 0,
                "misaligned_spending_percentage": (misaligned_amount / total_spent * 100) if total_spent > 0 else 0
            }
        
        # Analyze trend over time
        alignment_by_month = [monthly_alignment[month]["alignment_score"] for month in month_keys 
                             if month in monthly_alignment]
        months_index = list(range(len(alignment_by_month)))
        
        # Check if we have enough data points for regression
        drift_detected = False
        drift_magnitude = {}
        trend_analysis = {"slope": 0, "correlation": 0, "is_significant": False}
        
        if len(alignment_by_month) >= 3:
            # Calculate linear regression
            if len(months_index) > 0 and len(alignment_by_month) > 0:
                slope, intercept = np.polyfit(months_index, alignment_by_month, 1)
                
                # Calculate correlation coefficient
                correlation = np.corrcoef(months_index, alignment_by_month)[0, 1]
                
                # Consider trend significant if correlation > 0.7 or < -0.7
                is_significant = abs(correlation) > 0.7
                
                trend_analysis = {
                    "slope": slope,
                    "correlation": correlation,
                    "is_significant": is_significant
                }
                
                # Determine if drift is detected
                drift_detected = is_significant and abs(slope) > 0.1
                
                if drift_detected:
                    # Calculate first and last month scores
                    first_month = month_keys[0]
                    last_month = month_keys[-1]
                    
                    if first_month in monthly_alignment and last_month in monthly_alignment:
                        first_score = monthly_alignment[first_month]["alignment_score"]
                        last_score = monthly_alignment[last_month]["alignment_score"]
                        
                        # Calculate percentage change
                        if abs(first_score) > 0.01:  # Avoid division by zero or very small numbers
                            percentage_change = ((last_score - first_score) / abs(first_score)) * 100
                        else:
                            percentage_change = 0
                            
                        drift_magnitude = {
                            "direction": "improving" if slope > 0 else "worsening",
                            "percentage_change": percentage_change,
                            "first_month_score": first_score,
                            "last_month_score": last_score
                        }
        
        # Generate recommendations based on analysis
        recommendations = []
        
        if drift_detected:
            if drift_magnitude.get("direction") == "worsening":
                # Identify categories with increasing misalignment
                misaligned_categories = {}
                
                # Compare first and last month
                first_month = month_keys[0]
                last_month = month_keys[-1]
                
                if first_month in monthly_alignment and last_month in monthly_alignment:
                    first_month_txs = transactions_by_month[first_month]
                    last_month_txs = transactions_by_month[last_month]
                    
                    # Group by category
                    first_by_category = {}
                    last_by_category = {}
                    
                    for tx in first_month_txs:
                        if tx.category not in first_by_category:
                            first_by_category[tx.category] = []
                        first_by_category[tx.category].append(tx)
                        
                    for tx in last_month_txs:
                        if tx.category not in last_by_category:
                            last_by_category[tx.category] = []
                        last_by_category[tx.category].append(tx)
                    
                    # Compare alignment by category
                    for category in set(last_by_category.keys()):
                        if category in last_by_category:
                            last_txs = last_by_category[category]
                            last_total = sum(tx.amount for tx in last_txs)
                            
                            # Categorize last month's transactions
                            categorized = self.batch_categorize_transactions(last_txs)
                            
                            # Count misaligned spending
                            misaligned_amount = 0
                            for tx in last_txs:
                                if tx.id in categorized and categorized[tx.id].alignment_score < -0.3:
                                    misaligned_amount += tx.amount
                            
                            # Check if category has significant misalignment
                            misalignment_percentage = (misaligned_amount / last_total) if last_total > 0 else 0
                            if misalignment_percentage > 0.5:  # More than 50% misaligned
                                misaligned_categories[category] = misalignment_percentage
                
                # Add recommendation for each misaligned category
                for category, percentage in sorted(misaligned_categories.items(), key=lambda x: x[1], reverse=True):
                    recommendations.append({
                        "type": "reduce_misaligned_category",
                        "category": category,
                        "misalignment_percentage": percentage,
                        "suggestion": f"Consider alternatives for spending in the '{category}' category"
                    })
                
                # Add general recommendation
                recommendations.append({
                    "type": "general_improvement",
                    "suggestion": "Review your spending patterns to better align with your values"
                })
            else:
                # Positive trend recommendations
                recommendations.append({
                    "type": "maintain_improvement",
                    "suggestion": "Continue your positive trend in values-aligned spending"
                })
        else:
            # No significant drift
            # Check if alignment is generally good or poor
            avg_alignment = np.mean(alignment_by_month) if alignment_by_month else 0
            
            if avg_alignment > 0.3:
                recommendations.append({
                    "type": "maintain_good_alignment",
                    "suggestion": "Continue your consistent values-aligned spending"
                })
            elif avg_alignment < -0.3:
                recommendations.append({
                    "type": "improve_alignment",
                    "suggestion": "Consider adjusting spending to better align with your values"
                })
        
        # Compile final result
        result = {
            "monthly_alignment": monthly_alignment,
            "trend_analysis": trend_analysis,
            "drift_detected": drift_detected,
            "drift_magnitude": drift_magnitude if drift_detected else {"direction": "neutral", "percentage_change": 0},
            "average_alignment": np.mean(alignment_by_month) if alignment_by_month else 0,
            "recommendations": recommendations
        }
        
        return result
        
    def analyze_vendor_value_profiles(
        self,
        transactions: List[Transaction]
    ) -> Dict[str, Any]:
        """Create value profiles for vendors based on transaction history.
        
        Args:
            transactions: List of transactions to analyze
            
        Returns:
            Dict with vendor value profiles and rankings
        """
        # Group transactions by vendor
        transactions_by_vendor = {}
        
        for tx in transactions:
            vendor = tx.vendor
            if vendor not in transactions_by_vendor:
                transactions_by_vendor[vendor] = []
                
            transactions_by_vendor[vendor].append(tx)
        
        # Analyze each vendor
        vendor_profiles = {}
        for vendor, vendor_transactions in transactions_by_vendor.items():
            # Skip vendors with very few transactions
            if len(vendor_transactions) < 2:
                continue
                
            # Calculate totals
            total_spent = sum(tx.amount for tx in vendor_transactions)
            
            # Categorize transactions
            categorized = self.batch_categorize_transactions(vendor_transactions)
            
            # Calculate alignment metrics
            aligned_amount = 0
            misaligned_amount = 0
            neutral_amount = 0
            
            # Count alignment categories and collect tags
            all_tags = []
            for tx in vendor_transactions:
                if tx.id in categorized:
                    alignment = categorized[tx.id]
                    
                    if alignment.alignment_score > 0.3:
                        aligned_amount += tx.amount
                    elif alignment.alignment_score < -0.3:
                        misaligned_amount += tx.amount
                    else:
                        neutral_amount += tx.amount
                
                # Collect all tags
                all_tags.extend(tx.tags)
            
            # Calculate overall alignment score for this vendor
            alignment_score = 0
            if total_spent > 0:
                alignment_score = (aligned_amount - misaligned_amount) / total_spent
                # Ensure we stay within the -1.0 to 1.0 bounds (avoiding floating point errors)
                alignment_score = max(-1.0, min(1.0, alignment_score))
                
            # Count tag frequencies
            tag_counts = {}
            for tag in all_tags:
                if tag in tag_counts:
                    tag_counts[tag] += 1
                else:
                    tag_counts[tag] = 1
                    
            # Find most common tags (at least appearing twice)
            common_tags = [tag for tag, count in tag_counts.items() if count > 1]
            
            # Calculate value consistency (higher means more consistent values)
            value_consistency = 0
            if len(vendor_transactions) > 1:
                # Calculate variance of alignment scores
                alignment_scores = [categorized[tx.id].alignment_score for tx in vendor_transactions if tx.id in categorized]
                if alignment_scores:
                    # Lower variance means more consistent
                    variance = np.var(alignment_scores)
                    value_consistency = 1 / (1 + variance)  # Normalize to 0-1 range
            
            # Generate recommendation based on alignment
            recommendation = {}
            if alignment_score < -0.3:
                # Suggest alternatives for misaligned vendors
                category = vendor_transactions[0].category if vendor_transactions else "General"
                alternatives = self.suggest_alternative_vendors(vendor, category)
                
                recommendation = {
                    "type": "consider_alternatives",
                    "reason": "Low values alignment",
                    "alternatives": alternatives
                }
            elif alignment_score > 0.7:
                recommendation = {
                    "type": "continue_patronage",
                    "reason": "Excellent values alignment"
                }
            elif alignment_score > 0.3:
                recommendation = {
                    "type": "maintain",
                    "reason": "Good values alignment"
                }
            else:
                recommendation = {
                    "type": "neutral",
                    "reason": "Neutral values alignment"
                }
                
            # Store vendor profile
            vendor_profiles[vendor] = {
                "transaction_count": len(vendor_transactions),
                "total_spent": total_spent,
                "alignment_score": alignment_score,
                "common_tags": common_tags,
                "value_consistency": value_consistency,
                "recommendation": recommendation,
                "aligned_percentage": (aligned_amount / total_spent * 100) if total_spent > 0 else 0,
                "misaligned_percentage": (misaligned_amount / total_spent * 100) if total_spent > 0 else 0
            }
        
        # Create vendor rankings
        sorted_vendors = sorted(vendor_profiles.items(), key=lambda x: x[1]["alignment_score"], reverse=True)
        
        most_aligned = [vendor for vendor, profile in sorted_vendors 
                        if profile["alignment_score"] > 0.3][:5]  # Top 5 aligned
                        
        least_aligned = [vendor for vendor, profile in sorted_vendors 
                         if profile["alignment_score"] < 0][-5:]  # Bottom 5 aligned
        
        # Generate alternatives for misaligned vendors
        recommended_alternatives = {}
        for vendor, profile in vendor_profiles.items():
            if profile["alignment_score"] < -0.2:
                # Find this vendor's transactions to get categories
                vendor_txs = transactions_by_vendor[vendor]
                
                # Use most common category
                category_counts = {}
                for tx in vendor_txs:
                    if tx.category in category_counts:
                        category_counts[tx.category] += 1
                    else:
                        category_counts[tx.category] = 1
                        
                main_category = max(category_counts.items(), key=lambda x: x[1])[0] if category_counts else "General"
                
                # Get alternatives
                alternatives = self.suggest_alternative_vendors(vendor, main_category)
                
                if alternatives:
                    recommended_alternatives[vendor] = alternatives
        
        # Compile final result
        result = {
            "vendor_profiles": vendor_profiles,
            "vendor_rankings": {
                "most_aligned": most_aligned,
                "least_aligned": least_aligned
            },
            "recommended_alternatives": recommended_alternatives,
            "total_vendors_analyzed": len(vendor_profiles)
        }
        
        return result


def create_default_value_categories() -> List[ValueCategory]:
    """Create a default set of value categories.
    
    Returns:
        List of default ValueCategory objects
    """
    return [
        ValueCategory(
            id="sustainable_food",
            name="Sustainable Food",
            description="Food produced using sustainable methods with minimal environmental impact",
            tags=["organic", "local", "farmers_market", "sustainable", "fair_trade"],
            alignment="aligned",
            impact_level=4,
            alternatives=["conventional_food"]
        ),
        ValueCategory(
            id="conventional_food",
            name="Conventional Food",
            description="Conventionally produced food from standard grocery stores",
            tags=["supermarket", "conventional", "grocery", "processed"],
            alignment="neutral",
            impact_level=2,
            alternatives=["sustainable_food"]
        ),
        ValueCategory(
            id="fast_food",
            name="Fast Food",
            description="Mass-produced food with high environmental impact and low nutritional value",
            tags=["fast_food", "junk_food", "drive_through"],
            alignment="misaligned",
            impact_level=3,
            alternatives=["sustainable_food", "local_restaurant"]
        ),
        ValueCategory(
            id="public_transit",
            name="Public Transportation",
            description="Low-carbon transportation options",
            tags=["bus", "train", "subway", "public_transit", "carpool"],
            alignment="aligned",
            impact_level=4,
            alternatives=["fossil_fuel_transport"]
        ),
        ValueCategory(
            id="fossil_fuel_transport",
            name="Fossil Fuel Transportation",
            description="Transportation using fossil fuels",
            tags=["gas", "petrol", "diesel", "fuel"],
            alignment="misaligned",
            impact_level=4,
            alternatives=["public_transit", "electric_vehicle"]
        ),
        ValueCategory(
            id="electric_vehicle",
            name="Electric Vehicle",
            description="Transportation using electric power",
            tags=["electric", "ev", "charging", "tesla"],
            alignment="aligned",
            impact_level=3,
            alternatives=["fossil_fuel_transport"]
        ),
        ValueCategory(
            id="sustainable_fashion",
            name="Sustainable Fashion",
            description="Clothing produced with ethical labor and sustainable materials",
            tags=["ethical", "sustainable", "fair_trade", "secondhand", "thrift"],
            alignment="aligned",
            impact_level=3,
            alternatives=["fast_fashion"]
        ),
        ValueCategory(
            id="fast_fashion",
            name="Fast Fashion",
            description="Inexpensive clothing produced rapidly with high environmental impact",
            tags=["fast_fashion", "discount_clothes", "cheap_clothing"],
            alignment="misaligned",
            impact_level=3,
            alternatives=["sustainable_fashion"]
        ),
        ValueCategory(
            id="local_business",
            name="Local Business",
            description="Independently owned local businesses",
            tags=["local", "independent", "small_business", "community"],
            alignment="aligned",
            impact_level=4,
            alternatives=["chain_business"]
        ),
        ValueCategory(
            id="chain_business",
            name="Chain Business",
            description="Large chain businesses and corporations",
            tags=["chain", "corporation", "franchise"],
            alignment="neutral",
            impact_level=2,
            alternatives=["local_business"]
        ),
        ValueCategory(
            id="charitable_giving",
            name="Charitable Giving",
            description="Donations to charitable causes and organizations",
            tags=["donation", "charity", "nonprofit", "giving", "philanthropy"],
            alignment="aligned",
            impact_level=5,
            alternatives=[]
        ),
        ValueCategory(
            id="renewable_energy",
            name="Renewable Energy",
            description="Energy from renewable sources",
            tags=["renewable", "solar", "wind", "green_energy"],
            alignment="aligned",
            impact_level=5,
            alternatives=["fossil_fuel_energy"]
        ),
        ValueCategory(
            id="fossil_fuel_energy",
            name="Fossil Fuel Energy",
            description="Energy from fossil fuel sources",
            tags=["coal", "natural_gas", "oil", "fossil_fuel"],
            alignment="misaligned",
            impact_level=5,
            alternatives=["renewable_energy"]
        )
    ]