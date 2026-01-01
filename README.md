# Meshtastic Web Interface

A real-time web interface for sending and receiving Meshtastic messages through a USB-connected node.

## Features

- 📡 **Real-time messaging** - View incoming messages instantly
- 💬 **Direct Messages & Channel Chat** - Send messages to any configured channel or DM specific nodes
- 📻 **Multi-channel support** - Automatically detects and lists all configured channels from your device
- 🛰️ **Auto-updating node list** - See all visible nodes with their short names, long names, and IDs
- 🌐 **Network accessible** - Access from any device on your network
- 🔊 **Text-to-speech** - Optional audio announcements for DMs and non-MediumFast channels (using gspeak)
- 🎨 **Modern two-column UI** - Clean sidebar navigation to switch between channels and DMs
- 💾 **SQLite message history** - All messages persist across page refreshes
- 🏷️ **Smart message display** - Channel names, timestamps, and sender info with hover tooltips
- 🔍 **Filtered conversations** - View only messages from the selected channel or DM
- 🎯 **Clean DM organization** - DM sidebar shows only your conversations with other nodes
- 💿 **Persistent node storage** - Node names are saved to database and persist even when nodes go offline
- ⚡ **Optimized database writes** - Change detection prevents unnecessary database writes

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
  - Messages show timestamp, sender name (hover for full details), and text
  - **Channel mode**: Shows only messages from the selected channel
  - **DM mode**: Shows only messages in the conversation with the selected person
  - Message history is saved and loads automatically on page refresh
  - Outgoing messages have a blue left border, incoming DMs have an orange border

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
   - Saves all messages and node information to SQLite database
   - Uses change detection to only save nodes when data actually changes
   - Broadcasts messages to web clients via SocketIO
   - Merges live node data with stored node data for persistent node names

2. **Database (database.py):**
   - Stores message history with: sender, recipient, text, timestamp, channel
   - Stores node information: node number, short name, long name, ID, last seen
   - Automatically creates tables on first run
   - Uses connection timeout (10s) to handle concurrent access
   - Provides queries for recent messages, filtered by DM/channel
   - Tracks node information even when nodes go offline

3. **Frontend (index.html):**
   - Real-time bidirectional communication via Socket.IO
   - Two-column layout with sidebar navigation
   - Mode switching between channels and DMs
   - Filters messages by selected channel or DM conversation
   - Displays sender names with tooltips showing full node details
   - Persists across page refreshes by loading from database