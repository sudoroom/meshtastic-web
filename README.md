# Meshtastic Web Interface

A real-time web interface for sending and receiving Meshtastic messages through a USB-connected node.

## Features

- 📡 View incoming messages in real-time
- 💬 Send messages to any configured channel or DM specific nodes
- 📻 Multi-channel support - automatically detects and lists all configured channels
- 🛰️ Auto-updating list of visible nodes
- 🌐 Access from any device on your network
- 🔊 Text-to-speech for DMs and non-MediumFast channels (using gspeak)
- 🎨 Two-column UI with sidebar navigation for channels and DMs
- 💾 SQLite message history - messages persist across page refreshes
- 🏷️ Channel names displayed in messages for easy identification

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

- **Interface Layout:**
  - Click "📡 Channels" or "💬 DMs" buttons at the top to switch modes
  - Sidebar shows available channels or DM conversations
  - Click a sidebar item to view that conversation
  - Messages appear in the main chat area on the right

- **Sending Messages:**
  - Select a channel or DM from the sidebar
  - Type your message and hit Send or press Enter
  - Messages appear immediately in the chat area

- **Viewing Messages:**
  - Incoming messages appear automatically in real-time
  - Messages show timestamp, sender name (with tooltip for full details), and text
  - Channel mode: Shows only messages from the selected channel
  - DM mode: Shows only messages to/from the selected person
  - Message history is saved and loads automatically on page refresh

- **Text-to-Speech:**
  - If `gspeak` is installed, DMs and non-MediumFast channels will be read aloud
  - MediumFast channel (channel 0) is silent due to high traffic

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

**No channels showing in sidebar**
- Wait a moment for the interface to connect to your device
- Check that your Meshtastic device has channels configured
- Check the browser console and Flask logs for errors

**No DM conversations showing**
- DM conversations only appear after you've sent or received at least one DM
- Switch to DMs mode and the sidebar will show all your conversations
- The list updates automatically when new DMs arrive

**Messages not persisting**
- Check that the database file `meshtastic_messages.db` is being created
- The database is automatically created in the project directory
- Database files are excluded from git (they contain personal messages)

## Project Structure

```
meshtastic-web/
├── app.py                      # Flask backend with SocketIO
├── database.py                 # SQLite database operations
├── templates/
│   └── index.html             # Web interface
├── requirements.txt           # Python dependencies
├── meshtastic_messages.db     # SQLite database (auto-created, gitignored)
└── README.md                  # This file
```

## How It Works

1. **Backend (app.py):**
   - Connects to Meshtastic device via USB serial
   - Subscribes to incoming messages via pubsub
   - Fetches channel configuration and node list from device
   - Saves all messages to SQLite database
   - Broadcasts messages to web clients via SocketIO

2. **Database (database.py):**
   - Stores message history with: sender, recipient, text, timestamp, channel
   - Automatically creates tables on first run
   - Provides queries for recent messages, filtered by DM/channel

3. **Frontend (index.html):**
   - Real-time bidirectional communication via Socket.IO
   - Two-column layout with sidebar navigation
   - Mode switching between channels and DMs
   - Filters messages by selected channel or DM conversation
   - Displays sender names with tooltips showing full node details
   - Persists across page refreshes by loading from database