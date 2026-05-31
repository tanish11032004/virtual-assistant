import pyttsx3
import random
import requests
from bs4 import BeautifulSoup
import logging

# Initialize text-to-speech engine (if you want to use it later)
engine = pyttsx3.init()

# Configure logging
logging.basicConfig(level=logging.ERROR)

# Chatbot logic
def chatbot_response(user_input):
    user_input = user_input.lower()
    greetings = ['hello!', 'hi there!', 'greetings!', 'howdy!']
    farewells = ['goodbye!', 'see you later!', 'take care!']

    # Simple responses based on user input
    if 'hello' in user_input:
        return random.choice(greetings) + ' How can I assist you today?'
    if 'how are you' in user_input:
        return 'I\'m just a chatbot, but I\'m here to help you!'
    if 'bye' in user_input or 'exit' in user_input:
        return random.choice(farewells) + ' Have a great day!'
    if 'help' in user_input:
        return 'Sure! You can ask me about the weather, news, or just chat!'

    # Perform a Google search if the input doesn't match predefined responses
    return google_search(user_input)

# Google search for chatbot
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
        logging.error(f"Error during Google search: {e}")
        return 'I encountered an error while searching.'
