import streamlit as st
import pymongo
import bcrypt
import time
from datetime import datetime

# --- DATABASE CONNECTION ---
@st.cache_resource
def init_connection():
    try:
        # Check if secret exists
        if 'MONGO_URI' not in st.secrets:
            st.error("🚨 Missing 'MONGO_URI' in .streamlit/secrets.toml")
            return None
            
        return pymongo.MongoClient(st.secrets["MONGO_URI"])
    except Exception as e:
        st.error(f"Failed to connect to DB: {e}")
        return None

def get_db():
    client = init_connection()
    if client:
        return client.stockdeck_db  # Use database named 'stockdeck_db'
    return None

# --- AUTHENTICATION FUNCTIONS ---

def sign_up(username, password, name):
    """Register a new user."""
    db = get_db()
    if db is None: return False, "Database connection failed."

    users = db.users
    
    # Check if user exists
    if users.find_one({'username': username}):
        return False, "Username already exists."
    
    # Hash password
    # bcrypt requires bytes, so encode utf-8
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    new_user = {
        "username": username,
        "password": hashed,  # Store binary hash
        "name": name,
        "created_at": datetime.now(),
        "role": "user"
    }
    
    try:
        users.insert_one(new_user)
        return True, "Account created successfully! Please log in."
    except Exception as e:
        return False, f"Error creating account: {e}"

def check_login(username, password):
    """Verify credentials."""
    db = get_db()
    if db is None: return False, None

    users = db.users
    user_data = users.find_one({'username': username})
    
    if user_data:
        # Verify Password
        stored_hash = user_data['password']
        # If stored as string (legacy), might need encoding, but here we store bytes
        if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
            return True, user_data['name']
    
    return False, None
