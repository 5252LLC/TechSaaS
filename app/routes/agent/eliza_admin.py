"""
TechSaaS Eliza Admin Routes

This module provides administrative routes for Eliza's evolution features,
allowing access to platform metrics, feature suggestions, and social media content.
"""

from flask import Blueprint, jsonify, request, render_template, current_app
from flask_login import login_required, current_user
import datetime

from app.services.eliza_service import get_eliza_service
from app import db

# Initialize blueprint
eliza_admin_bp = Blueprint('eliza_admin', __name__, url_prefix='/agent/admin/eliza')

@eliza_admin_bp.route('/metrics', methods=['GET'])
@login_required
def metrics():
    """Get platform metrics collected by Eliza"""
    if not current_user.is_admin():
        return jsonify({'error': 'Administrator access required'}), 403
        
    eliza = get_eliza_service()
    metrics = eliza.evolution.get_metrics()
    
    return jsonify({
        'metrics': metrics,
        'timestamp': datetime.datetime.now().isoformat()
    })

@eliza_admin_bp.route('/analyze', methods=['POST'])
@login_required
def analyze_platform():
    """Trigger platform analysis to generate metrics and suggestions"""
    if not current_user.is_admin():
        return jsonify({'error': 'Administrator access required'}), 403
        
    eliza = get_eliza_service()
    analysis = eliza.analyze_platform_metrics(db)
    
    return jsonify({
        'analysis': analysis,
        'timestamp': datetime.datetime.now().isoformat()
    })

@eliza_admin_bp.route('/suggestions', methods=['GET'])
@login_required
def suggestions():
    """Get feature suggestions generated by Eliza"""
    if not current_user.is_admin():
        return jsonify({'error': 'Administrator access required'}), 403
        
    eliza = get_eliza_service()
    suggestions = eliza.evolution.feature_suggestions
    
    return jsonify({
        'suggestions': suggestions,
        'count': len(suggestions),
        'timestamp': datetime.datetime.now().isoformat()
    })

@eliza_admin_bp.route('/tweet', methods=['GET'])
@login_required
def generate_tweet():
    """Generate a tweet based on platform metrics and suggestions"""
    if not current_user.is_admin():
        return jsonify({'error': 'Administrator access required'}), 403
        
    eliza = get_eliza_service()
    tweet = eliza.generate_tweet()
    
    return jsonify({
        'tweet': tweet,
        'timestamp': datetime.datetime.now().isoformat()
    })

@eliza_admin_bp.route('/memory', methods=['GET'])
@login_required
def memory_stats():
    """Get statistics about Eliza's memory system"""
    if not current_user.is_admin():
        return jsonify({'error': 'Administrator access required'}), 403
        
    eliza = get_eliza_service()
    
    # Collect memory statistics
    stats = {
        'categories': {},
        'total_memories': 0
    }
    
    for category in ['interactions', 'learnings', 'patterns', 'system']:
        memories = eliza.memory.retrieve(category)
        if memories:
            stats['categories'][category] = len(memories)
            stats['total_memories'] += len(memories)
    
    return jsonify({
        'memory_stats': stats,
        'timestamp': datetime.datetime.now().isoformat()
    })
