#!/bin/bash
# Setup script to create and configure virtual environment

# Don't exit on error immediately - we want to handle venv creation errors gracefully
set +e

echo "=========================================="
echo "Setting up Python virtual environment"
echo "=========================================="

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Get Python version
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo "Python version: $(python3 --version)"

# Check if venv module is available
if ! python3 -m venv --help &> /dev/null; then
    echo ""
    echo "=========================================="
    echo "ERROR: python3-venv package is not installed"
    echo "=========================================="
    echo ""
    echo "The venv module is required to create virtual environments."
    echo "Please install it using one of the following methods:"
    echo ""
    echo "On Debian/Ubuntu:"
    echo "  sudo apt install python3.10-venv"
    echo ""
    echo "On Red Hat/CentOS/Fedora:"
    echo "  sudo yum install python3-venv"
    echo "  # or"
    echo "  sudo dnf install python3-venv"
    echo ""
    echo "On macOS (with Homebrew):"
    echo "  brew install python3"
    echo ""
    echo "After installing, run this script again:"
    echo "  ./setup_venv.sh"
    echo ""
    exit 1
fi

# Re-enable exit on error for the rest of the script
set -e

# Create virtual environment
VENV_DIR="venv"
if [ -d "$VENV_DIR" ]; then
    echo "Virtual environment already exists at $VENV_DIR"
    read -p "Do you want to recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Removing existing virtual environment..."
        rm -rf "$VENV_DIR"
    else
        echo "Using existing virtual environment."
        source "$VENV_DIR/bin/activate"
        echo "Virtual environment activated!"
        echo ""
        echo "To activate manually, run: source $VENV_DIR/bin/activate"
        exit 0
    fi
fi

echo "Creating virtual environment at $VENV_DIR..."

# Try to create venv normally first
if python3 -m venv "$VENV_DIR" 2>/dev/null; then
    echo "Virtual environment created successfully."
elif python3 -m venv --without-pip "$VENV_DIR" 2>/dev/null; then
    echo "Virtual environment created without pip (ensurepip not available)."
    echo "Installing pip manually..."
    
    # Download get-pip.py and install pip
    if command -v curl &> /dev/null; then
        curl -sSL https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
    elif command -v wget &> /dev/null; then
        wget -q https://bootstrap.pypa.io/get-pip.py -O /tmp/get-pip.py
    else
        echo "Error: Neither curl nor wget is available. Cannot install pip."
        echo "Please install curl or wget, or install python3-pip package:"
        echo "  sudo apt install python3-pip"
        exit 1
    fi
    
    "$VENV_DIR/bin/python3" /tmp/get-pip.py --quiet
    rm -f /tmp/get-pip.py
    echo "Pip installed successfully."
else
    echo ""
    echo "=========================================="
    echo "ERROR: Failed to create virtual environment"
    echo "=========================================="
    echo ""
    echo "The venv module may not be properly configured."
    echo "Please try installing python3-venv:"
    echo ""
    echo "On Debian/Ubuntu:"
    echo "  sudo apt update"
    echo "  sudo apt install python3-venv"
    echo ""
    echo "Or install python3-pip and use virtualenv:"
    echo "  sudo apt install python3-pip"
    echo "  pip3 install virtualenv"
    echo "  virtualenv venv"
    echo ""
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install requirements
if [ -f "requirements.txt" ]; then
    echo "Installing packages from requirements.txt..."
    pip install -r requirements.txt
    echo ""
    echo "=========================================="
    echo "Setup complete!"
    echo "=========================================="
    echo ""
    echo "Virtual environment is now active."
    echo ""
    echo "To activate the virtual environment in the future, run:"
    echo "  source $VENV_DIR/bin/activate"
    echo ""
    echo "To deactivate, run:"
    echo "  deactivate"
    echo ""
    echo "To use with Jupyter notebooks, run:"
    echo "  python -m ipykernel install --user --name=venv --display-name 'Python (venv)'"
    echo ""
else
    echo "Warning: requirements.txt not found. Skipping package installation."
fi
