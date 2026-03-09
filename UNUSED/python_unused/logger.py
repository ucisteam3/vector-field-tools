"""
Centralized logging system for the application.
Set DEBUG_MODE = False to hide all debug logs.
"""

# Global debug flag - Set to False to hide all debug logs
DEBUG_MODE = False

def log_debug(message):
    """Print debug messages only if DEBUG_MODE is enabled"""
    if DEBUG_MODE:
        print(message)

def log_info(message):
    """Always print info messages (important user-facing information)"""
    print(message)

def log_success(message):
    """Always print success messages"""
    print(message)

def log_warning(message):
    """Always print warning messages"""
    print(message)

def log_error(message):
    """Always print error messages"""
    print(message)
