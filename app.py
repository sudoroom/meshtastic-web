from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import meshtastic
import meshtastic.serial_interface
from pubsub import pub

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

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
        # Send to all connected web clients
        socketio.emit('new_message', message_data)
        print(f"Received: {message_data}")

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect(auth=None):
    global interface
    if interface is None:
        # Subscribe to message receive events
        pub.subscribe(on_receive, "meshtastic.receive")
        # Connect to device (auto-finds USB device)
        interface = meshtastic.serial_interface.SerialInterface()
    print('Client connected')

@socketio.on('send_message')
def handle_send(data):
    """Send a message through meshtastic"""
    text = data.get('text', '')
    if interface and text:
        interface.sendText(text)
        emit('message_sent', {'status': 'success'})
    else:
        emit('message_sent', {'status': 'error'})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)