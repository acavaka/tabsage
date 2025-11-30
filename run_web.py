#!/usr/bin/env python3
"""
Launch web server for TabSage knowledge graph visualization
"""

from services.web.app import run_server

if __name__ == "__main__":
    import os
    
    # Configure Firestore (long-term memory)
    # Use Firestore if available, otherwise fallback to in-memory
    kg_provider = os.getenv("KG_PROVIDER", "firestore")  # Default: firestore
    
    if kg_provider == "firestore":
        # Check for credentials
        if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            # Try to use gcloud auth
            try:
                import subprocess
                result = subprocess.run(
                    ["gcloud", "auth", "application-default", "print-access-token"],
                    capture_output=True,
                    timeout=2
                )
                if result.returncode == 0:
                    print("✅ Using gcloud application-default credentials")
                else:
                    print("⚠️  GOOGLE_APPLICATION_CREDENTIALS not set")
                    print("   Using gcloud auth or fallback to in-memory")
            except Exception:
                print("⚠️  Firestore credentials not found, will use fallback")
        else:
            print(f"✅ GOOGLE_APPLICATION_CREDENTIALS: {os.getenv('GOOGLE_APPLICATION_CREDENTIALS')}")
        
        os.environ["KG_PROVIDER"] = "firestore"
        print(f"📊 KG Provider: Firestore (long-term memory)")
    else:
        os.environ["KG_PROVIDER"] = kg_provider
        print(f"📊 KG Provider: {kg_provider}")
    
    # Attempt observability initialization (optional)
    try:
        from observability.setup import initialize_observability
        initialize_observability(metrics_port=8001)
    except ImportError:
        # Observability is not required for web server
        pass
    
    # Launch web server
    print("=" * 60)
    print("🌐 Starting TabSage Web Server")
    print("=" * 60)
    print()
    print("📊 Available pages:")
    print("   • http://localhost:5001/ - Standard graph visualization")
    print("   • http://localhost:5001/mindmap - Mindmap visualization")
    print("   • http://localhost:5001/api/graph - Graph data API")
    print("   • http://localhost:5001/api/stats - Statistics API")
    print()
    print("🚀 Server starting...")
    print()
    
    # Use port 5001, as 5000 may be occupied by AirPlay
    run_server(host='127.0.0.1', port=5001, debug=True)
