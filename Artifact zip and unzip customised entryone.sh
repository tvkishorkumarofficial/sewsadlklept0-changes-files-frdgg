#!/bin/bash

# Configuration Flags (modify these as needed)
SETUP_SESSION_DATA=true  # Set to false to skip session data setup
CUSTOM_RUN=true         # true for fixed runs, false for infinite loop
CUSTOM_LOOP_COUNT=15    # Number of cycles when CUSTOM_RUN=true

# Function to install required packages
install_packages() {
    echo "┌─────────────────────────────────────┐"
    echo "│    Installing Required Packages    │"
    echo "└─────────────────────────────────────┘"
    
    # Update package lists first
    if ! sudo apt-get update; then
        echo "❌ Failed to update package lists!"
        exit 1
    fi
    
    # Critical packages that MUST be installed
    CRITICAL_PKGS=("curl" "wget" "zip" "unzip" "jq" "python3-pip" "xvfb")
    
    for pkg in "${CRITICAL_PKGS[@]}"; do
        if ! dpkg -l | grep -qw "^ii  $pkg"; then
            echo "🔧 Installing $pkg..."
            if ! sudo apt-get install -y $pkg; then
                echo "❌ Failed to install $pkg"
                exit 1
            fi
            # Double verification
            if ! dpkg -l | grep -qw "^ii  $pkg"; then
                echo "❌ $pkg still not installed after attempt!"
                exit 1
            fi
            echo "✅ $pkg successfully installed"
        else
            echo "✔️  $pkg already installed"
        fi
    done
    
    # Special verification for zip/unzip
    echo "🔍 Verifying zip/unzip binaries..."
    if ! command -v zip >/dev/null || ! command -v unzip >/dev/null; then
        echo "⚠️  zip/unzip commands missing, reinstalling..."
        sudo apt-get install --reinstall -y zip unzip
        if ! command -v zip >/dev/null || ! command -v unzip >/dev/null; then
            echo "❌ Critical: zip/unzip still not working!"
            exit 1
        fi
    fi
}

# Function to install Python dependencies
install_python_dependencies() {
    echo "┌─────────────────────────────────────┐"
    echo "│  Installing Python Dependencies    │"
    echo "└─────────────────────────────────────┘"
    
    if [ -f "requirements.txt" ]; then
        if command -v pip &> /dev/null; then
            pip install -r requirements.txt
        elif command -v pip3 &> /dev/null; then
            pip3 install -r requirements.txt
        else
            echo "❌ pip/pip3 not found!"
            exit 1
        fi
    else
        echo "⚠️  requirements.txt not found (skipping)"
    fi
}

# Function to kill all related processes
kill_related_processes() {
    echo "🛑 Stopping related processes..."
    pkill -f "python /app/main.py" || true
    pkill -f chrome || true
    pkill -f undetected_chromedriver || true
}

# Function to display IP and system information
display_ip_info() {
    echo "┌─────────────────────────────────────┐"
    echo "│      System Information            │"
    echo "└─────────────────────────────────────┘"
    
    IP_INFO=$(curl -s ipinfo.io)
    IP=$(echo "$IP_INFO" | jq -r '.ip')
    ISP=$(echo "$IP_INFO" | jq -r '.org')
    COUNTRY=$(echo "$IP_INFO" | jq -r '.country')
    REGION=$(echo "$IP_INFO" | jq -r '.region')
    CITY=$(echo "$IP_INFO" | jq -r '.city')
    HOSTNAME=$(hostname)
    
    echo "🌐 Hostname: $HOSTNAME"
    echo "📡 IP Address: $IP"
    echo "🏢 ISP: $ISP"
    echo "🌍 Country: $COUNTRY"
    echo "📍 Region: $REGION"
    echo "🏙️ City: $CITY"
}

# Function to setup session data (now optional)
setup_session_data() {
    echo "┌─────────────────────────────────────┐"
    echo "│    Setting Up Session Data         │"
    echo "└─────────────────────────────────────┘"
    
    # Create /app if it doesn't exist
    mkdir -p /app
    
    echo "📥 Downloading session data..."
    if ! curl -L -o /app/partial_session_data.zip "https://tvkkdata.tvkishorkumardata.workers.dev/download.aspx?file=8qKxnSNKFaledlfUzlgYGn99et%2FRFQul%2BQWjRtZ0143r3I6rlpa4UpA9OdUDMn7K&expiry=vhiabH3uNL0iuKsqwa%2B2Dg%3D%3D&mac=caef46210585537c58884754afc5a9d9797bed94118021f7b8561746ca6be65e"; then
        echo "❌ Download failed!"
        exit 1
    fi
    
    echo "🔒 Setting permissions (600)..."
    chmod 600 /app/partial_session_data.zip
    
    echo "📦 Extracting files..."
    if ! unzip -o /app/partial_session_data.zip -d /app/; then
        echo "❌ First unzip failed!"
        exit 1
    fi
    
    if [ -f "/app/partial_sessions.zip" ]; then
        echo "🔍 Found nested zip, extracting..."
        if ! unzip -o /app/partial_sessions.zip -d /app/; then
            echo "❌ Second unzip failed!"
            exit 1
        fi
    fi
    
    echo "🗃️ Organizing session files..."
    mkdir -p /app/sessions
    if [ -d "/app/app/sessions" ]; then
        mv /app/app/sessions/* /app/sessions/
    fi
    
    echo "✅ Session data ready at /app/sessions"
    ls -lh /app/sessions
}

# Main Execution Flow
echo "🚀 Starting Script Execution"

# 1. FIRST install all dependencies
install_packages

# 2. Install Python dependencies
install_python_dependencies

# 3. Setup environment
echo "⚙️ Setting up environment..."
export DISPLAY=:99
export DBUS_SESSION_BUS_ADDRESS=/dev/null
rm -f /tmp/.X99-lock

# 4. Display system info
display_ip_info

# 5. Start virtual display
echo "🖥️ Starting virtual display..."
Xvfb $DISPLAY -screen 0 1280x800x16 -nolisten tcp &
sleep 5

# 6. Conditionally setup session data
if [ "$SETUP_SESSION_DATA" = true ]; then
    setup_session_data
else
    echo "⏭️ Skipping session data setup as per configuration"
fi

# 7. Cleanup any existing processes
kill_related_processes
sleep 5

echo "┌─────────────────────────────────────┐"
echo "│    Starting Main Application       │"
echo "└─────────────────────────────────────┘"

if [ "$CUSTOM_RUN" = true ]; then
    for i in $(seq 1 $CUSTOM_LOOP_COUNT); do
        echo "🔄 Executing cycle $i/$CUSTOM_LOOP_COUNT..."
        kill_related_processes
        python /app/main.py -cv 127 -v -g IN --proxy socks5://14a7dad21f5c3:85d09469d0@45.143.10.209:12324
        echo "⏳ Cycle completed. Waiting 5 seconds..."
        sleep 5
    done
    echo "✅ All $CUSTOM_LOOP_COUNT cycles completed!"
else
    echo "♾️ Starting infinite loop..."
    while true; do
        kill_related_processes
        python /app/main.py -cv 127 -v -g IN --proxy socks5://14a7dad21f5c3:85d09469d0@45.143.10.209:12324
        echo "⏳ Script completed. Restarting in 5 seconds..."
        sleep 5
    done
fi

# Final cleanup
kill_related_processes
echo "🎉 Script execution finished successfully!"
exit 0
