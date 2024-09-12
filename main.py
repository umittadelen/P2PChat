import socket
import threading
import json
import time

# Configuration
BUFFER_SIZE = 1024
DISCOVERY_PORT = 6000
DEFAULT_PORT = 0  # Let the OS choose an available port

# Global variables
public_ip = None
server_port = None
connections = {}
peers = {}

def get_public_ip():
    """Get the public IP of the local machine."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))  # Connect to a public DNS server
        ip = s.getsockname()[0]
    except:
        ip = '0.0.0.0'  # Fallback if unable to get public IP
    finally:
        s.close()
    return ip

def handle_client(connection, peer_ip, peer_port):
    """Handle incoming messages from peers."""
    print(f"[NEW CONNECTION] {peer_ip}:{peer_port} connected.")
    while True:
        try:
            message = connection.recv(BUFFER_SIZE).decode('utf-8')
            if message:
                print(f"[{peer_ip}:{peer_port}] {message}")
                broadcast(message, peer_ip, peer_port)
            else:
                break
        except:
            break

    # Remove the connection if it breaks
    connection.close()
    del connections[(peer_ip, peer_port)]
    print(f"[DISCONNECTED] {peer_ip}:{peer_port} disconnected.")
    reconnect_to_peers()

def broadcast(message, sender_ip, sender_port):
    """Send the message to all peers except the one who sent it."""
    for (peer_ip, peer_port), conn in connections.items():
        if (peer_ip, peer_port) != (sender_ip, sender_port):
            try:
                conn.send(f"{sender_ip}:{sender_port}: {message}".encode('utf-8'))
            except:
                conn.close()
                del connections[(peer_ip, peer_port)]

def start_listening():
    """Start the server to listen for incoming connections."""
    global server_port
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('', DEFAULT_PORT))  # Bind to a free port
    server_socket.listen()
    server_port = server_socket.getsockname()[1]  # Retrieve the assigned port
    print(f"[LISTENING] Peer {public_ip} is listening on port {server_port}")

    while True:
        connection, (peer_ip, peer_port) = server_socket.accept()
        connections[(peer_ip, peer_port)] = connection

        # Send our peer list to the new peer
        peer_list = {f"{ip}:{port}": (ip, port) for (ip, port), _ in connections.items()}
        connection.send(json.dumps(peer_list).encode('utf-8'))

        thread = threading.Thread(target=handle_client, args=(connection, peer_ip, peer_port))
        thread.start()
        print(f"[ACTIVE CONNECTIONS] {len(connections)}")

def connect_to_peer(peer_ip, peer_port):
    """Connect to another peer using its IP and port."""
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_socket.connect((peer_ip, peer_port))
        
        # Send our peer info (IP and port)
        client_socket.send(json.dumps({'ip': public_ip, 'port': server_port}).encode('utf-8'))

        # Receive the peer list from the connected peer
        peer_list = json.loads(client_socket.recv(BUFFER_SIZE).decode('utf-8'))
        for ip_port in peer_list.values():
            if ip_port != (public_ip, server_port) and ip_port not in connections:
                connections[ip_port] = client_socket
                thread = threading.Thread(target=handle_client, args=(client_socket, ip_port[0], ip_port[1]))
                thread.start()

        # Add the new peer to our list and notify others
        connections[(public_ip, server_port)] = client_socket
    except Exception as e:
        print(f"[CONNECT ERROR] {e}")

def reconnect_to_peers():
    """Try to reconnect to peers if the connection is lost."""
    for (peer_ip, peer_port) in list(peers.keys()):
        if (peer_ip, peer_port) not in connections:
            connect_to_peer(peer_ip, peer_port)

def broadcast_presence():
    """Broadcast our presence to discoverable peers."""
    try:
        discovery_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        discovery_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        while True:
            peer_info = {
                'ip': public_ip,
                'port': server_port
            }
            discovery_socket.sendto(json.dumps(peer_info).encode('utf-8'), ('<broadcast>', DISCOVERY_PORT))
            time.sleep(10)  # Broadcast every 10 seconds
    except Exception as e:
        print(f"[BROADCAST ERROR] {e}")

def manual_connect():
    """Prompt the user to connect to a peer or start as a server."""
    while True:
        host_ip = input("Enter the IP of an active peer (or press Enter to start as server): ")
        if not host_ip:
            print(f"[NO HOST IP] Starting as server...")
            start_listening()
            break
        else:
            try:
                peer_port = int(input("Enter the port of the active peer: "))
                connect_to_peer(host_ip, peer_port)
                break
            except Exception as e:
                print(f"[CONNECTION ERROR] {e}. Retrying...")

def send_message(message):
    """Send a message to all connected peers."""
    for conn in connections.values():
        try:
            conn.send(f"{public_ip}:{server_port}: {message}".encode('utf-8'))
        except:
            conn.close()
            for ip_port, c in list(connections.items()):
                if c == conn:
                    del connections[ip_port]

# Get the public IP of the local machine
public_ip = get_public_ip()

# Start the server thread
server_thread = threading.Thread(target=start_listening)
server_thread.start()

# Start broadcasting our presence
broadcast_thread = threading.Thread(target=broadcast_presence)
broadcast_thread.start()

# Start discovering peers
manual_connect()

# Command interface
while True:
    command = input()
    if command.startswith("send"):
        _, message = command.split(maxsplit=1)
        send_message(message)
    elif command == "exit":
        break
