"""
Routes for cryptocurrency data functionality.
"""
from flask import render_template, request, jsonify, current_app
from app.routes.crypto import crypto_bp

@crypto_bp.route('/', methods=['GET'])
def index():
    """Cryptocurrency dashboard landing page."""
    # Sample crypto data for preview
    crypto_data = [
        {'name': 'Bitcoin', 'symbol': 'BTC', 'price': 44500.00, 'change': 2.5},
        {'name': 'Ethereum', 'symbol': 'ETH', 'price': 3200.00, 'change': 1.2},
        {'name': 'Cardano', 'symbol': 'ADA', 'price': 1.20, 'change': -0.8},
        {'name': 'Solana', 'symbol': 'SOL', 'price': 105.00, 'change': 5.3},
    ]
    return render_template('crypto/index.html', crypto_data=crypto_data)
