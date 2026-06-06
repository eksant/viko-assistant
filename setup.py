import subprocess
import sys
import shutil

def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)

def main():
    uv = shutil.which("uv")

    if uv:
        print("Using uv...")
        run([uv, "pip", "install", "-r", "requirements.txt"])
    else:
        print("uv not found, falling back to pip. Install uv for faster installs: https://docs.astral.sh/uv/")
        run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

    print("Installing Playwright browsers...")
    run([sys.executable, "-m", "playwright", "install"])

    print("\nSetup complete. Run 'python viko.py' to start.")

if __name__ == "__main__":
    main()
