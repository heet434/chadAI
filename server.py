import socket
import threading
import os
import argparse

class Server(threading.Thread):
    
	def __init__(self, host, port):
		super().__init__()
		self.connections = []
		self.host = host
		self.port = port
  
	def run(self):
		
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
		sock.bind((self.host, self.port))
  
		sock.listen(1)
		print('Listening at', sock.getsockname())
  
		while True:
      
			# Accepting new connections
			sc, sockname = sock.accept()
			print(f"Accepting a new connection from {sc.getpeername()} to {sc.getsockname()}")

			# Creating a new thread for the new connection
			server_socket = ServerSocket(sc, sockname, self)

			# Starting the new thread
			server_socket.start()

			# Add thread to active connections
			self.connections.append(server_socket)
			print('Ready to receive messages from', sc.getpeername())

 
	def broadcast(self, message, source):
		for connection in self.connections:
			# Send to all connected clients except the source client
			if connection.sockname != source:
				connection.send(message)
    
	def remove_connection(self, connection):
		self.connections.remove(connection)
  
class ServerSocket(threading.Thread):
  
	def __init__(self, sc, sockname, server):
		super().__init__()
		self.sc = sc
		self.sockname = sockname
		self.server = server
	
	def run(self):
		while True:
			message = self.sc.recv(1024).decode('utf-8')
			if message:
				print(f"Received {message} from {self.sockname}")
				self.server.broadcast(message, self.sockname)
			else:
				# Client has closed the socket, exit the thread
				print(f"Connection from {self.sockname} has been closed")
				self.sc.close()
				self.server.remove_connection(self)
				return
	
	def send(self, message):
		self.sc.sendall(message.encode('ascii')) 
  
def exit(server):
	
	while True:
		i = input('')
		if i == 'q':
			print('Closing all connections...')
			for connection in server.connections:
				connection.sc.close()
			print('Shutting down the server...')
			os._exit(0)
   
if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Chatroom server')
	parser.add_argument('host', help='Interface the server listens at')
	parser.add_argument('-p', metavar='PORT', type=int, default=1060,
						help='TCP port (default 1060)')
	args = parser.parse_args()
	# Create and start the server
	server = Server(args.host, args.p)
	server.start()
	
	exit = threading.Thread(target = exit, args=(server,))
	exit.start()