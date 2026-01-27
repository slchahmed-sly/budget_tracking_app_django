import os
from google import genai
from google.genai import types

api_key = os.environ.get("GEMINI_API_KEY")

def get_financial_advice(context_data):
    if not api_key:
        return "Error: API Key not found."

    try:
        client = genai.Client(api_key=api_key)

    
        prompt = (
            f"Role: You are a sharp financial detective. You have access to the user's full transaction history. "
            f"Your goal is to calculate the hard numbers AND find hidden insights in the comments.\n\n"
            
            f"=== LANGUAGE ===\n"
            f"IMPORTANT: You must respond in the following language: {context_data.get('language', 'en')}"
            
            f"=== DATA ===\n"
            f"Days Left: {context_data['remaining_days']}\n"
            f"Current Cash: {context_data['main_budget']} {context_data['currency']}\n"
            f"Daily Allowance: {context_data['daily_allowance']} {context_data['currency']}\n"
            f"Risk Info: {context_data['uncertain_total']} is uncertain income. {context_data['debt_total']} is owed to user.\n"
            f"FULL LEDGER:\n{context_data['full_ledger']}\n\n"
            
            f"=== INSTRUCTIONS ===\n"
            f"Output exactly 3 distinct sections. Do not use Markdown (**bold**) but use clear headers.\n\n"
            
            f"SECTION 1: THE STRATEGY\n"
            f"- Calculate the 'Real Safe Spend' (Cash - Uncertain - Debts) / Days.\n"
            f"- Calculate the 'Skip Day Bonus' (Allowance * 2).\n"
            f"- If there are debts to collect, calculate how much they would increase the daily allowance.\n\n"
            
            f"SECTION 2: LEDGER ANALYSIS\n"
            f"- Read the comments in the ledger carefully. Are there reminders? (e.g. 'pay back later', 'refund').\n"
            f"- Are there unusual spending patterns? (e.g. 'Why 3 expenses for Coffee today?').\n"
            f"- Identify specific transactions that look risky or need attention.\n"
            f"- If the comments are empty or boring, just say 'No specific notes found in ledger.'\n\n"
            
            f"SECTION 3: VERDICT\n"
            f"- One sentence summary of their financial health.\n\n"
            
        )

        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt
        )

        return response.text

    except Exception as e:
        return f"AI Logic Error: {str(e)}"