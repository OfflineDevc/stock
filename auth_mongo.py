import streamlit as st
import pymongo
import bcrypt
import time
from datetime import datetime, date

# --- DATABASE CONNECTION ---
@st.cache_resource
def init_connection():
    try:
        if 'MONGO_URI' not in st.secrets:
            # st.error("🚨 Missing 'MONGO_URI' in .streamlit/secrets.toml")
            return None
        return pymongo.MongoClient(st.secrets["MONGO_URI"])
    except Exception as e:
        st.error(f"Failed to connect to DB: {e}")
        return None

def get_db():
    client = init_connection()
    if client:
        return client.stockdeck_db
    return None

# --- AUTHENTICATION ---

def sign_up(username, password, name):
    db = get_db()
    if db is None: return False, "Database connection failed."

    users = db.users
    if users.find_one({'username': username}):
        return False, "Username already exists."
    
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    new_user = {
        "username": username,
        "password": hashed,
        "name": name,
        "created_at": datetime.now(),
        "role": "user",
        "tier": "standard"  # Default Tier
    }
    
    try:
        users.insert_one(new_user)
        return True, "Account created successfully! Please log in."
    except Exception as e:
        return False, f"Error creating account: {e}"

def check_login(username, password):
    db = get_db()
    if db is None: return False, None, "standard"

    users = db.users
    user_data = users.find_one({'username': username})
    
    if user_data:
        stored_hash = user_data.get('password')
        if stored_hash and bcrypt.checkpw(password.encode('utf-8'), stored_hash):
            # Return Name AND Tier
            return True, user_data.get('name', username), user_data.get('tier', 'standard')
    
    return False, None, "standard"

# --- TIER & QUOTA MANAGEMENT ---

def get_user_tier(username):
    db = get_db()
    if not db: return 'standard'
    user = db.users.find_one({'username': username})
    return user.get('tier', 'standard') if user else 'standard'

def check_quota(username, feature_name):
    """
    Check if user allowed to use feature today.
    Returns: (Allowed: bool, Message: str, UsageCount: int, MaxLimit: int)
    """
    db = get_db()
    if not db: return True, "Offline", 0, 99

    user = db.users.find_one({'username': username})
    if not user: return False, "User not found", 0, 0
    
    tier = user.get('tier', 'standard')
    if tier == 'admin':
        return True, "Admin Access", 0, 999
        
    # --- TIER RULES ---
    # Standard: Scanner, Deep Dive ONLY
    # Pro: All Features
    
    pro_features = ['ai_analysis', 'wealth', 'health']
    
    if tier == 'standard' and feature_name in pro_features:
        return False, "🔒 Upgrade to Pro to use this feature.", 0, 0

    # --- QUOTA LIMITS ---
    LIMIT = 3 # 3 times per day for both Standard and Pro
    
    today_str = date.today().isoformat() # "2024-01-01"
    
    # Path: usage.{date}.{feature}
    usage_doc = db.usage.find_one({'username': username, 'date': today_str})
    current_count = 0
    
    if usage_doc and feature_name in usage_doc:
        current_count = usage_doc[feature_name]
        
    if current_count >= LIMIT:
        return False, f"⚠️ Daily limit reached ({LIMIT}/{LIMIT}). Come back tomorrow!", current_count, LIMIT
        
    return True, "Access Granted", current_count, LIMIT

def increment_quota(username, feature_name):
    """Call this AFTER successfully running a feature."""
    db = get_db()
    if not db: return
    
    # Don't count for admins (optional, but let's track anyway or skip)
    # user = db.users.find_one({'username': username})
    # if user and user.get('tier') == 'admin': return

    today_str = date.today().isoformat()
    
    db.usage.update_one(
        {'username': username, 'date': today_str},
        {'$inc': {feature_name: 1}},
        upsert=True
    )

# --- PORTFOLIO HISTORY ---

def save_portfolio(username, portfolio_data):
    """Save generated AI portfolio."""
    db = get_db()
    if not db: return False
    
    doc = {
        'username': username,
        'created_at': datetime.now(),
        'data': portfolio_data,
        'name': f"Portfolio {date.today().isoformat()}"
    }
    db.portfolios.insert_one(doc)
    return True

def get_user_portfolios(username):
    """Fetch user's saved portfolios."""
    db = get_db()
    if not db: return []
    
    cursor = db.portfolios.find({'username': username}).sort('created_at', -1)
    return list(cursor)
