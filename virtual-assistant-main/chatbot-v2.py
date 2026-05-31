import tkinter as tk
from tkinter import scrolledtext, filedialog
import time
import speech_recognition as sr
import pyttsx3
import random
import requests
from bs4 import BeautifulSoup

recognizer = sr.Recognizer()
engine = pyttsx3.init()

def chatbot_response(user_input):
    user_input = user_input.lower()
    greetings = ['hello!', 'hi there!', 'greetings!', 'howdy!']
    farewells = ['goodbye!', 'see you later!', 'take care!']
    
    if 'hello' in user_input:
        return random.choice(greetings) + ' How can I assist you today?'
    if 'how are you' in user_input:
        return 'I\'m just a chatbot, but I\'m here to help you!'
    if 'bye' in user_input or 'exit' in user_input:
        return random.choice(farewells) + ' Have a great day!'
    if 'help' in user_input:
        return 'Sure! You can ask me about the weather, news, or just chat!'
    
    return google_search(user_input)

def google_search(query):
    try:
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        snippets = soup.find_all('div', class_='BNeawe s3v9rd AP7Wnd')
        results = [snippet.get_text() for snippet in snippets][:3]
        
        if results:
            return 'Here are some results:\n' + '\n'.join(results)
        else:
            return 'I couldn\'t find anything on that. Sorry!'
    except Exception as e:
        return 'I encountered an error while searching.'

def send_message():
    user_input = input_box.get()
    if user_input:
        chat_area.insert(tk.END, 'You: ' + user_input + '\n')
        input_box.delete(0, tk.END)
        chat_area.insert(tk.END, 'Bot is typing...\n')
        root.update()
        time.sleep(1)
        chat_area.delete('end-2l', 'end-1l')
        
        response = chatbot_response(user_input)
        chat_area.insert(tk.END, 'Bot: ' + response + '\n\n')
        chat_area.yview(tk.END)
        speak_text(response)

def recognize_speech():
    with sr.Microphone() as source:
        chat_area.insert(tk.END, 'Listening...\n')
        audio = recognizer.listen(source)
        try:
            user_input = recognizer.recognize_google(audio)
            chat_area.insert(tk.END, 'You (voice): ' + user_input + '\n')
            response = chatbot_response(user_input)
            chat_area.insert(tk.END, 'Bot: ' + response + '\n\n')
            speak_text(response)
        except sr.UnknownValueError:
            chat_area.insert(tk.END, 'Bot: I couldn\'t understand you. Please try again.\n\n')
        except sr.RequestError:
            chat_area.insert(tk.END, 'Bot: Speech recognition service is unavailable.\n\n')

def speak_text(text):
    engine.say(text)
    engine.runAndWait()

def save_chat_history():
    file_path = filedialog.asksaveasfilename(defaultextension='.txt', filetypes=[('Text files', '*.txt'), ('All files', '*.*')])
    if file_path:
        with open(file_path, 'w') as file:
            file.write(chat_area.get('1.0', tk.END))
        chat_area.insert(tk.END, 'Chat history saved.\n\n')

def load_chat_history():
    file_path = filedialog.askopenfilename(filetypes=[('Text files', '*.txt'), ('All files', '*.*')])
    if file_path:
        with open(file_path, 'r') as file:
            chat_area.insert(tk.END, file.read())

def toggle_theme():
    current_bg = root.cget('bg')
    if current_bg == 'lightgray':
        root.config(bg='black')
        chat_area.config(bg='black', fg='white')
        input_box.config(bg='black', fg='white', insertbackground='white')
        send_button.config(bg='gray', fg='white')
        voice_button.config(bg='gray', fg='white')
        theme_button.config(bg='gray', fg='white')
    else:
        root.config(bg='lightgray')
        chat_area.config(bg='white', fg='black')
        input_box.config(bg='white', fg='black', insertbackground='black')
        send_button.config(bg='white', fg='black')
        voice_button.config(bg='white', fg='black')
        theme_button.config(bg='white', fg='black')

# Set up the GUI
root = tk.Tk()
root.title('Chatbot with GUI')
root.config(bg='lightgray')

chat_area = scrolledtext.ScrolledText(root, wrap=tk.WORD, height=20, width=50, bg='white', fg='black')
chat_area.pack(padx=10, pady=10)
chat_area.config(state=tk.NORMAL)

input_box = tk.Entry(root, width=40, bg='white', fg='black', insertbackground='black')
input_box.pack(padx=10, pady=5)

send_button = tk.Button(root, text='Send', command=send_message, bg='white', fg='black')
send_button.pack(pady=5)

voice_button = tk.Button(root, text='Voice Input', command=recognize_speech, bg='white', fg='black')
voice_button.pack(pady=5)

theme_button = tk.Button(root, text='Toggle Dark Mode', command=toggle_theme, bg='white', fg='black')
theme_button.pack(pady=5)

menu_bar = tk.Menu(root)
file_menu = tk.Menu(menu_bar, tearoff=0)
file_menu.add_command(label='Save Chat History', command=save_chat_history)
file_menu.add_command(label='Load Chat History', command=load_chat_history)
menu_bar.add_cascade(label='File', menu=file_menu)

root.config(menu=menu_bar)
root.bind('<Return>', lambda event: send_message())

root.mainloop()
