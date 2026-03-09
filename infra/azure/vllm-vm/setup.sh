#!/bin/bash
set -euo pipefail

# Inclusify vLLM Azure VM Setup
# ==============================
#
# This script provisions an Azure T4 GPU VM for vLLM inference.
# Run from your local machine with Azure CLI authenticated.
#
# Prerequisites:
#   - Azure CLI installed and logged in (az login)
#   - GPU quota approved for Standard_NC4as_T4_v3 in your region
#   - SSH key at ~/.ssh/id_rsa.pub (or customize SSH_KEY_PATH)
#
# Usage:
#   ./infra/azure/vllm-vm/setup.sh
#
# The script is idempotent - safe to run multiple times.

# ============================================================================
# Configuration
# ============================================================================

# Resource names
RESOURCE_GROUP="${RESOURCE_GROUP:-inclusify-llm-rg}"
LOCATION="${LOCATION:-eastus}"
VM_NAME="${VM_NAME:-inclusify-vllm}"
VNET_NAME="${VNET_NAME:-inclusify-vnet}"
SUBNET_NAME="${SUBNET_NAME:-llm-subnet}"
NSG_NAME="${NSG_NAME:-inclusify-vllm-nsg}"
NIC_NAME="${NIC_NAME:-inclusify-vllm-nic}"
PUBLIC_IP_NAME="${PUBLIC_IP_NAME:-inclusify-vllm-ip}"

# VM configuration
VM_SIZE="Standard_NC4as_T4_v3"  # 4 vCPU, 28GB RAM, T4 GPU (16GB VRAM)
VM_IMAGE="Canonical:0001-com-ubuntu-server-jammy:22_04-lts-gen2:latest"
ADMIN_USER="azureuser"
SSH_KEY_PATH="${SSH_KEY_PATH:-$HOME/.ssh/id_rsa.pub}"

# OS disk size (default 128GB for model storage)
OS_DISK_SIZE=128

# ============================================================================
# Helper Functions
# ============================================================================

log() {
    echo "[$(date '+%H:%M:%S')] $1"
}

check_exists() {
    local resource_type=$1
    local name=$2
    local group=$3

    case $resource_type in
        "group")
            az group show --name "$name" &>/dev/null
            ;;
        "vm")
            az vm show --resource-group "$group" --name "$name" &>/dev/null
            ;;
        "vnet")
            az network vnet show --resource-group "$group" --name "$name" &>/dev/null
            ;;
        "subnet")
            az network vnet subnet show --resource-group "$group" --vnet-name "$VNET_NAME" --name "$name" &>/dev/null
            ;;
        "nsg")
            az network nsg show --resource-group "$group" --name "$name" &>/dev/null
            ;;
        "public-ip")
            az network public-ip show --resource-group "$group" --name "$name" &>/dev/null
            ;;
        "nic")
            az network nic show --resource-group "$group" --name "$name" &>/dev/null
            ;;
    esac
}

# ============================================================================
# Pre-flight Checks
# ============================================================================

log "=== Inclusify vLLM VM Setup ==="
log "Resource Group: $RESOURCE_GROUP"
log "Location: $LOCATION"
log "VM Size: $VM_SIZE"
log ""

# Check Azure CLI
if ! command -v az &>/dev/null; then
    echo "Error: Azure CLI not found. Install from https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Check logged in
if ! az account show &>/dev/null; then
    echo "Error: Not logged in to Azure. Run 'az login' first."
    exit 1
fi

# Check SSH key
if [ ! -f "$SSH_KEY_PATH" ]; then
    echo "Error: SSH public key not found at $SSH_KEY_PATH"
    echo "Generate one with: ssh-keygen -t rsa -b 4096"
    exit 1
fi

# Confirm before proceeding
echo ""
echo "This will create/update the following resources:"
echo "  - Resource Group: $RESOURCE_GROUP"
echo "  - VNet: $VNET_NAME"
echo "  - Subnet: $SUBNET_NAME"
echo "  - NSG: $NSG_NAME"
echo "  - VM: $VM_NAME ($VM_SIZE)"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

# ============================================================================
# Step 1: Resource Group
# ============================================================================

log "[1/8] Creating resource group..."
if check_exists "group" "$RESOURCE_GROUP" ""; then
    log "  Resource group already exists, skipping"
else
    az group create \
        --name "$RESOURCE_GROUP" \
        --location "$LOCATION" \
        --output none
    log "  Created resource group: $RESOURCE_GROUP"
fi

# ============================================================================
# Step 2: Virtual Network
# ============================================================================

log "[2/8] Creating virtual network..."
if check_exists "vnet" "$VNET_NAME" "$RESOURCE_GROUP"; then
    log "  VNet already exists, skipping"
else
    az network vnet create \
        --resource-group "$RESOURCE_GROUP" \
        --name "$VNET_NAME" \
        --address-prefix "10.0.0.0/16" \
        --output none
    log "  Created VNet: $VNET_NAME"
fi

# ============================================================================
# Step 3: Subnet
# ============================================================================

log "[3/8] Creating subnet..."
if check_exists "subnet" "$SUBNET_NAME" "$RESOURCE_GROUP"; then
    log "  Subnet already exists, skipping"
else
    az network vnet subnet create \
        --resource-group "$RESOURCE_GROUP" \
        --vnet-name "$VNET_NAME" \
        --name "$SUBNET_NAME" \
        --address-prefix "10.0.1.0/24" \
        --output none
    log "  Created subnet: $SUBNET_NAME"
fi

# ============================================================================
# Step 4: Network Security Group
# ============================================================================

log "[4/8] Creating network security group..."
if check_exists "nsg" "$NSG_NAME" "$RESOURCE_GROUP"; then
    log "  NSG already exists, skipping"
else
    az network nsg create \
        --resource-group "$RESOURCE_GROUP" \
        --name "$NSG_NAME" \
        --output none
    log "  Created NSG: $NSG_NAME"
fi

# Add SSH rule (allow from anywhere for initial setup, restrict later)
log "  Adding SSH rule..."
az network nsg rule create \
    --resource-group "$RESOURCE_GROUP" \
    --nsg-name "$NSG_NAME" \
    --name "AllowSSH" \
    --priority 100 \
    --access Allow \
    --direction Inbound \
    --protocol Tcp \
    --source-address-prefixes "*" \
    --source-port-ranges "*" \
    --destination-address-prefixes "*" \
    --destination-port-ranges 22 \
    --output none 2>/dev/null || log "  SSH rule already exists"

# Deny all other inbound traffic
log "  Adding deny-all rule..."
az network nsg rule create \
    --resource-group "$RESOURCE_GROUP" \
    --nsg-name "$NSG_NAME" \
    --name "DenyAllInbound" \
    --priority 4096 \
    --access Deny \
    --direction Inbound \
    --protocol "*" \
    --source-address-prefixes "*" \
    --source-port-ranges "*" \
    --destination-address-prefixes "*" \
    --destination-port-ranges "*" \
    --output none 2>/dev/null || log "  Deny-all rule already exists"

# ============================================================================
# Step 5: Public IP (for SSH access during setup)
# ============================================================================

log "[5/8] Creating public IP..."
if check_exists "public-ip" "$PUBLIC_IP_NAME" "$RESOURCE_GROUP"; then
    log "  Public IP already exists, skipping"
else
    az network public-ip create \
        --resource-group "$RESOURCE_GROUP" \
        --name "$PUBLIC_IP_NAME" \
        --sku Standard \
        --allocation-method Static \
        --output none
    log "  Created public IP: $PUBLIC_IP_NAME"
fi

# ============================================================================
# Step 6: Network Interface
# ============================================================================

log "[6/8] Creating network interface..."
if check_exists "nic" "$NIC_NAME" "$RESOURCE_GROUP"; then
    log "  NIC already exists, skipping"
else
    az network nic create \
        --resource-group "$RESOURCE_GROUP" \
        --name "$NIC_NAME" \
        --vnet-name "$VNET_NAME" \
        --subnet "$SUBNET_NAME" \
        --network-security-group "$NSG_NAME" \
        --public-ip-address "$PUBLIC_IP_NAME" \
        --output none
    log "  Created NIC: $NIC_NAME"
fi

# ============================================================================
# Step 7: Create VM
# ============================================================================

log "[7/8] Creating VM (this takes 5-10 minutes)..."
if check_exists "vm" "$VM_NAME" "$RESOURCE_GROUP"; then
    log "  VM already exists, skipping creation"
else
    az vm create \
        --resource-group "$RESOURCE_GROUP" \
        --name "$VM_NAME" \
        --nics "$NIC_NAME" \
        --image "$VM_IMAGE" \
        --size "$VM_SIZE" \
        --admin-username "$ADMIN_USER" \
        --ssh-key-values "@$SSH_KEY_PATH" \
        --os-disk-size-gb "$OS_DISK_SIZE" \
        --output none
    log "  Created VM: $VM_NAME"
fi

# ============================================================================
# Step 8: VM Setup Script
# ============================================================================

log "[8/8] Running VM setup script..."

# Get the public IP address
PUBLIC_IP=$(az network public-ip show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$PUBLIC_IP_NAME" \
    --query ipAddress \
    --output tsv)

# Get the private IP address
PRIVATE_IP=$(az network nic show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$NIC_NAME" \
    --query ipConfigurations[0].privateIPAddress \
    --output tsv)

log "  Public IP: $PUBLIC_IP"
log "  Private IP: $PRIVATE_IP"

# Create the VM setup script
VM_SETUP_SCRIPT=$(cat << 'VMSETUP'
#!/bin/bash
set -euo pipefail

echo "=== Inclusify vLLM VM Setup ==="

# Update system
echo "[1/7] Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install NVIDIA drivers
echo "[2/7] Installing NVIDIA drivers..."
sudo apt-get install -y ubuntu-drivers-common
sudo ubuntu-drivers autoinstall

# Install CUDA toolkit
echo "[3/7] Installing CUDA toolkit..."
wget -q https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt-get update
sudo apt-get install -y cuda-toolkit-12-4
rm cuda-keyring_1.1-1_all.deb

# Add CUDA to PATH
echo 'export PATH=/usr/local/cuda-12.4/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda-12.4/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
export PATH=/usr/local/cuda-12.4/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda-12.4/lib64:$LD_LIBRARY_PATH

# Install Python 3.11
echo "[4/7] Installing Python 3.11..."
sudo apt-get install -y python3.11 python3.11-venv python3-pip

# Create models directory
echo "[5/7] Creating directories..."
mkdir -p ~/models
mkdir -p ~/inclusify

# Clone repository
echo "[6/7] Cloning Inclusify repository..."
if [ ! -d ~/inclusify/.git ]; then
    git clone https://github.com/shahafwieder/inclusify.git ~/inclusify
else
    cd ~/inclusify && git pull
fi

# Create Python virtual environment and install dependencies
echo "[7/7] Setting up Python environment..."
cd ~/inclusify
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r infra/azure/vllm-vm/requirements.txt

echo ""
echo "=== VM Setup Complete ==="
echo "Next steps:"
echo "  1. Reboot the VM: sudo reboot"
echo "  2. After reboot, run quantization: python ~/inclusify/infra/azure/vllm-vm/quantize_model.py"
echo "  3. Copy vllm.service: sudo cp ~/inclusify/infra/azure/vllm-vm/vllm.service /etc/systemd/system/"
echo "  4. Enable service: sudo systemctl daemon-reload && sudo systemctl enable vllm"
echo "  5. Start service: sudo systemctl start vllm"
echo ""
VMSETUP
)

# Run the setup script on the VM
log "  Connecting to VM and running setup..."
log "  (This may take 15-30 minutes for driver installation)"
echo ""

# Copy setup script to VM and run it
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=60 "${ADMIN_USER}@${PUBLIC_IP}" << 'REMOTE_SCRIPT'
#!/bin/bash
set -euo pipefail

echo "=== Inclusify vLLM VM Setup ==="

# Update system
echo "[1/7] Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install NVIDIA drivers
echo "[2/7] Installing NVIDIA drivers..."
sudo apt-get install -y ubuntu-drivers-common
sudo ubuntu-drivers autoinstall

# Install CUDA toolkit
echo "[3/7] Installing CUDA toolkit..."
wget -q https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt-get update
sudo apt-get install -y cuda-toolkit-12-4
rm cuda-keyring_1.1-1_all.deb

# Add CUDA to PATH
echo 'export PATH=/usr/local/cuda-12.4/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda-12.4/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
export PATH=/usr/local/cuda-12.4/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda-12.4/lib64:$LD_LIBRARY_PATH

# Install Python 3.11
echo "[4/7] Installing Python 3.11..."
sudo apt-get install -y python3.11 python3.11-venv python3-pip

# Create models directory
echo "[5/7] Creating directories..."
mkdir -p ~/models
mkdir -p ~/inclusify

echo ""
echo "=== Initial VM Setup Complete ==="
echo ""
echo "Next steps (manual):"
echo "  1. Reboot the VM: sudo reboot"
echo "  2. After reboot, clone repo and run quantization"
echo ""
REMOTE_SCRIPT

# ============================================================================
# Summary
# ============================================================================

echo ""
log "=== Setup Complete ==="
echo ""
echo "VM Details:"
echo "  Name: $VM_NAME"
echo "  Size: $VM_SIZE"
echo "  Public IP: $PUBLIC_IP"
echo "  Private IP: $PRIVATE_IP"
echo ""
echo "SSH Access:"
echo "  ssh ${ADMIN_USER}@${PUBLIC_IP}"
echo ""
echo "Next Steps (on the VM):"
echo "  1. Reboot: sudo reboot"
echo "  2. After reboot, SSH back in"
echo "  3. Clone repo: git clone https://github.com/shahafwieder/inclusify.git ~/inclusify"
echo "  4. Run quantization: cd ~/inclusify && python3.11 -m venv .venv && source .venv/bin/activate && pip install -r infra/azure/vllm-vm/requirements.txt && python infra/azure/vllm-vm/quantize_model.py"
echo "  5. Install service: sudo cp infra/azure/vllm-vm/vllm.service /etc/systemd/system/ && sudo systemctl daemon-reload && sudo systemctl enable vllm && sudo systemctl start vllm"
echo "  6. Verify: curl http://localhost:8001/v1/models"
echo ""
echo "Backend Connection (from within VNet):"
echo "  VLLM_URL=http://${PRIVATE_IP}:8001"
echo ""
