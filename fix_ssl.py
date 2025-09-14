#!/usr/bin/env python3
"""Fix SSL certificate issues on macOS."""

import ssl
import certifi
import os

print("🔧 Fixing SSL certificates...")

# Install certificates for Python
try:
    import subprocess
    import sys
    
    # Try to install certificates
    result = subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "certifi"], 
                          capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Updated certifi package")
    
    # Set SSL cert path
    os.environ['SSL_CERT_FILE'] = certifi.where()
    os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
    
    print(f"✅ SSL certificates configured")
    print(f"   Certificate path: {certifi.where()}")
    
    # Test SSL
    import urllib.request
    urllib.request.urlopen('https://slack.com')
    print("✅ SSL connection test successful")
    
except Exception as e:
    print(f"⚠️  Manual fix needed: {e}")
    print("\nTry running:")
    print("pip install --upgrade certifi")
    print("/Applications/Python*/Install\\ Certificates.command")
