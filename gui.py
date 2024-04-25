import tkinter as tk
import utils as lora_utils
import mlx.core as mx
from mlx.utils import tree_flatten, tree_unflatten
from models.lora import LoRALinear
import string

# Load model and tokenizer
model, tokenizer, _ = lora_utils.load('./mlx_model')
adapter = './whatsapp.npz'
temp = 0.7

delay = 1000 # Delay in milliseconds for generating response

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

def handle_prompt(event):
    prompt = entry.get("1.0", tk.END).strip()  # Get entire content from Text widget
    if not prompt:
        return
    
    # Cancel any existing after task
    if hasattr(window, 'after_id'):
        window.after_cancel(window.after_id)
    
    # Schedule a new task to generate response after a delay (adjust delay as needed)
    window.after_id = window.after(delay, generate_response, prompt)

def generate_response(prompt):
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
    
    # Update the generated text in the output text box
    output_entry.config(state=tk.NORMAL)
    output_entry.delete("1.0", tk.END)  # Clear previous content
    output_entry.insert(tk.END, truncated_response)
    output_entry.config(state=tk.DISABLED)  # Disable editing


def tab_complete(event):
    prompt = entry.get("1.0", tk.END).strip()  # Get entire content from Text widget
    
    # Get the text from the output text box (already generated response)
    generated_text = output_entry.get("1.0", tk.END).strip()

    entry_text = ''
    if not prompt:
        return
    if prompt.endswith('\n'):
        entry_text = generated_text
    else:
        entry_text = " " + generated_text
    
    entry.insert(tk.END, entry_text)
    
    
# Create window
window = tk.Tk()
window.title("Dynamic Prompt Scanner")

# Provide size to window
window.geometry("800x400")  # Set initial window size

# Add text label for prompt entry
tk.Label(window, text="Enter Prompt:", font=("Arial", 14)).pack(pady=10)

# Add larger text box (Text widget) for prompt input
entry = tk.Text(window, width=100, height=5, font=("Arial", 12))  # Adjust width, height, and font
entry.pack(pady=10)

# Add text label for generated text
tk.Label(window, text="Generated Text:", font=("Arial", 14)).pack(pady=10)

# Add output text box (Text widget) for generated text display
output_entry = tk.Text(window, width=100, height=10, font=("Arial", 12), state=tk.DISABLED, wrap=tk.WORD)  # Adjust width, height, font, and disable editing
output_entry.pack(pady=10)

# Bind the handle_prompt function to the Text widget for key release events
entry.bind("<KeyRelease>", handle_prompt)

# Bind the tab_complete function to the Text widget for Tab key press events
entry.bind("<Tab>", tab_complete)

# Start the main event loop
window.mainloop()
