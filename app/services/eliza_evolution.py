"""
TechSaaS Eliza Evolution Service

This module enables Eliza to analyze application usage patterns and suggest
improvements and new features based on real application data. It implements
a feedback loop where Eliza can learn from user behaviors and evolve the platform.
"""

import os
import json
import logging
import datetime
import statistics
from collections import Counter, defaultdict
from flask import current_app
from sqlalchemy import desc, func

# Optional dependencies - comment out if not installed
# import pandas as pd
# import numpy as np

# Configure logger
logger = logging.getLogger(__name__)

class EvolutionMetric:
    """Class for tracking evolution metrics and identifying trends"""
    
    def __init__(self, name, category, value=0, count=0):
        """Initialize a metric
        
        Args:
            name: Metric name
            category: Metric category (usage, performance, feature, etc.)
            value: Initial value
            count: Number of data points
        """
        self.name = name
        self.category = category
        self.value = value
        self.count = count
        self.history = []
        self.created_at = datetime.datetime.now()
        self.updated_at = datetime.datetime.now()
    
    def add_value(self, value):
        """Add a new value to the metric"""
        self.history.append({
            'value': value,
            'timestamp': datetime.datetime.now().isoformat()
        })
        
        # Update running average
        self.value = ((self.value * self.count) + value) / (self.count + 1)
        self.count += 1
        self.updated_at = datetime.datetime.now()
    
    def get_trend(self):
        """Calculate the trend of this metric
        
        Returns:
            Trend percentage change over last 10 values, or None if insufficient data
        """
        if len(self.history) < 10:
            return None
            
        # Get last 10 values
        recent_values = [item['value'] for item in self.history[-10:]]
        
        # Calculate trend (simple linear regression slope)
        x = list(range(len(recent_values)))
        y = recent_values
        
        if len(set(y)) == 1:  # All values are the same
            return 0.0
        
        # Basic trend calculation
        mean_x = sum(x) / len(x)
        mean_y = sum(y) / len(y)
        
        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(len(x)))
        denominator = sum((x[i] - mean_x) ** 2 for i in range(len(x)))
        
        if denominator == 0:
            return 0.0
            
        slope = numerator / denominator
        
        # Convert to percentage change relative to mean
        if mean_y == 0:
            return 0.0
            
        return (slope * 10 / mean_y) * 100  # Percentage change over 10 points
    
    def to_dict(self):
        """Convert metric to dictionary"""
        return {
            'name': self.name,
            'category': self.category,
            'value': self.value,
            'count': self.count,
            'trend': self.get_trend(),
            'history': self.history[-10:] if len(self.history) > 10 else self.history,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class ElizaEvolution:
    """Service for Eliza to evolve the TechSaaS platform based on usage data"""
    
    def __init__(self, storage_path=None):
        """Initialize the evolution service
        
        Args:
            storage_path: Path to store evolution data
        """
        self.storage_path = storage_path or os.path.join(
            current_app.config.get('UPLOAD_FOLDER', 'app/static/uploads'),
            'eliza_evolution'
        )
        
        # Ensure directory exists
        os.makedirs(self.storage_path, exist_ok=True)
        
        # Metrics storage
        self.metrics = self._load_metrics()
        
        # Feature suggestions
        self.feature_suggestions = self._load_feature_suggestions()
        
        # Last analysis timestamp
        self.last_analysis = datetime.datetime.now()
    
    def _load_metrics(self):
        """Load metrics from storage"""
        metrics_path = os.path.join(self.storage_path, 'metrics.json')
        if os.path.exists(metrics_path):
            try:
                with open(metrics_path, 'r') as f:
                    data = json.load(f)
                    
                metrics = {}
                for category, items in data.items():
                    metrics[category] = {}
                    for name, metric_data in items.items():
                        metric = EvolutionMetric(name, category)
                        metric.value = metric_data.get('value', 0)
                        metric.count = metric_data.get('count', 0)
                        metric.history = metric_data.get('history', [])
                        metric.created_at = datetime.datetime.fromisoformat(metric_data.get('created_at', datetime.datetime.now().isoformat()))
                        metric.updated_at = datetime.datetime.fromisoformat(metric_data.get('updated_at', datetime.datetime.now().isoformat()))
                        metrics[category][name] = metric
                
                return metrics
            except Exception as e:
                logger.error(f"Error loading metrics: {str(e)}")
                return defaultdict(dict)
        else:
            return defaultdict(dict)
    
    def _save_metrics(self):
        """Save metrics to storage"""
        metrics_path = os.path.join(self.storage_path, 'metrics.json')
        try:
            data = {}
            for category, items in self.metrics.items():
                data[category] = {}
                for name, metric in items.items():
                    data[category][name] = metric.to_dict()
            
            with open(metrics_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving metrics: {str(e)}")
    
    def _load_feature_suggestions(self):
        """Load feature suggestions from storage"""
        suggestions_path = os.path.join(self.storage_path, 'feature_suggestions.json')
        if os.path.exists(suggestions_path):
            try:
                with open(suggestions_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading feature suggestions: {str(e)}")
                return []
        else:
            return []
    
    def _save_feature_suggestions(self):
        """Save feature suggestions to storage"""
        suggestions_path = os.path.join(self.storage_path, 'feature_suggestions.json')
        try:
            with open(suggestions_path, 'w') as f:
                json.dump(self.feature_suggestions, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving feature suggestions: {str(e)}")
    
    def record_metric(self, category, name, value):
        """Record a metric value
        
        Args:
            category: Metric category
            name: Metric name
            value: Metric value
        """
        if category not in self.metrics:
            self.metrics[category] = {}
            
        if name not in self.metrics[category]:
            self.metrics[category][name] = EvolutionMetric(name, category, value, 1)
        else:
            self.metrics[category][name].add_value(value)
            
        # Save metrics
        self._save_metrics()
    
    def get_metrics(self, category=None):
        """Get metrics by category
        
        Args:
            category: Optional category to filter by
            
        Returns:
            Dictionary of metrics
        """
        if category:
            return {name: metric.to_dict() for name, metric in self.metrics.get(category, {}).items()}
        else:
            result = {}
            for category, items in self.metrics.items():
                result[category] = {name: metric.to_dict() for name, metric in items.items()}
            return result
    
    def analyze_system_usage(self, db):
        """Analyze system usage data from the database
        
        Args:
            db: Database session
            
        Returns:
            Analysis results
        """
        try:
            results = {}
            
            # Check if we have the models imported
            from app.models.scraped_data.scraped_data import ScrapedData
            from app.models.user import User
            
            # User activity analysis
            user_count = db.session.query(func.count(User.id)).scalar()
            active_users = db.session.query(func.count(User.id)).filter(
                User.last_login > (datetime.datetime.now() - datetime.timedelta(days=7))
            ).scalar()
            
            results['users'] = {
                'total': user_count,
                'active_last_7_days': active_users,
                'activity_ratio': active_users / user_count if user_count > 0 else 0
            }
            
            # Record user metrics
            self.record_metric('users', 'total', user_count)
            self.record_metric('users', 'active', active_users)
            
            # Scraping activity analysis
            scrape_count = db.session.query(func.count(ScrapedData.id)).scalar()
            recent_scrapes = db.session.query(func.count(ScrapedData.id)).filter(
                ScrapedData.created_at > (datetime.datetime.now() - datetime.timedelta(days=7))
            ).scalar()
            
            results['scraping'] = {
                'total': scrape_count,
                'last_7_days': recent_scrapes,
                'recent_ratio': recent_scrapes / scrape_count if scrape_count > 0 else 0
            }
            
            # Record scraping metrics
            self.record_metric('scraping', 'total', scrape_count)
            self.record_metric('scraping', 'recent', recent_scrapes)
            
            # TODO: Add more analyses as needed
            
            # Mark last analysis time
            self.last_analysis = datetime.datetime.now()
            
            return results
        except Exception as e:
            logger.error(f"Error analyzing system usage: {str(e)}")
            return {'error': str(e)}
    
    def suggest_features(self, usage_data):
        """Generate feature suggestions based on usage data
        
        Args:
            usage_data: Usage data from analyze_system_usage
            
        Returns:
            List of feature suggestions
        """
        suggestions = []
        
        try:
            # Example logic - can be expanded with more sophisticated analysis
            if 'scraping' in usage_data:
                scraping_data = usage_data['scraping']
                
                # If scraping usage is high, suggest advanced features
                if scraping_data.get('recent_ratio', 0) > 0.3:
                    suggestions.append({
                        'title': 'Advanced Scraping Filters',
                        'description': 'Based on high scraping activity, users would benefit from advanced content filtering options.',
                        'priority': 'high',
                        'category': 'scraping',
                        'metrics': {
                            'recent_ratio': scraping_data.get('recent_ratio', 0),
                            'total_scrapes': scraping_data.get('total', 0)
                        },
                        'created_at': datetime.datetime.now().isoformat()
                    })
            
            # Example: Check user activity and suggest features
            if 'users' in usage_data:
                user_data = usage_data['users']
                
                # If activity ratio is low, suggest user engagement features
                if user_data.get('activity_ratio', 0) < 0.2:
                    suggestions.append({
                        'title': 'User Engagement Dashboard',
                        'description': 'Low user activity suggests a need for better engagement tools like a personalized dashboard.',
                        'priority': 'medium',
                        'category': 'users',
                        'metrics': {
                            'activity_ratio': user_data.get('activity_ratio', 0),
                            'total_users': user_data.get('total', 0)
                        },
                        'created_at': datetime.datetime.now().isoformat()
                    })
            
            # Check trending metrics for additional insights
            for category, metrics in self.metrics.items():
                for name, metric in metrics.items():
                    trend = metric.get_trend()
                    
                    if trend is not None:
                        # Significant upward trend
                        if trend > 20:
                            suggestions.append({
                                'title': f'Expand {category.capitalize()} {name.capitalize()} Features',
                                'description': f'Usage of {name} in {category} is trending up significantly ({trend:.1f}%). Consider expanding these capabilities.',
                                'priority': 'high',
                                'category': category,
                                'metrics': {
                                    'trend': trend,
                                    'value': metric.value
                                },
                                'created_at': datetime.datetime.now().isoformat()
                            })
                        # Significant downward trend
                        elif trend < -20:
                            suggestions.append({
                                'title': f'Evaluate {category.capitalize()} {name.capitalize()} Features',
                                'description': f'Usage of {name} in {category} is trending down significantly ({trend:.1f}%). Consider evaluating and improving these features.',
                                'priority': 'medium',
                                'category': category,
                                'metrics': {
                                    'trend': trend,
                                    'value': metric.value
                                },
                                'created_at': datetime.datetime.now().isoformat()
                            })
            
            # Add suggestions to the existing list (avoiding duplicates)
            existing_titles = {s['title'] for s in self.feature_suggestions}
            for suggestion in suggestions:
                if suggestion['title'] not in existing_titles:
                    self.feature_suggestions.append(suggestion)
                    existing_titles.add(suggestion['title'])
            
            # Save suggestions
            self._save_feature_suggestions()
            
            return suggestions
        except Exception as e:
            logger.error(f"Error generating feature suggestions: {str(e)}")
            return []
    
    def generate_social_content(self, platform='twitter'):
        """Generate social media content based on app analytics and feature updates
        
        Args:
            platform: Social media platform to generate content for
            
        Returns:
            List of content items with text and metadata
        """
        content_items = []
        
        try:
            # Generate content about feature suggestions
            for suggestion in self.feature_suggestions[:3]:  # Focus on top 3 newest
                title = suggestion['title']
                category = suggestion.get('category', 'general')
                
                if platform == 'twitter':
                    text = f"🚀 TechSaaS is evolving! I'm suggesting a new feature: {title} based on user activity in {category}. #TechSaaS #AI #DataAnalysis"
                    content_items.append({
                        'text': text,
                        'type': 'feature_suggestion',
                        'suggestion_id': suggestion.get('id', title),
                        'platform': platform,
                        'created_at': datetime.datetime.now().isoformat()
                    })
            
            # Generate content about interesting metrics
            interesting_metrics = []
            for category, metrics in self.metrics.items():
                for name, metric in metrics.items():
                    # Only consider metrics with enough data points
                    if metric.count >= 5:
                        trend = metric.get_trend()
                        if trend is not None and abs(trend) > 15:
                            interesting_metrics.append((category, name, metric, trend))
            
            # Sort by absolute trend value (most significant first)
            interesting_metrics.sort(key=lambda x: abs(x[3]), reverse=True)
            
            # Generate content for top metrics
            for category, name, metric, trend in interesting_metrics[:2]:
                trend_direction = "📈 increasing" if trend > 0 else "📉 decreasing"
                
                if platform == 'twitter':
                    text = f"I've noticed {category} {name} is {trend_direction} by {abs(trend):.1f}% in TechSaaS. I'm learning from this to suggest improvements! #TechSaaS #AILearning"
                    content_items.append({
                        'text': text,
                        'type': 'metric_insight',
                        'metric': f"{category}.{name}",
                        'trend': trend,
                        'platform': platform,
                        'created_at': datetime.datetime.now().isoformat()
                    })
            
            return content_items
        except Exception as e:
            logger.error(f"Error generating social content: {str(e)}")
            return []


# Convenience function to get service instance
def get_evolution_service():
    """Get an instance of the evolution service
    
    Returns:
        Configured evolution service instance
    """
    return ElizaEvolution()
