from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
import meshtastic
import meshtastic.serial_interface
from pubsub import pub
import subprocess
from database import init_database, save_message, get_recent_messages, get_message_count, upsert_node, get_all_nodes

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize database
init_database()

# Connect to your meshtastic device
interface = None

def on_receive(packet, interface):
    """Called when a message is received"""
    if 'decoded' in packet and 'text' in packet['decoded']:
        channel_index = packet.get('channel', 0)
        message_data = {
            'from': packet['from'],
            'to': packet['to'],
            'text': packet['decoded']['text'],
            'time': packet.get('rxTime', 'unknown'),
            'channel': channel_index
        }

        # Save sender's node info if available
        from_node_num = message_data['from']
        if interface and interface.nodes and from_node_num in interface.nodes:
            node = interface.nodes[from_node_num]
            user_obj = node.get('user')
            if user_obj:
                upsert_node(
                    from_node_num,
                    user_obj.get('shortName'),
                    user_obj.get('longName'),
                    user_obj.get('id')
                )

        # Save to database
        if message_data['time'] != 'unknown':
            save_message(
                from_node=message_data['from'],
                to_node=message_data['to'],
                text=message_data['text'],
                timestamp=message_data['time'],
                channel_index=channel_index
            )

        # Send to all connected web clients
        socketio.emit('new_message', message_data)
        print(f"Received: {message_data}")

        # Speak the message aloud using gspeak (Google TTS)
        # Skip MediumFast channel (channelIndex 0 / broadcast to 0xffffffff)
        # Only speak DMs and other channels
        is_broadcast = message_data['to'] == 4294967295  # 0xffffffff
        channel_index = packet.get('channel', 0)

        # Don't speak if it's the MediumFast channel (channel 0 broadcast)
        if not (is_broadcast and channel_index == 0):
            try:
                text_to_speak = message_data['text']
                subprocess.run(['gspeak', text_to_speak], check=False)
            except Exception as e:
                print(f"Error speaking message: {e}")

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect(auth=None):
    global interface
    if interface is None:
        print("Initializing meshtastic interface...")
        # Subscribe to message receive events
        pub.subscribe(on_receive, "meshtastic.receive")
        # Connect to device (auto-finds USB device)
        try:
            interface = meshtastic.serial_interface.SerialInterface()
            print(f"Meshtastic interface connected: {interface}")
        except Exception as e:
            print(f"Error connecting to meshtastic: {e}")
    print('Client connected')
    # Send initial node list
    if interface:
        send_node_list()
        send_channel_list()
    # Send message history
    send_message_history()
    # Send our own node number
    send_my_node_number()

@socketio.on('get_my_node_number')
def send_my_node_number():
    """Send our own node number to the client"""
    try:
        if interface and interface.myInfo:
            my_node_num = interface.myInfo.my_node_num
            emit('my_node_number', {'node_number': my_node_num})
            print(f"Sent my node number: {my_node_num}")
        else:
            emit('my_node_number', {'node_number': None})
    except Exception as e:
        print(f"Error sending node number: {e}")
        emit('my_node_number', {'node_number': None})

@socketio.on('get_message_history')
def send_message_history(limit=100):
    """Send message history to client"""
    try:
        all_messages = get_recent_messages(limit=limit, is_dm=None)
        channel_messages = get_recent_messages(limit=limit, is_dm=False)
        dm_messages = get_recent_messages(limit=limit, is_dm=True)

        # Enrich messages with node information
        for msg in all_messages + channel_messages + dm_messages:
            msg['channel_index'] = msg.get('channel_index', 0)

        emit('message_history', {
            'all': all_messages,
            'channel': channel_messages,
            'dms': dm_messages,
            'total_count': get_message_count()
        })
        print(f"Sent message history: {len(all_messages)} total messages")
    except Exception as e:
        print(f"Error sending message history: {e}")
        emit('message_history', {
            'all': [],
            'channel': [],
            'dms': [],
            'total_count': 0
        })

@socketio.on('get_channels')
def send_channel_list():
    """Send list of configured channels to client"""
    if interface and interface.localNode:
        channels = []
        try:
            # Get channel configuration from local node
            channel_config = interface.localNode.channels
            for i, channel in enumerate(channel_config):
                if channel and hasattr(channel, 'settings'):
                    settings = channel.settings
                    channel_info = {
                        'index': i,
                        'name': settings.name if settings.name else f'Channel {i}',
                        'role': str(channel.role) if hasattr(channel, 'role') else 'DISABLED'
                    }
                    # Only include enabled channels
                    if channel_info['role'] != 'DISABLED':
                        channels.append(channel_info)
            emit('channel_list', {'channels': channels})
            print(f"Sent {len(channels)} channels to client: {channels}")
        except Exception as e:
            print(f"Error getting channels: {e}")
            emit('channel_list', {'channels': []})
    else:
        emit('channel_list', {'channels': []})

@socketio.on('get_nodes')
def send_node_list():
    """Send list of visible nodes to client, merging with stored nodes from database"""
    try:
        # Start with nodes from database (includes offline nodes)
        stored_nodes = get_all_nodes()

        # Update with currently visible nodes from interface
        # Create a copy to avoid "dictionary changed size during iteration" error
        if interface and interface.nodes:
            nodes_snapshot = dict(interface.nodes.items())
            # Batch process nodes to reduce database writes
            nodes_to_save = []
            for node_id, node in nodes_snapshot.items():
                # Extract user data
                user_obj = node.get('user')
                if user_obj:
                    node_num = node['num']
                    short_name = user_obj.get('shortName')
                    long_name = user_obj.get('longName')
                    node_id_str = user_obj.get('id')

                    nodes_to_save.append((node_num, short_name, long_name, node_id_str))

                    # Update stored_nodes with current info
                    stored_nodes[node_num] = {
                        'shortName': short_name,
                        'longName': long_name,
                        'id': node_id_str
                    }

            # Save nodes only if they're new or changed
            for node_data in nodes_to_save:
                node_num, short_name, long_name, node_id_str = node_data
                try:
                    # Check if this node is new or has changed
                    existing = stored_nodes.get(node_num)
                    if not existing or (
                        existing.get('shortName') != short_name or
                        existing.get('longName') != long_name or
                        existing.get('id') != node_id_str
                    ):
                        upsert_node(node_num, short_name, long_name, node_id_str)
                except Exception as e:
                    print(f"Error saving node {node_num}: {e}")

        # Convert to list format for sending to client
        nodes = []
        for node_num, node_data in stored_nodes.items():
            node_info = {
                'num': node_num,
                'user': {
                    'shortName': node_data.get('shortName'),
                    'longName': node_data.get('longName'),
                    'id': node_data.get('id')
                }
            }
            nodes.append(node_info)

        emit('node_list', {'nodes': nodes})
        print(f"Sent {len(nodes)} nodes to client (including stored nodes)")
    except Exception as e:
        print(f"Error in send_node_list: {e}")
        import traceback
        traceback.print_exc()
        # Send empty list on error
        emit('node_list', {'nodes': []})

@socketio.on('send_message')
def handle_send(data):
    """Send a message through meshtastic"""
    print(f"Received send_message event with data: {data}")
    text = data.get('text', '')
    recipient = data.get('recipient', 'channel:0')  # 'channel:X' or node number
    print(f"Text to send: '{text}' to {recipient}")
    print(f"Interface status: {interface}")
    if interface and text:
        print(f"Attempting to send: '{text}' to {recipient}")
        try:
            # Get our own node number for the database
            my_node_num = interface.myInfo.my_node_num if interface.myInfo else 0
            import time

            # Convert recipient to string if it's an integer
            recipient_str = str(recipient) if isinstance(recipient, int) else recipient

            if recipient_str.startswith('channel:'):
                # Send to specific channel
                channel_index = int(recipient_str.split(':')[1])
                interface.sendText(text, channelIndex=channel_index)
                print(f"Message sent to channel {channel_index} successfully!")
                # Save to database
                save_message(
                    from_node=my_node_num,
                    to_node=4294967295,  # Broadcast
                    text=text,
                    timestamp=int(time.time()),
                    channel_index=channel_index
                )
            else:
                # Send DM to specific node
                interface.sendText(text, destinationId=int(recipient))
                print(f"DM sent to node {recipient} successfully!")
                # Save to database
                save_message(
                    from_node=my_node_num,
                    to_node=int(recipient),
                    text=text,
                    timestamp=int(time.time()),
                    channel_index=0
                )

            emit('message_sent', {'status': 'success'})
        except Exception as e:
            print(f"Error sending message: {e}")
            emit('message_sent', {'status': 'error', 'message': str(e)})
    else:
        print(f"Cannot send - interface: {interface}, text: '{text}'")
        emit('message_sent', {'status': 'error'})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)