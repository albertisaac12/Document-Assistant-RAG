import sqlite3
import google.generativeai as genai
import sys

def main():
    conn = sqlite3.connect('instance/document_chatbot.db')
    cursor = conn.cursor()
    cursor.execute('SELECT gemini_api_key FROM users WHERE gemini_api_key IS NOT NULL LIMIT 1')
    row = cursor.fetchone()
    if not row:
        print("No API key found in DB.")
        sys.exit(1)
        
    api_key = row[0]
    genai.configure(api_key=api_key)
    
    print("Available Embedding Models:")
    for m in genai.list_models():
        if "embedContent" in m.supported_generation_methods:
            print(f"- {m.name}")

if __name__ == '__main__':
    main()
