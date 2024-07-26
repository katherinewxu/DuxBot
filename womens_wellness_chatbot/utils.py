from langchain_openai import ChatOpenAI
from config import OPENAI_API_KEY
import json

def generate_followup_questions(initial_response):
    llm_json = ChatOpenAI(
        model_name="gpt-3.5-turbo",
        openai_api_key=OPENAI_API_KEY,
        model_kwargs={"response_format": {"type": "json_object"}}
    )

    followup_prompt = f"""Put yourself in the shoes of the person who is provided this initial response. Based on the following initial response, generate 2 follow-up questions the user could ask. Provide the output as a JSON object with a "questions" key containing an array of strings:

    Initial response:
    {initial_response}

    Follow-up questions (in JSON format):"""

    followup_response = llm_json.predict(followup_prompt)
    return json.loads(followup_response)['questions'][:2]  # Limit to 2 questions
