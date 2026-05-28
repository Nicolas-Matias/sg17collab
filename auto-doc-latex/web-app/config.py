"""
Configuration file for ITU-T Report Generator Web Application
"""

import os
from datetime import timedelta

# ============================================
# Path Configuration
# ============================================

# Base directory of the web app
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Parent directory (auto-doc-latex/)
PARENT_DIR = os.path.dirname(BASE_DIR)

# Scripts directory
SCRIPTS_DIR = os.path.join(PARENT_DIR, 'scripts-new')

# Template directories
WP_TEMPLATE_DIR = os.path.join(PARENT_DIR, 'wp_doc_template')
QUESTION_TEMPLATE_DIR = os.path.join(PARENT_DIR, 'question_doc_template')

# Temporary files directory
TEMP_DIR = os.path.join(BASE_DIR, 'temp')

# Static and templates directories
STATIC_DIR = os.path.join(BASE_DIR, 'static')
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')

# ============================================
# Flask Configuration
# ============================================

class Config:
    """Base configuration"""

    # Secret key for session management
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # Debug mode
    DEBUG = True

    # Max upload size (for CSV work programme files) - Arbitrary value
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    # Temporary files cleanup age - Arbitrary value
    TEMP_FILE_MAX_AGE = timedelta(hours=1)

    # Allowed extensions for uploads
    ALLOWED_EXTENSIONS = {'csv', 'txt'}

    # Report generation timeout (seconds) - Arbitrary value
    GENERATION_TIMEOUT = 300  # 5 minutes

    # Templates auto-reload
    TEMPLATES_AUTO_RELOAD = True


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.environ.get('SECRET_KEY')


# ============================================
# Active Configuration
# ============================================

config_name = os.environ.get('FLASK_ENV', 'development')

if config_name == 'production':
    active_config = ProductionConfig
else:
    active_config = DevelopmentConfig


# ============================================
# Utility Functions
# ============================================

def ensure_directories():
    """Create required directories if they don't exist"""
    os.makedirs(TEMP_DIR, exist_ok=True)
    os.makedirs(STATIC_DIR, exist_ok=True)
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    os.makedirs(os.path.join(STATIC_DIR, 'css'), exist_ok=True)
    os.makedirs(os.path.join(STATIC_DIR, 'js'), exist_ok=True)
    os.makedirs(os.path.join(STATIC_DIR, 'images'), exist_ok=True)


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS
