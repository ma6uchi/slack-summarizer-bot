import os
import google.generativeai as genai

def lambda_handler(event, context):
    api_key = os.environ.get("API_KEY")

    # APIキーが設定されていない場合はエラーを返す
    if not api_key:
        return {
            "statusCode": 500,
            "body": "API_KEY environment variable is not set."
        }

    genai.configure(api_key=api_key) 

    try:
        model = genai.GenerativeModel('gemini-1.5-flash') # または使用したいモデル名
        response = model.generate_content("AIの仕事を50文字で教えて")

        return {
            "statusCode": 200, 
            "body": response.text
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": f"Error: {str(e)}"
        }