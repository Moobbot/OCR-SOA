import platform
import subprocess
import sys
import os


def install(package_spec, index_url=None, extra_args=None):
    cmd = [sys.executable, "-m", "pip", "install", package_spec]
    if index_url:
        cmd.extend(["--index-url", index_url])
    if extra_args:
        cmd.extend(extra_args)

    print(f"Running: {' '.join(cmd)}")
    subprocess.check_call(cmd)


def main():
    system = platform.system()
    print(f"Detected OS: {system}")

    # Upgrade pip
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])

    # 1. Install PyTorch with CUDA support
    if system == "Windows":
        print("Installing PyTorch for Windows (CUDA 12.1)...")
        # specific command for windows cuda
        install(
            "torch torchvision torchaudio",
            index_url="https://download.pytorch.org/whl/cu121",
        )
    elif system == "Linux":
        print("Installing PyTorch for Linux (CUDA 12.1)...")
        install(
            "torch torchvision torchaudio"
        )  # Linux wheels usually bundle CUDA or use default
    else:
        print("Unsupported OS for auto-GPU setup. Installing standard torch.")
        install("torch torchvision torchaudio")

    # 2. Install requirements from file (excluding torch if possible, or letting pip handle it)
    # We'll just run pip install -r requirements.txt.
    # Since torch is already installed, pip should skip it if version satisfies,
    # or we might need to be careful about requirements.txt content not forcing a non-cuda version.

    if os.path.exists("requirements.txt"):
        print("Installing dependencies from requirements.txt...")
        # We assume requirements.txt has 'torch' but hopefully not pinned to a cpu version
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
        )
    else:
        print("requirements.txt not found!")

    # 3. vLLM specific handling (Experimental on Windows)
    if system == "Windows":
        print("\n[WARNING] vLLM is primarily designed for Linux.")
        print(
            "If 'pip install vllm' failed above, you might need to use WSL2 or wait for official Windows support."
        )
        print(
            "Alternative: specific wheels might be available, but are not handled by this script."
        )

    print("\nSetup complete!")


if __name__ == "__main__":
    main()
