import socket
import threading
import uuid

# Global set to keep track of received messages
received_messages = set()

# Function to handle incoming messages from peers
def handle_peer_connection(peer_socket):
    while True:
        try:
            message = peer_socket.recv(1024).decode()
            if message:
                message_id, content = message.split(":", 1)

                if message_id not in received_messages:
                    received_messages.add(message_id)
                    print(f"[RECEIVED] {content}")

                    # Broadcast the message to all peers (except the one it came from)
                    broadcast_message(message, peer_socket)
        except:
            break
    peer_socket.close()

# Function to broadcast a message to all connected peers
def broadcast_message(message, exclude_socket=None):
    for peer in peers:
        if peer != exclude_socket:
            try:
                peer.sendall(message.encode())
            except:
                peer.close()
                peers.remove(peer)

# Function to listen for incoming connections
def listen_for_peers(host, port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen()

    print(f"[LISTENING] on {host}:{port}")

    while True:
        peer_socket, peer_address = server_socket.accept()
        peers.append(peer_socket)
        print(f"[CONNECTED] {peer_address}")

        threading.Thread(target=handle_peer_connection, args=(peer_socket,)).start()

# Function to connect to a peer
def connect_to_peer(peer_host, peer_port):
    peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    peer_socket.connect((peer_host, peer_port))
    peers.append(peer_socket)

    print(f"[CONNECTED TO PEER] {peer_host}:{peer_port}")

    threading.Thread(target=handle_peer_connection, args=(peer_socket,)).start()

# Function to send a message
def send_message():
    while True:
        message_content = input("")
        message_id = str(uuid.uuid4())
        message = f"{message_id}:{message_content}"
        received_messages.add(message_id)
        broadcast_message(message)

# Main function
def main():
    host = 'localhost'  # Set this to your local IP if needed
    port = int(input("Enter your port: "))

    # Start the peer listener
    threading.Thread(target=listen_for_peers, args=(host, port)).start()

    while True:
        action = input("Enter 'connect' to connect to a peer or 'send' to send a message: ")
        if action == "connect":
            peer_host = input("Enter peer host: ")
            peer_port = int(input("Enter peer port: "))
            connect_to_peer(peer_host, peer_port)
        elif action == "send":
            threading.Thread(target=send_message).start()

if __name__ == "__main__":
    peers = []
    main()
