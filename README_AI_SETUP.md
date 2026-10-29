# Real AI Chatbot Setup

The SmartHealth chatbot can use the OpenAI Responses API. OpenAI's current documentation lists GPT-5.6 Luna as a cost-sensitive model and states that current models are available through the Responses API and client SDKs.

## Windows PowerShell

1. Install dependencies:

```powershell
venv\Scripts\python.exe -m pip install -r requirements.txt
```

2. Set your API key for the current terminal session:

```powershell
$env:OPENAI_API_KEY="YOUR_API_KEY"
$env:OPENAI_MODEL="gpt-5.6-luna"
$env:FLASK_SECRET_KEY="USE-A-LONG-RANDOM-SECRET"
```

3. Start the app:

```powershell
venv\Scripts\python.exe app.py
```

The chatbot will use the real LLM when `OPENAI_API_KEY` is present. Without the key it safely falls back to a small local educational assistant.

Never put the API key directly into `app.py` or commit it to Git.
