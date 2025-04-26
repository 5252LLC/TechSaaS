"""
Routes for cryptocurrency data functionality.
"""
from flask import render_template, request, jsonify, current_app
from app.routes.crypto import crypto_bp
import requests
import logging
from flask_login import login_required

@crypto_bp.route('/', methods=['GET'])
@login_required
def index():
    """Cryptocurrency dashboard landing page."""
    try:
        # Attempt to fetch live cryptocurrency data
        api_url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": "10",
            "page": "1",
            "sparkline": "false"
        }
        
        response = requests.get(api_url, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            crypto_data = []
            
            for coin in data:
                crypto_data.append({
                    'name': coin['name'],
                    'symbol': coin['symbol'].upper(),
                    'price': coin['current_price'],
                    'change': coin['price_change_percentage_24h'] or 0
                })
            
            logging.info(f"Successfully fetched live crypto data: {len(crypto_data)} coins")
        else:
            # Fallback to sample data if API request fails
            logging.warning(f"Failed to fetch live crypto data. Status code: {response.status_code}")
            crypto_data = [
                {'name': 'Bitcoin', 'symbol': 'BTC', 'price': 44500.00, 'change': 2.5},
                {'name': 'Ethereum', 'symbol': 'ETH', 'price': 3200.00, 'change': 1.2},
                {'name': 'Cardano', 'symbol': 'ADA', 'price': 1.20, 'change': -0.8},
                {'name': 'Solana', 'symbol': 'SOL', 'price': 105.00, 'change': 5.3},
            ]
    except Exception as e:
        # Handle any exceptions and fall back to sample data
        logging.error(f"Error fetching crypto data: {str(e)}")
        crypto_data = [
            {'name': 'Bitcoin', 'symbol': 'BTC', 'price': 44500.00, 'change': 2.5},
            {'name': 'Ethereum', 'symbol': 'ETH', 'price': 3200.00, 'change': 1.2},
            {'name': 'Cardano', 'symbol': 'ADA', 'price': 1.20, 'change': -0.8},
            {'name': 'Solana', 'symbol': 'SOL', 'price': 105.00, 'change': 5.3},
        ]
    
    return render_template('crypto/index.html', crypto_data=crypto_data)
