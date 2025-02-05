import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure the Gemini API
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))

def chat_with_gemini():
    # Create a model instance
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Start a chat session
    chat = model.start_chat(history=[])
    
    print("Chat started with Gemini (type 'quit' to exit)")
    print("-" * 50)
    
    while True:
        # Get user input
        user_input = input("You: ").strip()
        
        # Check for quit command
        if user_input.lower() == 'quit':
            print("Ending chat session...")
            break
        
        try:
            # Get response from Gemini
            response = chat.send_message(user_input)
            print("\nGemini:", response.text)
            print("-" * 50)
            
        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    chat_with_gemini()