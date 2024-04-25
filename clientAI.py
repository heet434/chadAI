import socket
import threading
import os
import argparse
import sys
import tkinter as tk
import string
import utils as lora_utils
import mlx.core as mx
from mlx.utils import tree_flatten, tree_unflatten
from models.lora import LoRALinear


## Load model and tokenizer
model, tokenizer, _ = lora_utils.load('./mlx_model')
adapter = './whatsapp.npz'
temp = 0.7

delay = 2000 # Delay in milliseconds for generating response

def generate(model, prompt, tokenizer, max_len):

    model.load_weights(adapter, strict=False)
    prompt = mx.array(tokenizer.encode(prompt))

    tokens = []
    for token, n in zip(
        lora_utils.generate(prompt, model, temp),
        range(max_len),
    ):
        if token == tokenizer.eos_token_id:
            break

        tokens.append(token.item())
    return tokenizer.decode(tokens)

def get_number_of_words(prompt):
    return len(prompt.split())

def generate_response(prompt, output_entry):
    num_tokens = get_number_of_words(prompt) + 20
    response = generate(model, prompt, tokenizer, num_tokens)
    excluded_punctuation = "'\""
    # Determine the index of the first punctuation mark after the prompt
    punctuation_indices = [response.find(punct) for punct in string.punctuation if punct not in excluded_punctuation]
    valid_indices = [idx for idx in punctuation_indices if idx != -1]
    
    if valid_indices:
        # Find the earliest punctuation index after the prompt
        first_punctuation_index = min(valid_indices)
        
        # Include the prompt and text up to the first punctuation mark in the output
        truncated_response = response[:first_punctuation_index + 1]
    else:
        # If no punctuation mark is found, include the entire generated response
        truncated_response = response
        
    #print(type(output_entry))
    
    # Update the generated text in the output text box
    output_entry.config(state=tk.NORMAL)
    output_entry.delete(0, tk.END)  # Clear previous content
    output_entry.insert(tk.END, truncated_response)
    output_entry.config(state=tk.DISABLED)  # Disable editing


def handle_prompt(event, entry, window, messages, username, aiResponse):
    
    recieved_messages = []
    
    start_index = 0
    end_index = 0
    if messages.size() >= 10:
    # Retrieve the last 10 messages
        start_index = messages.size()-10
        end_index = messages.size()  # end_index is exclusive in range, so it's messages.size()
    else:
    # Retrieve all messages (from the last to the first)
        start_index = 0
        end_index = messages.size()  # end_index is exclusive in range, so it's -1 to exclude index 0

    # Use a list comprehension to retrieve messages from the Listbox
    recieved_messages = [messages.get(i) for i in range(start_index, end_index)]
    
    
    prompt = ""
    # set prompt to last 10 messages recieved, if less than 10 messages, set prompt to all messages recieved
    if len(recieved_messages) < 10:
        prompt = "\n".join(recieved_messages)
    else:
        prompt = "\n".join(recieved_messages[-10:])
        
    #print('prompt' + prompt)

    usertext = entry.get().strip()  # Get entire content from Text widget
    if(usertext == ""):
        aiResponse.delete(0, tk.END)
        aiResponse.insert(0, "AI Response")
        return
    prompt = prompt + "\n" + username + ": " + usertext
    #print("Prompt" + prompt)
    if not prompt:
        return
    
    # Cancel any existing after task
    if hasattr(window, 'after_id'):
        window.after_cancel(window.after_id)
    
    # Schedule a new task to generate response after a delay (adjust delay as needed)
    window.after_id = window.after(delay, lambda: generate_response(prompt, aiResponse))
    
def tab_complete(event, textInput, ai_response):
    # Get the text from the ai_response Entry widget
    ai_text = ai_response.get()
    
    # Split the AI response into words
    words = ai_text.split()
    
    if words:  # Check if there are words in the AI response
        first_word = words[0]  # Get the first word
        
        # Get the current text from the textInput Entry widget
        current_text = textInput.get()
        
        # Append the first word of AI response to the current text and insert into textInput
        completed_text = current_text + first_word + " "
        textInput.delete(0, tk.END)  # Clear existing text
        textInput.insert(0, completed_text)  # Insert completed text
    
    # Return 'break' to prevent further default handling of the Tab key
    return 'break'


class Send(threading.Thread):
    
    # Listens for user input and sends it to the server
    
    # sock is the socket object
    # name(str) is the name of the user
  
	def __init__(self, sock, name):
		super().__init__()
		self.sock = sock
		self.name = name

	def run(self):
		# Listens for user input and sends it to the server
		# Typing "Quit" will close the connection and exit the program
  
		while True:
			#print('{}: '.format(self.name), end='')
			sys.stdout.flush()	
			message = sys.stdin.readline()[:-1]

			if message == 'QUIT':
				self.sock.sendall('Server: {} has left the chat.'.format(self.name).encode('utf-8'))
				break
			
			else:
				self.sock.sendall('{}: {}'.format(self.name, message).encode('utf-8'))
		print('\nQuitting...')
		self.sock.close()
		os._exit(0)	
  
class Receive(threading.Thread):
	
    # Listens for incoming messages

    # sock is the socket object
    # name(str) is the name of the user

    def __init__(self, sock, name):
        super().__init__()
        self.sock = sock
        self.name = name
        self.messages = None

    def run(self): 
        # Receives data from the server and prints it to the screen
        while True:
            message = self.sock.recv(1024).decode('utf-8')
            if message:
                if self.messages:
                    self.messages.insert(tk.END, message)
                    #print('hi')
            else:
                # Server has closed the socket, exit the program
                print('\nOh no, we have lost connection to the server!')
                print('\nQuitting...')
                self.sock.close()
                os._exit(0)

class Client:
	
	# Manage the client-server connection and integration of the GUI
	
	def __init__(self, host, port):
		self.host = host
		self.port = port
		self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.name = None
		self.messages = None
  
	def start(self):
		print('Trying to connect to {}:{}...'.format(self.host, self.port))
		self.sock.connect((self.host, self.port))
		print('Successfully connected to {}:{}'.format(self.host, self.port))
		print()
		self.name = input('Your name: ')
		print()
		print('Welcome, {}! Getting ready to send and receive messages...'.format(self.name))
  
		# Create send and receive threads
		send = Send(self.sock, self.name)
		receive = Receive(self.sock, self.name)
  
		# Start send and receive threads
		send.start()
		receive.start()
	
		self.sock.sendall('Server: {} has joined the chat. Say hi!'.format(self.name).encode('utf-8'))
		print("\rAll set! Leave the chatroom anytime by typing 'QUIT'\n")
		#print('{}: '.format(self.name), end = '')

		return receive

	def send(self, textInput):
		# Sends messages to the server
		message = textInput.get()
		textInput.delete(0, tk.END)
		self.messages.insert(tk.END, '{}: {}'.format(self.name, message))
  
		# Type 'QUIT' to leave the chatroom
		if message == 'QUIT':
			self.sock.sendall('Server: {} has left the chat.'.format(self.name).encode('utf-8'))
			print('\nQuitting...')
			self.sock.close()
			os._exit(0)
		else:
			self.sock.sendall('{}: {}'.format(self.name, message).encode('utf-8'))
   

def main(host, port):

    client = Client(host, port)
    receive = client.start()

    # GUI
    window = tk.Tk()
    window.title('Chatroom')

    fromMessage = tk.Frame(master = window)
    scrollBar = tk.Scrollbar(master = fromMessage)
    messages = tk.Listbox(master = fromMessage, yscrollcommand = scrollBar.set)
    scrollBar.pack(side = tk.RIGHT, fill = tk.Y, expand=False)	
    messages.pack(side = tk.LEFT, fill = tk.BOTH, expand=True)

    client.messages = messages
    receive.messages = messages

    fromMessage.grid(row = 0, column = 0, columnspan = 2, sticky = "nsew")
    fromEntry = tk.Entry(master = window)
    textInput = tk.Entry(master = fromEntry)
    aiResponse = tk.Entry(master = fromEntry)
    
    
    output_entry = tk.Text(window, height=10, width=50)
    aiResponse.pack(fill = tk.BOTH, expand = True)
    aiResponse.insert(0, "AI Response")
    # aiResponse should not be editable
    aiResponse.config(state=tk.DISABLED)

    textInput.pack(fill = tk.BOTH, expand = True)
    textInput.bind("<KeyRelease>", lambda event: handle_prompt(event, textInput, window, messages, client.name, aiResponse))
    textInput.bind("<Tab>", lambda event: tab_complete(event, textInput, aiResponse))
    textInput.bind("<Return>", lambda x: client.send(textInput))
    textInput.insert(0, "Type your message here.")

    btnSend = tk.Button(
        master = window,
        text = "Send",
        command = lambda: client.send(textInput)
    )
    fromEntry.grid(row = 1, column = 0, padx = 10,  sticky = "ew")
    btnSend.grid(row = 1, column = 1, pady=10, sticky = "ew")

    window.rowconfigure(0, minsize = 500, weight = 1)
    window.rowconfigure(1, minsize = 50, weight = 0)
    window.columnconfigure(0, minsize = 500, weight = 1)
    window.columnconfigure(1, minsize = 200, weight = 0)

    window.mainloop()

 
if __name__ == '__main__':
	parser = argparse.ArgumentParser(description = 'Chatroom Client')
	parser.add_argument('host', help = 'Interface the server listens at')
	parser.add_argument('-p', metavar = 'PORT', type = int, default = 1060, help = 'TCP port (default 1060)')
	args = parser.parse_args()
	main(args.host, args.p)