#!/bin/bash
# Simple build script for Unix-like systems (macOS, Linux)

echo "🚀 Building Genea HTR GUI Standalone Application"
echo "================================================"

# Make sure we're in the right directory
if [ ! -f "genea_htr_gui.py" ]; then
    echo "❌ Error: genea_htr_gui.py not found in current directory"
    echo "Please run this script from the directory containing your application files."
    exit 1
fi

# Run the Python build script
python3 build_standalone.py

echo ""
echo "Build script completed. Check the output above for results."
