import os
import json
from langgraph.graph import StateGraph
from langgraph.graph import END
from app.core.openai_client import get_openai_client
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

# Step 1: Define all tool functions (responses)
def answer_general_info(state):
    # TODO: Implement with canonical answer and prompt engineering
    return {"output": "[General info answer goes here]"}
def answer_academic_info(state):
    # TODO: Implement with canonical answer and prompt engineering
    return {"output": "[Academic info answer goes here]"}
def answer_admission_info(state):
    # TODO: Implement with canonical answer and prompt engineering
    return {"output": "[Admission info answer goes here]"}
def answer_fee_info(state):
    # TODO: Implement with canonical answer and prompt engineering
    return {"output": "[Fee info answer goes here]"}
def answer_activities_info(state):
    # TODO: Implement with canonical answer and prompt engineering
    return {"output": "[Activities info answer goes here]"}
def answer_inclusion_info(state):
    # TODO: Implement with canonical answer and prompt engineering
    return {"output": "[Inclusion info answer goes here]"}
def answer_contact_info(state):
    # TODO: Implement with canonical answer and prompt engineering
    return {"output": "[Contact info answer goes here]"}
def answer_fallback(state):
    # Use OpenAI LLM for general-purpose fallback answers
    openai_client = get_openai_client()
    user_input = state["input"]
    prompt = f"User: {user_input}\nAI:"
    response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "You are a helpful school assistant chatbot."},
                  {"role": "user", "content": user_input}],
        max_tokens=400,
        temperature=0.7,
    )
    # If using OpenAI's async client, use await above and make this function async
    content = response.choices[0].message.content
    return {"output": content.strip() if content else "Sorry, I couldn't find an answer to your question."}

# Step 2: Intent classifier
def classify_intent(state):
    user_input = state["input"].lower()

    if any(w in user_input for w in ["where", "location", "what is prakriti", "type of school"]):
        return {"output": "general_info"}
    elif any(w in user_input for w in ["curriculum", "program", "subjects", "courses", "igcse", "a level"]):
        return {"output": "academic_info"}
    elif "admission" in user_input or "how to apply" in user_input:
        return {"output": "admission_info"}
    elif "fee" in user_input or "cost" in user_input or "charges" in user_input:
        return {"output": "fee_info"}
    elif "activities" in user_input or "sports" in user_input or "co-curricular" in user_input:
        return {"output": "activities_info"}
    elif "inclusive" in user_input or "special needs" in user_input or "bridge" in user_input:
        return {"output": "inclusion_info"}
    elif "contact" in user_input or "email" in user_input or "how to reach" in user_input:
        return {"output": "contact_info"}
    else:
        return {"output": "fallback"}

# Step 3: Build the LangGraph
from typing import TypedDict

class ChatState(TypedDict):
    input: str
    output: str

graph = StateGraph(ChatState)

# Add nodes
graph.add_node("classify", classify_intent)
graph.add_node("general_info", answer_general_info)
graph.add_node("academic_info", answer_academic_info)
graph.add_node("admission_info", answer_admission_info)
graph.add_node("fee_info", answer_fee_info)
graph.add_node("activities_info", answer_activities_info)
graph.add_node("inclusion_info", answer_inclusion_info)
graph.add_node("contact_info", answer_contact_info)
graph.add_node("fallback", answer_fallback)

# Edges
graph.set_entry_point("classify")

# Add conditional edges using the new API
graph.add_conditional_edges(
    "classify",
    lambda x: x["output"],
    {
        "general_info": "general_info",
        "academic_info": "academic_info",
        "admission_info": "admission_info",
        "fee_info": "fee_info",
        "activities_info": "activities_info",
        "inclusion_info": "inclusion_info",
        "contact_info": "contact_info",
        "fallback": "fallback"
    }
)

# Route all tools to END
graph.add_edge("general_info", END)
graph.add_edge("academic_info", END)
graph.add_edge("admission_info", END)
graph.add_edge("fee_info", END)
graph.add_edge("activities_info", END)
graph.add_edge("inclusion_info", END)
graph.add_edge("contact_info", END)
graph.add_edge("fallback", END)

# Compile graph
chatbot = graph.compile() 