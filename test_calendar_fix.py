import requests
import json

print("Testing calendar query detection for Hindi query...")

url = 'http://localhost:8000/chatbot/'
data = {
    'message': '3rd January ko kya hai',
    'conversation_history': [],
    'user_id': '0f7f1e15-5a05-438b-83eb-b990b4a46cab'
}

try:
    response = requests.post(url, json=data, timeout=20)
    if response.status_code == 200:
        print('✅ Request successful')
        result = response.json()
        response_text = result.get('response', '')

        # Check what the response contains
        if 'hazrat ali' in response_text.lower() or 'birthday' in response_text.lower():
            print('🎉 SUCCESS: Real calendar data found (Hazrat Ali birthday)')
            print('Calendar query detection is working!')
        elif 'braille' in response_text.lower() or 'ब्रेल' in response_text:
            print('❌ FAILED: Still showing web fallback data (World Braille Day)')
            print('Calendar query detection is NOT working')
        else:
            print('❓ UNKNOWN response type')
            print('Response preview:', response_text[:150] + '...')
    else:
        print(f'❌ HTTP Error: {response.status_code}')

except Exception as e:
    print(f'❌ Connection error: {e}')


