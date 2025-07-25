from slack_sdk import WebClient
import google.generativeai as genai
import os
from dotenv import load_dotenv
import time
from datetime import datetime
from flask import Flask, request, make_response, jsonify, request
import json
import requests
import threading



MODEL = "gemini-2.0-flash" # model version
now = datetime.fromtimestamp(time.time()).strftime("%Y.%m.%d %H:%M:%S") #현재시각

load_dotenv(dotenv_path="./tokens.env")
API_KEYS = [
    os.getenv("GOOGLE_API_KEY1"),
    os.getenv("GOOGLE_API_KEY2"),
    os.getenv("GOOGLE_API_KEY3"),
    os.getenv("GOOGLE_API_KEY4")
]
token = os.getenv("SLACK_BOT_TOKEN")

current_api_index = 0
call_count = 0

genai.configure(api_key=API_KEYS[current_api_index])  # 초기 API 키 설정
model = genai.GenerativeModel(MODEL)

if API_KEYS is None or len(API_KEYS) == 0:
    raise ValueError("Google Generative AI API KEY ERROR!")

def get_next():
    global current_api_index
    api_key = API_KEYS[current_api_index]
    current_api_index = (current_api_index + 1) % len(API_KEYS)  # 라운드 로빈 방식으로 순환
    print(current_api_index)
    return api_key

# Google AI API 설정
def conf_next():
    global call_count, model
    if call_count >= 5:
        genai.configure(api_key=get_next())
        global nowmodel
        model = genai.GenerativeModel(MODEL)
        print(f"[DEBUG] API 키 변경됨: {current_api_index}번 키: {API_KEYS[current_api_index]}")
        call_count = 0
        return model
    call_count += 1

# Slack 클라이언트 설정
client = WebClient(token=token)

app = Flask(__name__)

'''
@app.route('/slack', methods=['POST'])
def hears():
    slack_event = request.get_json()
    if "challenge" in slack_event:
        print("[Slack Challenge]", slack_event["challenge"])
        return jsonify({"challenge": slack_event["challenge"]})
    
    print("[Slack Event]", slack_event)
    return make_response("OK", 200)
'''

def reply(response_url, text):
    requests.post(response_url, json={"text": text, "mrkdwn": True})

def deferred(text):
    return jsonify({
            "response_type": "ephemeral",
            "text": text
        })

def cmd_menu_recommendation(time_type, req_text, response_url):
    try:
        response = model.generate_content(f"""
너는 '무난하고 현실적인 {time_type} 메뉴'를 추천하는 AI야.

기본 원칙은 다음과 같아:
1. **일상적으로 먹을 수 있는 현실적인 메뉴만 추천**해. 지나치게 특이하거나 퓨전 성격이 강한 메뉴(예: 김치볶음밥 그라탕, 명란 아보카도 볶음밥 등)는 제외해.
2. **추천되는 메뉴는 한식, 중식, 일식, 양식, 분식 등에서 고르게 분포**되도록 해. 항상 특정 한두 메뉴만 반복하지 말고, **메뉴 풀이 넓고 다양하게 유지**해.
3. **매번 무작위(random)**로 메뉴를 구성해.
4. 추천 메뉴는 **식당, 매점, 편의점, 도시락 가게, 배달 앱, 슈퍼마켓, 대형마트 등에서 실제로 구매 가능한 메뉴여야 해.**
5. 사용자가 아래에 제시한 요청사항이 있다면, 이를 **최우선으로 반영**하고 그렇지 않으면 **무난한 추천**으로 구성해.

요청사항: {req_text}

총 15개의 메뉴를 추천하고,
형식은 아래처럼 작성해. 불필요한 표현은 넣지 마.
**메뉴 추천**
1. 후보군1: 설명
2. 후보군2: 설명
3. 후보군3: 설명
(...)
10. 후보군15: 설명
""")
        conf_next()
        reply_text = "No response"
        if hasattr(response, 'text'): reply_text = response.text
        print(f"[DEBUG] {reply_text}")
        final_reply = model.generate_content(f"""
너는 '무난하고 현실적인 {time_type} 메뉴'를 추천하는 AI야.
{reply_text}
상기 15개의 메뉴 추천 후보군 중 5개만 완전 무작위로 고르되,
다음 요청사항이 있다면 최우선적으로 반영하여 골라.
요청사항: {req_text}
형식은 아래처럼 작성해. 불필요한 표현은 넣지 마.
*{time_type}메뉴 추천*
1. 메뉴명: 설명
2. 메뉴명: 설명
3. 메뉴명: 설명     
4. 메뉴명: 설명 
5. 메뉴명: 설명                                      
""")
        conf_next()
        if hasattr(final_reply, 'text'): final_reply = final_reply.text
        print(f"[DEBUG] 최종 추천: {final_reply}")
        reply(response_url, final_reply)
         
    except Exception as e:
        reply(response_url, f"오류 발생: {str(e)}")


@app.route('/slack/command', methods=['POST'])
def slash_command():
    form = request.form
    command = form.get('command')
    text = form.get('text', 'None')
    response_url = form.get('response_url')

    if command == "/점메추":
        threading.Thread(target=cmd_menu_recommendation, args=("점심", text, response_url)).start()
        return deferred(f"`{MODEL}`이(가) 점심 메뉴를 추천해드릴게요. 잠시만 기다려주세요.")
    elif command == "/저메추":
        threading.Thread(target=cmd_menu_recommendation, args=("저녁", text, response_url)).start()
        return deferred(f"`{MODEL}`이(가) 저녁 메뉴를 추천해드릴게요. 잠시만 기다려주세요.")
    else:
        print(f"[DEBUG] 알 수 없는 명령어: {command}")
        return make_response("Unknown command", 400)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)