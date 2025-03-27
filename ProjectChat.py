import os
import openai
import requests
import pandas as pd
from dotenv import load_dotenv
from google.cloud import translate_v2 as translate
from openpyxl import load_workbook

# Load environment variables from .env file
load_dotenv()

# Set API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_CREDENTIALS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

if not OPENAI_API_KEY:
    raise ValueError("Missing OpenAI API Key! Check your .env file.")
if not GOOGLE_CREDENTIALS_PATH:
    raise ValueError("Missing Google Cloud Credentials! Check your .env file.")

# Set Google Cloud credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_CREDENTIALS_PATH

# Initialize Google Cloud Translator
translator = translate.Client()

def translate_text(text, from_lang, target_lang, use_mymemory=False):
    """Translate text using MyMemory API first, with Google Translate as a fallback."""
    
    # MyMemory API (primary)
    try:
        url = f"https://api.mymemory.translated.net/get?q={text}&langpair={from_lang}|{target_lang}"
        response = requests.get(url)
        response_json = response.json()

        if response_json.get("responseData"):
            translated_text = response_json["responseData"].get("translatedText")
            
            # Check if MyMemory returned a quota error
            if "YOU USED ALL AVAILABLE FREE TRANSLATIONS FOR TODAY" in translated_text:
                print(f"⚠️ MyMemory limit reached")
                raise ValueError("MyMemory free limit exceeded.")  # Force fallback to Google Translate
            
            print(f"MyMemory Translated to {target_lang}: {translated_text}")
            return translated_text
        else:
            print(f"⚠️ MyMemory Translation error ({target_lang}): {response_json}")
    except Exception as e:
        print(f"MyMemory API error ({target_lang}): {e}")
             
    print("🔄 Falling back to Google Translate...")

    # Google Translate (fallback)
    try:
        result = translator.translate(text, target_language=target_lang)
        print(f"Translated to {target_lang}: {result['translatedText']}")
        return result["translatedText"]
    except Exception as e:
        print(f"Google Translate error ({target_lang}): {e}")

    # Return original text if both translations fail
    print(f"⚠️ Both translation services failed for {target_lang}. Returning original text.")
    return text  


def ask_chatgpt(question):
    """Ask ChatGPT and return the response."""
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  # Updated client initialization
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",  # Updated model name
        messages=[{"role": "user", "content": question}]
    )
    return response.choices[0].message.content  # Corrected response extraction

def multilingual_query(question, languages):
    """Translate a question into multiple languages, ask ChatGPT, and retranslate responses."""
    results = []

    for lang in languages:
        print(f"\nProcessing language: {lang.upper()}...")  # Debugging output

        # Step 1: Translate question to the target language
        translated_question = translate_text(question, 'en', lang)

        # Step 2: Ask ChatGPT the translated question
        chatgpt_response = ask_chatgpt(translated_question)

        # Step 3: Translate ChatGPT's response back to English
        translated_response = translate_text(chatgpt_response, lang, 'en')

        # Store in list for DataFrame
        results.append({
            "Language": lang.upper(),
            "Translated Question": translated_question,
            "ChatGPT Response": chatgpt_response,
            "Translated Back to English": translated_response
        })
    return results

def save_to_excel(data, filename="data.xlsx"):
    """Save results to an Excel file, appending if it already exists."""
    try:
        # Convert data to DataFrame
        df = pd.DataFrame(data)
        
        # Read existing data
        df_existing = pd.read_excel(filename, engine='openpyxl')

        # Append new data
        df_combined = pd.concat([df_existing, df], ignore_index=True)
        #df_combined = df_existing.append(df, ignore_index=True)

        # Save the combined data to Excel
        df_combined.to_excel(filename, index=False, engine="openpyxl")

        print(f"✅ Results saved and appended to {filename}")
                
    except Exception as e:
        print(f"❌ Error saving to Excel: {e}")

    

# Define languages (ISO 639-1 codes)
languages = ['fr', 'hi', 'zh', 'ja', 'ar'] 

# Get user input
user_question = input("Enter your question: ")

# Run the multilingual query
responses = multilingual_query(user_question, languages)

# Print results
for response in responses:
    print(f"\n--- {response['Language']} ---")
    print(f"Translated Question: {response['Translated Question']}")
    print(f"ChatGPT Response: {response['ChatGPT Response']}")
    print(f"Translated Back: {response['Translated Back to English']}")

# Save results to an Excel file
save_to_excel(responses)
