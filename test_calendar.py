import requests
import json

url = 'http://localhost:8000/chatbot/'
data = {
    'message': '3rd January ko kya hai',
    'conversation_history': [],
    'user_id': '0f7f1e15-5a05-438b-83eb-b990b4a46cab'
}

try:
    response = requests.post(url, json=data, timeout=15)
    if response.status_code == 200:
        print('SUCCESS: Response received')
        result = response.json()
        response_text = result.get('response', '')
        if 'hazrat ali' in response_text.lower() or 'birthday' in response_text.lower():
            print('SUCCESS: Real calendar data found (Hazrat Ali birthday)')
        elif 'braille' in response_text.lower() or 'ब्रेल' in response_text:
            print('FAILED: Still showing web fallback data (World Braille Day)')
        else:
            print('UNKNOWN: Response contains:', repr(response_text[:200]))
    else:
        print(f'ERROR: {response.status_code}')
except Exception as e:
    print(f'Connection error: {e}')


