import os
from app.core.openai_client import get_openai_client, get_default_gpt_model

async def auto_grade(request):
    """
    Use LangGraph and OpenAI GPT-4 to auto-grade student answers.
    """
    openai_client = get_openai_client()
    model_name = get_default_gpt_model()

    print(f"[GradingAgent] 🔍 MODEL: Using {model_name.upper()} for answer grading")

    prompt = f"""
    You are an expert teacher. Grade the following student answer.
    Question: {request.question or 'N/A'}
    Answer Key: {request.answer_key}
    Student Answer: {request.student_answer}
    Rubric: {request.rubric or 'Standard'}
    Provide a score (0-1) and concise feedback.
    Respond in JSON: {{"score": float, "feedback": string}}
    """
    response = await openai_client.chat.completions.create(
        model=get_default_gpt_model(),
        messages=[{"role": "system", "content": "You are a helpful grading assistant."},
                  {"role": "user", "content": prompt}],
        max_tokens=200,
        temperature=0.3,
    )
    import json
    content = response.choices[0].message.content
    if content:
        try:
            result = json.loads(content)
            return result
        except Exception:
            return {"score": 0.0, "feedback": "Could not parse grading result."}
    else:
        return {"score": 0.0, "feedback": "No grading response generated."} 