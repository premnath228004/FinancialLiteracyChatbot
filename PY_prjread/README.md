# Financial Data Chatbot

This is a simple chatbot application that uses the Gemini API to process or respond to queries related to financial data stored in `financial_data.json`.

## Features

- Interacts with Google's Gemini API for natural language processing
- Securely loads API keys from `.env` file using `python-dotenv`
- Processes queries related to financial data

## Prerequisites

- Python 3.x
- Google Gemini API key

## Installation

1. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Create a `.env` file in the project root and add your Gemini API key:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

3. Ensure `financial_data.json` is present in the project root with your financial data.

## Usage

Run the chatbot with:
```
python chatbot.py
```

## Dependencies

- `google-genai` - For interacting with Google's Gemini API
- `python-dotenv` - For securely loading API keys from `.env` file

## File Structure

- `chatbot.py` - Main chatbot application
- `financial_data.json` - Financial data storage
- `requirements.txt` - Project dependencies
- `.env` - Environment variables (not included in repository)