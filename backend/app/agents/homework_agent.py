import os
from app.core.openai_client import get_openai_client, get_default_gpt_model

async def generate_homework(request):
    """
    Use LangGraph and OpenAI GPT-4 to generate personalized homework questions.
    """
    openai_client = get_openai_client()
    model_name = get_default_gpt_model()

    print(f"[HomeworkAgent] 🔍 MODEL: Using {model_name.upper()} for homework generation")

    prompt = f"""
    You are an expert teacher. Generate 5 personalized homework questions for:
    Subject: {request.subject}
    Grade: {request.grade}
    Topic: {request.topic or 'General'}
    Student: {request.student_name or 'Student'}
    Format as a numbered list.
    """
    response = await openai_client.chat.completions.create(
        model=get_default_gpt_model(),
        messages=[{"role": "system", "content": "You are a helpful homework generator."},
                  {"role": "user", "content": prompt}],
        max_tokens=400,
        temperature=0.7,
    )
    content = response.choices[0].message.content
    return content.strip() if content else "Sorry, I couldn't generate homework." 