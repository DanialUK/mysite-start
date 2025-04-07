import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Determine which settings to import based on the environment
if os.getenv('DJANGO_ENV') == 'production':
    from .production import *
else:
    from .development import * 