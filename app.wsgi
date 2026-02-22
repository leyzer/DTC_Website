#!/usr/bin/python3
"""
WSGI entry point for HelioHost deployment
"""
import os
import sys

# Add the parent directory to the path so imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the Flask app
from server import app as application
