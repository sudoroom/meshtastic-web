# Meshtastic Web Interface

A real-time web interface for sending and receiving Meshtastic messages through a USB-connected node.

## Features

- 📡 View incoming messages in real-time
- 💬 Send messages to the MediumFast channel or DM specific nodes
- 🛰️ Auto-updating list of visible nodes
- 🌐 Access from any device on your network
- 🔊 Text-to-speech for DMs and non-MediumFast channels (using gspeak)
- 📑 Tabbed interface separating All Messages, Channel, and Direct Messages

## Setup

### Prerequisites

- Python 3.11+ (Python 3.11.2+ works great)
- USB-connected Meshtastic device
- Permission to access serial devices (see below)
- (Optional) `gspeak` for text-to-speech announcements

### Installation

1. Clone this repository
   ```bash
   git clone <your-repo-url>
   cd meshtastic-web
   ```

2. Create and activate virtual environment
   ```bash
   python3 -m venv meshtastic-web
   source meshtastic-web/bin/activate
   ```

3. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

4. Set up serial port permissions
   ```bash
   # Add your user to the dialout group
   sudo usermod -a -G dialout $USER

   # Log out and log back in for this to take effect
   # Or reboot your system
   ```

5. (Optional) Set up text-to-speech with gspeak
   ```bash
   # Install dependencies
   sudo apt-get install mpg123
   pip install gtts-cli

   # Create the gspeak script
   sudo nano /usr/bin/gspeak
   ```

   Add this content to `/usr/bin/gspeak`:
   ```bash
   #!/bin/bash
   ALLPARMS="$@"
   gtts-cli "$ALLPARMS" | mpg123 -
   ```

   Make it executable:
   ```bash
   sudo chmod +x /usr/bin/gspeak
   ```

   Test it:
   ```bash
   gspeak "Hello from Meshtastic"
   ```

### Running

```bash
# Activate the virtual environment
source meshtastic-web/bin/activate

# Run the app
python app.py
```

The interface will be available at `http://localhost:5000` or `http://<your-ip>:5000`

## Usage

- Select recipient from dropdown (channel or specific node)
- Type your message and hit Send or press Enter
- Incoming messages appear automatically in real-time
- Use tabs to filter messages: All Messages, Channel (MediumFast), or Direct Messages
- If `gspeak` is installed, DMs and other channels will be read aloud (MediumFast channel is silent due to high traffic)

## Recreating the Virtual Environment

If you need to recreate the virtual environment from scratch:

```bash
python3 -m venv meshtastic-web
source meshtastic-web/bin/activate
pip install -r requirements.txt
```

## Troubleshooting

**Permission denied on /dev/ttyACM0**
- Make sure you're in the `dialout` group: `groups | grep dialout`
- Log out and back in after adding yourself to the group

**No nodes showing in dropdown**
- Wait a minute for your device to hear from other nodes on the mesh
- The list auto-refreshes every 30 seconds

## Project Structure

```
meshtastic-web/
├── app.py                  # Flask backend
├── templates/
│   └── index.html         # Web interface
├── requirements.txt       # Python dependencies
└── README.md             # This file
```