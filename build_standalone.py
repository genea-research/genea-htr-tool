#!/usr/bin/env python3
"""
Build script for creating a standalone executable of the Genea HTR GUI application.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{description}...")
    print(f"Running: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("[SUCCESS] Command completed!")
        if result.stdout:
            print(f"Output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] {e}")
        if e.stdout:
            print(f"Stdout: {e.stdout}")
        if e.stderr:
            print(f"Stderr: {e.stderr}")
        return False

def check_dependencies():
    """Check if all required dependencies are installed."""
    print("Checking dependencies...")
    
    # Map package names to their import names (required dependencies)
    required_package_imports = {
        'openai': 'openai',
        'Pillow': 'PIL',
        'reportlab': 'reportlab',
        'tkinterdnd2': 'tkinterdnd2',
        'requests': 'requests',
        'PyMuPDF': 'fitz',  # PyMuPDF imports as 'fitz'
        'pyinstaller==6.9.0': 'PyInstaller'
    }
    
    # Optional dependencies (for different AI providers)
    optional_package_imports = {
        'anthropic': 'anthropic',
        'google-generativeai': 'google.generativeai'
    }
    
    missing_required = []
    missing_optional = []
    
    # Check required dependencies
    for package, import_name in required_package_imports.items():
        try:
            __import__(import_name)
            print(f"[OK] {package} is installed")
        except ImportError:
            missing_required.append(package)
            print(f"[MISSING] {package} is missing (REQUIRED)")
    
    # Check optional dependencies
    for package, import_name in optional_package_imports.items():
        try:
            __import__(import_name)
            print(f"[OK] {package} is installed (optional)")
        except ImportError:
            missing_optional.append(package)
            print(f"[INFO] {package} is missing (optional - needed for specific AI providers)")
    
    if missing_required:
        print(f"\n[ERROR] Missing required packages: {', '.join(missing_required)}")
        print("Please install them with: pip install " + " ".join(missing_required))
        return False
    
    if missing_optional:
        print(f"\n[INFO] Missing optional packages: {', '.join(missing_optional)}")
        print("These are only needed if you plan to use specific AI providers.")
        print("You can install them with: pip install " + " ".join(missing_optional))
    
    print("[SUCCESS] All required dependencies are installed!")
    return True

def clean_build_directories():
    """Clean previous build directories."""
    print("\nCleaning previous build directories...")
    
    dirs_to_clean = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"[REMOVED] {dir_name}")
        else:
            print(f"[INFO] {dir_name} doesn't exist, skipping")

def check_required_files():
    """Check if required files exist."""
    print("\nChecking required files...")
    
    required_files = [
        'genea_htr_gui.py',
        'genea_htr.py',
        'genea_htr_gui.spec'
    ]
    
    optional_files = [
        'htr-app-header.png',
        'htr_settings.json',
        'README_GUI.md',
        'README.md'
    ]
    
    missing_required = []
    for file_name in required_files:
        if os.path.exists(file_name):
            print(f"[OK] {file_name} found")
        else:
            missing_required.append(file_name)
            print(f"[MISSING] {file_name} missing")
    
    for file_name in optional_files:
        if os.path.exists(file_name):
            print(f"[OK] {file_name} found (optional)")
        else:
            print(f"[INFO] {file_name} not found (optional)")
    
    if missing_required:
        print(f"\n[ERROR] Missing required files: {', '.join(missing_required)}")
        return False
    
    return True

def build_executable():
    """Build the standalone executable using PyInstaller."""
    print("\nBuilding standalone executable...")
    
    # Use the spec file for building
    cmd = [sys.executable, '-m', 'PyInstaller', 'genea_htr_gui.spec', '--clean']
    
    return run_command(cmd, "Building with PyInstaller")

def show_results():
    """Show the build results."""
    print("\nBuild Results:")
    
    if sys.platform == 'darwin':  # macOS
        app_path = Path('dist/GeneaHTR.app')
        
        if app_path.exists():
            print(f"[SUCCESS] macOS App Bundle created: {app_path}")
            print(f"   Size: {get_directory_size(app_path):.1f} MB")
            print(f"   Ready for distribution - users can drag to Applications folder")
        else:
            print("[ERROR] App bundle not found")
    else:
        exe_path = Path('dist/GeneaHTR.exe' if sys.platform == 'win32' else 'dist/GeneaHTR')
        
        if exe_path.exists():
            print(f"[SUCCESS] Executable created: {exe_path}")
            print(f"   Size: {get_file_size(exe_path):.1f} MB")
    
    dist_path = Path('dist')
    if dist_path.exists():
        print(f"\nDistribution folder: {dist_path.absolute()}")
        print(f"   Contains: GeneaHTR.app (main application)")

def get_file_size(file_path):
    """Get file size in MB."""
    return os.path.getsize(file_path) / (1024 * 1024)

def get_directory_size(dir_path):
    """Get directory size in MB."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(dir_path):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            if os.path.exists(file_path):
                total_size += os.path.getsize(file_path)
    return total_size / (1024 * 1024)

def main():
    """Main build process."""
    print("Genea HTR GUI - Standalone Build Script")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists('genea_htr_gui.py'):
        print("[ERROR] genea_htr_gui.py not found in current directory")
        print("Please run this script from the directory containing your application files.")
        sys.exit(1)
    
    # Step 1: Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Step 2: Check required files
    if not check_required_files():
        sys.exit(1)
    
    # Step 3: Clean previous builds
    clean_build_directories()
    
    # Step 4: Build executable
    if not build_executable():
        print("\n[ERROR] Build failed!")
        sys.exit(1)
    
    # Step 5: Show results
    show_results()
    
    print("\n[SUCCESS] Build completed successfully!")
    print("\nNext steps:")
    print("1. Test the executable in the 'dist' folder")
    print("2. The executable should work on any similar system without Python installed")
    print("3. You can distribute the entire 'dist' folder or just the executable")
    
    if sys.platform == 'darwin':
        print("4. On macOS, you can drag the .app bundle to Applications folder")

if __name__ == "__main__":
    main()
