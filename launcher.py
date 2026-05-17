"""
launcher.py — Entry point for the PyInstaller .exe bundle.
Streamlit MUST run in the main thread (it needs signal.signal).
The browser is opened from a helper thread once the server is ready.
"""
import os
import socket
import sys
import threading
import time
import webbrowser


BASE = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))


def find_free_port(start: int = 8501) -> int:
    for port in range(start, start + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', port)) != 0:
                return port
    return start


def wait_and_open_browser(url: str, port: int, timeout: int = 30):
    """Wait for the Streamlit server to respond, then open a browser tab."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', port)) == 0:
                webbrowser.open(url)
                print(f"[Laptop Finder] Browser opened: {url}")
                return
        time.sleep(0.3)
    print(f"[WARN] Server did not respond within {timeout}s. Open manually: {url}")


def main():
    dashboard_path = os.path.join(BASE, "laptop_dashboard.py")

    if not os.path.exists(dashboard_path):
        print(f"[ERROR] File not found: {dashboard_path}")
        input("Press Enter to exit...")
        sys.exit(1)

    # Working directory next to the .exe — SQLite and caches write here
    exe_dir = os.path.dirname(
        sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)
    )
    os.chdir(exe_dir)

    port = find_free_port(8501)
    url  = f"http://localhost:{port}"

    print(f"[Laptop Finder] Starting on {url} ...")

    # Open browser from a helper thread
    t = threading.Thread(target=wait_and_open_browser, args=(url, port), daemon=True)
    t.start()

    # Streamlit runs in the main thread — it blocks execution
    from streamlit.web import cli as stcli
    sys.argv = [
        "streamlit", "run", dashboard_path,
        "--server.port", str(port),
        "--server.headless", "true",
        "--global.developmentMode", "false",
        "--browser.gatherUsageStats", "false",
    ]
    stcli.main()


if __name__ == "__main__":
    main()

