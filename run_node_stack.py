import subprocess
import sys
import threading
import time
import os

def run_fastapi():
    print("Starting FastAPI Backend on port 8000...")
    subprocess.run([sys.executable, "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"])

def run_nextjs():
    print("Starting Next.js Sentinel Frontend on port 3000...")
    frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
    npx_cmd = "npx.cmd" if os.name == "nt" else "npx"
    subprocess.run([npx_cmd, "next", "dev", "-p", "3000"], cwd=frontend_dir)

if __name__ == "__main__":
    t1 = threading.Thread(target=run_fastapi)
    t2 = threading.Thread(target=run_nextjs)
    
    t1.start()
    time.sleep(2)
    t2.start()
    
    try:
        t1.join()
        t2.join()
    except KeyboardInterrupt:
        print("Shutting down services...")
        sys.exit(0)
