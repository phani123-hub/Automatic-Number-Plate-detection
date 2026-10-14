"""
Flask Application Entry Point
Run the Flask backend server
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app_factory import create_app

if __name__ == '__main__':
    app = create_app()
    
    # Development mode
    app.run(
        debug=True,
        host='0.0.0.0',
        port=5000,
        use_reloader=True
    )
    
    # For production, use:
    # gunicorn -w 4 -b 0.0.0.0:5000 run_flask:app
