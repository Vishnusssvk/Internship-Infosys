from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate, MessagesPlaceholder
from langchain.memory import ChatMessageHistory
from langchain.schema import SystemMessage
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

def chat_with_gemini():
    # Initialize the Gemini model
    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=os.getenv('GOOGLE_API_KEY'),
        temperature=0.7
    )
    
    # Initialize chat history
    chat_history = ChatMessageHistory()
    
    # Create the chat prompt template
    prompt = PromptTemplate(
        input_variables=["input"],
        template="{input}"
    )
    
    # Create the chain
    chain = LLMChain(
        llm=llm,
        prompt=prompt,
        verbose=False
    )
    
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
            response = chain.run(user_input)
            
            # Add messages to history
            chat_history.add_user_message(user_input)
            chat_history.add_ai_message(response)
            
            print("\nGemini:", response)
            print("-" * 50)
            
        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    chat_with_gemini()