import re
import os
import json
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
try:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
except Exception:
    client = None

def parse_chat(file_path):
    messages = []
    current_message= None;

    pattern=r"^(\d{1,2}/\d{1,2}/\d{2},\s\d{1,2}:\d{2}.*)-\s(.+?):\s(.*)"

    with open(file_path,"r",encoding="utf-8") as file:
        lines=file.readlines()

    for line in lines:
        line=line.strip()
        match=re.match(pattern,line)
        if match:
            if current_message:
                messages.append(current_message)

            current_message = {
                "datetime": match.group(1).strip(),
                "sender": match.group(2).strip(),
                "message": match.group(3).strip()
            }
        else:
            if current_message:
                current_message["message"] += " " + line

    if current_message:
        messages.append(current_message)

    return messages

def extract_event_with_ai(message_text):

    prompt = f"""
You are an event extraction assistant.

From the WhatsApp message below, extract event information.

Return ONLY valid JSON with this schema:

{{
  "is_event": boolean,
  "title": string or null,
  "start_datetime": ISO 8601 string or null,
  "end_datetime": ISO 8601 string or null,
  "confidence": number between 0 and 1
}}

Rules:
- If no event exists, return is_event=false
- If date not found, start_datetime=null
- Assume timezone Asia/Kolkata
- Convert relative dates to full ISO format
- Today is {datetime.now().date()}

Message:
\"\"\"{message_text}\"\"\"
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {"role": "system", "content": "You extract structured event data."},
            {"role": "user", "content": prompt}
        ]
    )

    content = response.choices[0].message.content.strip()

    try:
        return json.loads(content)
    except:
        return None

def is_future_date(date_string):
    try:
        event_date = datetime.fromisoformat(date_string)
        return event_date > datetime.now()
    except:
        return False

if __name__ == "__main__":
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not found in .env file.")
        print("Please add your API key to the source/.env file.")
        exit(1)

    file_path = "chat.txt"

    messages = parse_chat(file_path)

    print(f"Parsed {len(messages)} messages\n")

    for msg in messages:
        print("Processing:", msg["message"][:60], "...")

        ai_result = extract_event_with_ai(msg["message"])

        if not ai_result:
            continue

        if (
            ai_result["is_event"]
            and ai_result["confidence"] > 0.7
            and ai_result["start_datetime"]
            and is_future_date(ai_result["start_datetime"])
        ):
            print("EVENT DETECTED:")
            print(ai_result)
            print("-" * 50)
