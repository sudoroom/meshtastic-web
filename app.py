from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
import meshtastic
import meshtastic.serial_interface
from pubsub import pub
import subprocess
from database import init_database, save_message, get_recent_messages, get_message_count

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize database
init_database()

# Connect to your meshtastic device
interface = None

def on_receive(packet, interface):
    """Called when a message is received"""
    if 'decoded' in packet and 'text' in packet['decoded']:
        message_data = {
            'from': packet['from'],
            'to': packet['to'],
            'text': packet['decoded']['text'],
            'time': packet.get('rxTime', 'unknown')
        }

        # Save to database
        if message_data['time'] != 'unknown':
            channel_index = packet.get('channel', 0)
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

@socketio.on('get_nodes')
def send_node_list():
    """Send list of visible nodes to client"""
    if interface and interface.nodes:
        nodes = []
        for node_id, node in interface.nodes.items():
            # Extract user data into a plain dict for JSON serialization
            user_obj = node.get('user')
            user_data = {}
            if user_obj:
                # user_obj is a dict, so use dict access
                user_data = {
                    'longName': user_obj.get('longName'),
                    'shortName': user_obj.get('shortName'),
                    'id': user_obj.get('id')
                }

            node_info = {
                'id': node_id,
                'num': node['num'],
                'user': user_data
            }
            nodes.append(node_info)
        emit('node_list', {'nodes': nodes})
        print(f"Sent {len(nodes)} nodes to client")
    else:
        emit('node_list', {'nodes': []})

@socketio.on('send_message')
def handle_send(data):
    """Send a message through meshtastic"""
    print(f"Received send_message event with data: {data}")
    text = data.get('text', '')
    recipient = data.get('recipient', 'channel')  # 'channel' or node number
    print(f"Text to send: '{text}' to {recipient}")
    print(f"Interface status: {interface}")
    if interface and text:
        print(f"Attempting to send: '{text}' to {recipient}")
        try:
            # Get our own node number for the database
            my_node_num = interface.myInfo.my_node_num if interface.myInfo else 0

            if recipient == 'channel':
                # Send to default channel (MediumFast)
                interface.sendText(text, channelIndex=0)
                print("Message sent to channel successfully!")
                # Save to database
                import time
                save_message(
                    from_node=my_node_num,
                    to_node=4294967295,  # Broadcast
                    text=text,
                    timestamp=int(time.time()),
                    channel_index=0
                )
            else:
                # Send DM to specific node
                interface.sendText(text, destinationId=int(recipient))
                print(f"DM sent to node {recipient} successfully!")
                # Save to database
                import time
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