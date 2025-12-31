import os
from app.core.openai_client import get_openai_client, get_default_gpt_model

async def generate_lesson_plan(request):
    """
    Use LangGraph and OpenAI GPT-4 to generate a weekly lesson plan.
    """
    openai_client = get_openai_client()
    model_name = get_default_gpt_model()

    print(f"[LessonPlanAgent] 🔍 MODEL: Using {model_name.upper()} for lesson plan generation")

    prompt = f"""
    You are an expert school teacher. Generate a detailed weekly lesson plan for:
    Subject: {request.subject}
    Grade: {request.grade}
    Week: {request.week}
    Format as a clear, structured plan with objectives, activities, and outcomes.
    """
    # LangGraph agent logic (simplified for now)
    response = await openai_client.achat.completions.create(
        model=get_default_gpt_model(),
        messages=[{"role": "system", "content": "You are a helpful lesson planner."},
                  {"role": "user", "content": prompt}],
        max_tokens=800,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip() 