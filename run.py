import subprocess
import sys
import threading
import time
import os

def run_fastapi():
    print("Starting FastAPI Backend on port 8000...")
    subprocess.run([sys.executable, "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"])

def run_streamlit():
    print("Starting Streamlit Frontend on port 8501...")
    subprocess.run([sys.executable, "-m", "streamlit", "run", "app/Home.py", "--server.port", "8501", "--server.address", "0.0.0.0"])

if __name__ == "__main__":
    t1 = threading.Thread(target=run_fastapi)
    t2 = threading.Thread(target=run_streamlit)
    
    t1.start()
    # slight delay so backend starts first
    time.sleep(2)
    t2.start()
    
    try:
        t1.join()
        t2.join()
    except KeyboardInterrupt:
        print("Shutting down services...")
        sys.exit(0)
