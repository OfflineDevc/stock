import streamlit as st
import pymongo
import bcrypt
import time
from datetime import datetime, date
import re

# --- DATABASE CONNECTION ---
@st.cache_resource
def init_connection():
    try:
        if 'MONGO_URI' not in st.secrets:
            # st.error("Missing 'MONGO_URI' in .streamlit/secrets.toml")
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

def validate_email(email):
    # Basic Regex for Email
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(pattern, email) is not None

def validate_password(password):
    """
    >8 chars, Upper, Lower, Number, Special Char
    """
    if len(password) < 8: return False
    if not re.search(r"[A-Z]", password): return False
    if not re.search(r"[a-z]", password): return False
    if not re.search(r"\d", password): return False
    if not re.search(r"[ !@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", password): return False
    return True

def sign_up(username, password, name):
    db = get_db()
    if db is None: return False, "Database connection failed."

    # 1. Validate Email
    if not validate_email(username):
        return False, "Invalid Email Format. Please use a valid email (e.g. user@gmail.com)."

    # 2. Validate Password
    if not validate_password(password):
        return False, "Weak Password. Must be >8 chars, include Upper, Lower, Number, and Special Char (@#$%...)."

    users = db.users
    if users.find_one({'username': username}):
        return False, "Email already exists."
    
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

# --- ACCOUNT MANAGEMENT ---

def change_password(username, old_pass, new_pass):
    db = get_db()
    if db is None: return False, "Database Error"
    
    user = db.users.find_one({'username': username})
    if not user: return False, "User not found"
    
    # Verify Old
    if not bcrypt.checkpw(old_pass.encode('utf-8'), user['password']):
        return False, "Incorrect old password"
        
    # Set New
    new_hashed = bcrypt.hashpw(new_pass.encode('utf-8'), bcrypt.gensalt())
    db.users.update_one({'username': username}, {'$set': {'password': new_hashed}})
    return True, "Password updated successfully!"

# --- HISTORY MANAGEMENT ---

def save_health_check(username, input_df, analysis_text, gpa, details=None):
    """Save HealthDeck Analysis Result"""
    db = get_db()
    if db is None: return False
    
    doc = {
        'username': username,
        'created_at': datetime.now(),
        'portfolio_json': input_df.to_dict(orient='records'), # Save input portfolio
        'analysis': analysis_text,
        'gpa': gpa,
        'details': details if details else [],
        'name': f"Health Check {date.today().isoformat()}"
    }
    db.health_history.insert_one(doc)
    return True

def get_health_history(username):
    db = get_db()
    if db is None: return []
    return list(db.health_history.find({'username': username}).sort('created_at', -1))

# --- TIER & QUOTA MANAGEMENT ---

def get_user_tier(username):
    db = get_db()
    if db is None: return 'standard'
    user = db.users.find_one({'username': username})
    return user.get('tier', 'standard') if user else 'standard'

def check_quota(username, feature_name):
    """
    Check if user allowed to use feature today.
    Returns: (Allowed: bool, Message: str, UsageCount: int, MaxLimit: int)
    """
    db = get_db()
    if db is None: return True, "Offline", 0, 99

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
        return False, "Upgrade to Pro to use this feature.", 0, 0

    # --- QUOTA LIMITS ---
    LIMIT = 3 # 3 times per day for both Standard and Pro
    
    today_str = date.today().isoformat() # "2024-01-01"
    
    # Path: usage.{date}.{feature}
    usage_doc = db.usage.find_one({'username': username, 'date': today_str})
    current_count = 0
    
    if usage_doc and feature_name in usage_doc:
        current_count = usage_doc[feature_name]
        
    if current_count >= LIMIT:
        return False, f"Daily limit reached ({LIMIT}/{LIMIT}). Come back tomorrow!", current_count, LIMIT
        
    return True, "Access Granted", current_count, LIMIT

def increment_quota(username, feature_name):
    """Call this AFTER successfully running a feature."""
    db = get_db()
    if db is None: return
    
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
    if db is None: return False
    
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
    if db is None: return []
    
    cursor = db.portfolios.find({'username': username}).sort('created_at', -1)
    return list(cursor)
