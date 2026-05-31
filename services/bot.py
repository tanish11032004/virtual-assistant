import random
from typing import List, Dict

class ChatBot:
    """Chatbot service for handling user interactions."""
    
    GREETINGS: List[str] = ['Hello!', 'Hi there!', 'Greetings!', 'Howdy!']
    FAREWELLS: List[str] = ['Goodbye!', 'See you later!', 'Take care!']
    
    @staticmethod
    def get_response(user_input: str) -> str:
        """
        Generate response based on user input.
        
        Args:
            user_input: User's message
            
        Returns:
            Bot's response message
        """
        user_input = user_input.lower()
        
        if 'hello' in user_input:
            return f"{random.choice(ChatBot.GREETINGS)} How can I assist you today?"
        if 'bye' in user_input or 'exit' in user_input:
            return f"{random.choice(ChatBot.FAREWELLS)} Have a great day!"
        
        return "I'm not sure how to answer that. Could you try asking something else?"

chatbot_response = ChatBot.get_response
