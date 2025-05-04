"""
Database Connector for API Gateway

This module provides database connection and operations for the API Gateway,
specifically for persisting API keys, usage data, and subscription information.
"""

import os
import json
import time
import logging
import sqlite3
from datetime import datetime, timedelta
from threading import Lock

logger = logging.getLogger("api_gateway.db")

# Database file path
DB_FILE = os.environ.get('API_DB_FILE', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'api_gateway.db'))

# Ensure data directory exists
os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)

# Thread lock for database operations
db_lock = Lock()

class DBConnector:
    """Database connector for API Gateway operations"""
    
    def __init__(self, db_file=DB_FILE):
        """Initialize the database connector"""
        self.db_file = db_file
        self._init_db()
    
    def _get_connection(self):
        """Get a database connection"""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """Initialize the database schema"""
        with db_lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # API Keys table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_keys (
                key_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                user_id TEXT NOT NULL,
                api_key TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                last_used INTEGER,
                status TEXT NOT NULL,
                tier TEXT NOT NULL
            )
            ''')
            
            # API Usage table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_id TEXT NOT NULL,
                endpoint TEXT NOT NULL,
                count INTEGER NOT NULL,
                date TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                FOREIGN KEY (key_id) REFERENCES api_keys (key_id)
            )
            ''')
            
            # Subscription tiers table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscription_tiers (
                tier_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                rate_limit INTEGER NOT NULL,
                features TEXT NOT NULL,
                price_amount REAL NOT NULL,
                price_currency TEXT NOT NULL,
                price_interval TEXT NOT NULL
            )
            ''')
            
            # User subscriptions table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_subscriptions (
                user_id TEXT NOT NULL,
                tier_id TEXT NOT NULL,
                start_date INTEGER NOT NULL,
                end_date INTEGER,
                status TEXT NOT NULL,
                PRIMARY KEY (user_id, tier_id),
                FOREIGN KEY (tier_id) REFERENCES subscription_tiers (tier_id)
            )
            ''')
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys (user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_api_usage_key_id ON api_usage (key_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_api_usage_date ON api_usage (date)')
            
            conn.commit()
            conn.close()
            
            # Initialize subscription tiers if they don't exist
            self._init_subscription_tiers()
    
    def _init_subscription_tiers(self):
        """Initialize subscription tiers"""
        tiers = {
            "free": {
                "name": "Free Tier",
                "description": "Basic access for evaluation and personal projects",
                "rate_limit": 60,
                "features": json.dumps(["Basic API access", "Public data only", "Community support"]),
                "price_amount": 0,
                "price_currency": "USD",
                "price_interval": "month"
            },
            "basic": {
                "name": "Basic Tier",
                "description": "Enhanced access for startups and small businesses",
                "rate_limit": 300,
                "features": json.dumps([
                    "Full API access",
                    "Advanced data access",
                    "Email support",
                    "Analytics dashboard"
                ]),
                "price_amount": 49,
                "price_currency": "USD",
                "price_interval": "month"
            },
            "professional": {
                "name": "Professional Tier",
                "description": "High-volume access for growing businesses",
                "rate_limit": 1000,
                "features": json.dumps([
                    "Full API access",
                    "Premium data access",
                    "Priority support",
                    "Advanced analytics",
                    "Customizable rate limits"
                ]),
                "price_amount": 199,
                "price_currency": "USD",
                "price_interval": "month"
            },
            "enterprise": {
                "name": "Enterprise Tier",
                "description": "Unlimited access for large organizations",
                "rate_limit": 5000,
                "features": json.dumps([
                    "Full API access",
                    "Premium data access",
                    "Dedicated support",
                    "Custom solutions",
                    "Service level agreement",
                    "Custom rate limits"
                ]),
                "price_amount": 999,
                "price_currency": "USD",
                "price_interval": "month"
            }
        }
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        for tier_id, tier_data in tiers.items():
            # Check if tier exists
            cursor.execute('SELECT COUNT(*) FROM subscription_tiers WHERE tier_id = ?', (tier_id,))
            count = cursor.fetchone()[0]
            
            if count == 0:
                # Insert tier
                cursor.execute('''
                INSERT INTO subscription_tiers (
                    tier_id, name, description, rate_limit, features,
                    price_amount, price_currency, price_interval
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    tier_id, tier_data['name'], tier_data['description'],
                    tier_data['rate_limit'], tier_data['features'],
                    tier_data['price_amount'], tier_data['price_currency'],
                    tier_data['price_interval']
                ))
        
        conn.commit()
        conn.close()
    
    def get_subscription_tiers(self):
        """Get all subscription tiers"""
        with db_lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM subscription_tiers ORDER BY price_amount')
            rows = cursor.fetchall()
            
            tiers = []
            for row in rows:
                tier = dict(row)
                tier['features'] = json.loads(tier['features'])
                tier['price'] = {
                    'amount': tier.pop('price_amount'),
                    'currency': tier.pop('price_currency'),
                    'interval': tier.pop('price_interval')
                }
                tiers.append(tier)
            
            conn.close()
            return tiers
    
    def get_subscription_tier(self, tier_id):
        """Get a specific subscription tier"""
        with db_lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM subscription_tiers WHERE tier_id = ?', (tier_id,))
            row = cursor.fetchone()
            
            if row:
                tier = dict(row)
                tier['features'] = json.loads(tier['features'])
                tier['price'] = {
                    'amount': tier.pop('price_amount'),
                    'currency': tier.pop('price_currency'),
                    'interval': tier.pop('price_interval')
                }
                conn.close()
                return tier
            
            conn.close()
            return None
    
    def get_api_keys(self, user_id):
        """Get API keys for a user"""
        with db_lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT key_id, name, created_at, last_used, status, tier
            FROM api_keys WHERE user_id = ?
            ''', (user_id,))
            
            keys = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            return keys
    
    def get_api_key(self, key_id):
        """Get a specific API key"""
        with db_lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM api_keys WHERE key_id = ?', (key_id,))
            row = cursor.fetchone()
            
            conn.close()
            return dict(row) if row else None
    
    def create_api_key(self, key_id, name, user_id, api_key, tier="free"):
        """Create a new API key"""
        with db_lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            now = int(time.time())
            
            cursor.execute('''
            INSERT INTO api_keys (key_id, name, user_id, api_key, created_at, status, tier)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (key_id, name, user_id, api_key, now, "active", tier))
            
            conn.commit()
            conn.close()
            
            return {
                "key_id": key_id,
                "name": name,
                "api_key": api_key,
                "created_at": now,
                "status": "active",
                "tier": tier
            }
    
    def update_api_key(self, key_id, **updates):
        """Update an API key"""
        allowed_fields = ["name", "status", "tier", "last_used"]
        updates = {k: v for k, v in updates.items() if k in allowed_fields}
        
        if not updates:
            return False
        
        with db_lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            set_clause = ", ".join([f"{field} = ?" for field in updates.keys()])
            values = list(updates.values())
            values.append(key_id)
            
            cursor.execute(f'''
            UPDATE api_keys
            SET {set_clause}
            WHERE key_id = ?
            ''', values)
            
            success = cursor.rowcount > 0
            
            conn.commit()
            conn.close()
            
            return success
    
    def validate_api_key(self, api_key):
        """Validate an API key and return key information"""
        with db_lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT key_id, user_id, tier, status
            FROM api_keys
            WHERE api_key = ? AND status = 'active'
            ''', (api_key,))
            
            row = cursor.fetchone()
            
            if row:
                # Update last used time
                now = int(time.time())
                cursor.execute('''
                UPDATE api_keys
                SET last_used = ?
                WHERE key_id = ?
                ''', (now, row['key_id']))
                
                conn.commit()
                
                result = dict(row)
                
                # Get tier details
                tier_id = result.get('tier')
                tier = self.get_subscription_tier(tier_id)
                if tier:
                    result['rate_limit'] = tier.get('rate_limit')
                
                conn.close()
                return result
            
            conn.close()
            return None
    
    def track_api_usage(self, key_id, endpoint, count=1, date=None):
        """Track API usage for a key"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        with db_lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            now = int(time.time())
            
            # Check if record exists for this key, endpoint, and date
            cursor.execute('''
            SELECT id, count FROM api_usage
            WHERE key_id = ? AND endpoint = ? AND date = ?
            ''', (key_id, endpoint, date))
            
            row = cursor.fetchone()
            
            if row:
                # Update existing record
                new_count = row['count'] + count
                cursor.execute('''
                UPDATE api_usage
                SET count = ?, timestamp = ?
                WHERE id = ?
                ''', (new_count, now, row['id']))
            else:
                # Create new record
                cursor.execute('''
                INSERT INTO api_usage (key_id, endpoint, count, date, timestamp)
                VALUES (?, ?, ?, ?, ?)
                ''', (key_id, endpoint, count, date, now))
            
            conn.commit()
            conn.close()
            
            return True
    
    def get_api_usage(self, key_id=None, user_id=None, start_date=None, end_date=None):
        """Get API usage data"""
        if not key_id and not user_id:
            return []
        
        # Set default date range if not provided
        if not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
        
        if not start_date:
            # Default to last 30 days
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        with db_lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            query_params = []
            
            if key_id:
                # Get usage for a specific key
                query = '''
                SELECT u.date, u.endpoint, u.count, u.timestamp, a.name as key_name
                FROM api_usage u
                JOIN api_keys a ON u.key_id = a.key_id
                WHERE u.key_id = ? AND u.date BETWEEN ? AND ?
                ORDER BY u.date DESC, u.endpoint
                '''
                query_params = [key_id, start_date, end_date]
            else:
                # Get usage for all keys belonging to a user
                query = '''
                SELECT u.date, u.endpoint, u.count, u.timestamp, a.key_id, a.name as key_name
                FROM api_usage u
                JOIN api_keys a ON u.key_id = a.key_id
                WHERE a.user_id = ? AND u.date BETWEEN ? AND ?
                ORDER BY u.date DESC, a.key_id, u.endpoint
                '''
                query_params = [user_id, start_date, end_date]
            
            cursor.execute(query, query_params)
            rows = cursor.fetchall()
            
            # Format the results
            usage_by_date = {}
            for row in rows:
                row_dict = dict(row)
                date = row_dict['date']
                
                if date not in usage_by_date:
                    usage_by_date[date] = {
                        'date': date,
                        'total_requests': 0,
                        'endpoints': []
                    }
                
                # Add endpoint usage
                endpoint_data = {
                    'endpoint': row_dict['endpoint'],
                    'requests': row_dict['count']
                }
                
                if 'key_id' in row_dict:
                    endpoint_data['key_id'] = row_dict['key_id']
                    endpoint_data['key_name'] = row_dict['key_name']
                
                usage_by_date[date]['endpoints'].append(endpoint_data)
                usage_by_date[date]['total_requests'] += row_dict['count']
            
            # Convert to list and sort by date (newest first)
            usage_data = list(usage_by_date.values())
            usage_data.sort(key=lambda x: x['date'], reverse=True)
            
            conn.close()
            return usage_data
    
    def get_user_subscription(self, user_id):
        """Get a user's current subscription"""
        with db_lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            now = int(time.time())
            
            cursor.execute('''
            SELECT s.*, t.name, t.description, t.rate_limit, t.features,
                   t.price_amount, t.price_currency, t.price_interval
            FROM user_subscriptions s
            JOIN subscription_tiers t ON s.tier_id = t.tier_id
            WHERE s.user_id = ? AND s.status = 'active' AND (s.end_date IS NULL OR s.end_date > ?)
            ORDER BY t.price_amount DESC
            LIMIT 1
            ''', (user_id, now))
            
            row = cursor.fetchone()
            
            if not row:
                # If no active subscription, return the free tier
                cursor.execute('''
                SELECT * FROM subscription_tiers WHERE tier_id = 'free'
                ''')
                tier_row = cursor.fetchone()
                
                if tier_row:
                    subscription = {
                        'user_id': user_id,
                        'tier_id': 'free',
                        'start_date': now,
                        'end_date': None,
                        'status': 'active',
                        **dict(tier_row)
                    }
                    
                    subscription['features'] = json.loads(subscription['features'])
                    subscription['price'] = {
                        'amount': subscription.pop('price_amount'),
                        'currency': subscription.pop('price_currency'),
                        'interval': subscription.pop('price_interval')
                    }
                    
                    conn.close()
                    return subscription
            else:
                subscription = dict(row)
                
                subscription['features'] = json.loads(subscription['features'])
                subscription['price'] = {
                    'amount': subscription.pop('price_amount'),
                    'currency': subscription.pop('price_currency'),
                    'interval': subscription.pop('price_interval')
                }
                
                conn.close()
                return subscription
            
            conn.close()
            return None
    
    def set_user_subscription(self, user_id, tier_id, start_date=None, end_date=None):
        """Set a user's subscription"""
        if start_date is None:
            start_date = int(time.time())
        
        with db_lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Check if a subscription already exists
            cursor.execute('''
            SELECT tier_id FROM user_subscriptions
            WHERE user_id = ? AND status = 'active'
            ''', (user_id,))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update the existing subscription
                if existing['tier_id'] != tier_id:
                    # Deactivate the current subscription
                    cursor.execute('''
                    UPDATE user_subscriptions
                    SET status = 'inactive', end_date = ?
                    WHERE user_id = ? AND tier_id = ? AND status = 'active'
                    ''', (start_date, user_id, existing['tier_id']))
                    
                    # Create a new subscription
                    cursor.execute('''
                    INSERT INTO user_subscriptions (user_id, tier_id, start_date, end_date, status)
                    VALUES (?, ?, ?, ?, 'active')
                    ''', (user_id, tier_id, start_date, end_date))
                else:
                    # Just update the end date if needed
                    if end_date is not None:
                        cursor.execute('''
                        UPDATE user_subscriptions
                        SET end_date = ?
                        WHERE user_id = ? AND tier_id = ? AND status = 'active'
                        ''', (end_date, user_id, tier_id))
            else:
                # Create a new subscription
                cursor.execute('''
                INSERT INTO user_subscriptions (user_id, tier_id, start_date, end_date, status)
                VALUES (?, ?, ?, ?, 'active')
                ''', (user_id, tier_id, start_date, end_date))
            
            conn.commit()
            
            # Get the subscription details
            subscription = self.get_user_subscription(user_id)
            
            conn.close()
            return subscription

# Singleton instance
_db_connector = None

def get_db_connector():
    """Get the database connector singleton instance"""
    global _db_connector
    if _db_connector is None:
        _db_connector = DBConnector()
    return _db_connector
