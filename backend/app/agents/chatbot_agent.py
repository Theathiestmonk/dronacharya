import os
import json
from app.core.openai_client import get_openai_client
from rapidfuzz import fuzz

# Path to local knowledge base JSON
KB_PATH = os.path.join(os.path.dirname(__file__), '../../core/knowledge_base.json')

async def retrieve_from_json(query: str, threshold: int = 50) -> str | None:
    """Fuzzy match the user query to questions in the local JSON KB."""
    try:
        with open(KB_PATH, 'r', encoding='utf-8') as f:
            kb = json.load(f)
        best_score = 0
        best_answer = None
        for entry in kb.get('entries', []):
            score = fuzz.token_set_ratio(query.lower(), entry['question'].lower())
            print(f"[Chatbot] Comparing to: {entry['question']} | Score: {score}")
            if score > best_score and score >= threshold:
                best_score = score
                best_answer = entry['answer']
        return best_answer
    except Exception as e:
        print(f"[Chatbot] Error reading KB: {e}")
    return None

async def generate_chatbot_response(request):
    """
    Use OpenAI GPT-4 to generate a chatbot response with RAG logic and fuzzy matching.
    """
    openai_client = get_openai_client()
    user_query = request.message

    # Step 0: Intent detection for holiday calendar
    holiday_keywords = [
        'holiday calendar', 'school holidays', 'vacation calendar', 'holidays', 'school calendar', 'show holidays', 'holiday list', 'calendar of holidays'
    ]
    if any(kw in user_query.lower() for kw in holiday_keywords):
        return {
            'type': 'calendar',
            'url': 'https://calendar.google.com/calendar/embed?src=Y185MWZiZDlkMjE4ZTQ5YzZjY2RhNGEyOTg3ZWI0ZDJkYjcyYTJmYTBlN2JiMTkzYWY2N2U4NjlhY2NiYmRiZWQ3QGdyb3VwLmNhbGVuZGFyLmdvb2dsZS5jb20&ctz=Asia/Kolkata'
        }

    # Step 0.5: Intent-based Q&A for "What kind of school is Prakriti?"
    school_type_intents = [
        'what kind of school is prakriti',
        'what type of school is prakriti',
        'what is prakriti school',
        'describe prakriti school',
        'tell me about prakriti',
        'prakriti school description',
        'is prakriti a progressive school',
        'is prakriti an alternative school',
        'what grades does prakriti have',
        'what makes prakriti different',
        'what is special about prakriti school',
        'prakriti school overview',
        'prakriti k12 school',
        'what does prakriti focus on',
        'what is the philosophy of prakriti school',
    ]
    if any(kw in user_query.lower() for kw in school_type_intents):
        canonical_answer = (
            'Prakriti is an alternative/progressive K–12 school in Noida/Greater Noida focusing on "learning for happiness" through deep experiential education.'
        )
        prompt = (
            f"A user asked about the type of school Prakriti is. Here is the official answer: {canonical_answer}\n"
            "Please explain this in your own words, elaborate, or summarize as needed."
        )
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are a helpful school assistant chatbot."},
                      {"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.7,
        )
        content = response.choices[0].message.content
        return content.strip() if content else canonical_answer

    # Step 0.6: Intent-based Q&A for "What's the teaching philosophy at Prakriti?"
    teaching_philosophy_intents = [
        "what's the teaching philosophy at prakriti",
        "what is prakriti's teaching philosophy",
        "how does prakriti teach",
        "what is the teaching style at prakriti",
        "prakriti school teaching approach",
        "prakriti education philosophy",
        "how are students taught at prakriti",
        "what is the learning model at prakriti",
        "what is prakriti's approach to education",
        "what is the classroom environment at prakriti",
        "prakriti's learning philosophy",
        "what is the focus of teaching at prakriti",
        "prakriti school philosophy",
    ]
    if any(kw in user_query.lower() for kw in teaching_philosophy_intents):
        canonical_answer = (
            'The school follows a compassionate, learner-centric model based on reconnecting with inner nature ("prakriti"), promoting joy, self-expression, and holistic development.'
        )
        prompt = (
            f"A user asked about the teaching philosophy at Prakriti. Here is the official answer: {canonical_answer}\n"
            "Please explain this in your own words, elaborate, or summarize as needed."
        )
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are a helpful school assistant chatbot."},
                      {"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.7,
        )
        content = response.choices[0].message.content
        return content.strip() if content else canonical_answer

    # Step 0.7: Intent-based Q&A for "Which subjects are available for IGCSE and AS/A Level?"
    igcse_subjects_intents = [
        "which subjects are available for igcse and as/a level",
        "igcse subjects",
        "as level subjects",
        "a level subjects",
        "subjects offered igcse",
        "subjects offered as level",
        "subjects offered a level",
        "prakriti igcse subjects",
        "prakriti as level subjects",
        "prakriti a level subjects",
        "what can i study at prakriti",
        "what are the options for igcse",
        "what are the options for a level",
        "what are the options for as level",
        "prakriti subject list",
        "prakriti subject options",
        "subjects for grade 9",
        "subjects for grade 10",
        "subjects for grade 11",
        "subjects for grade 12",
    ]
    if any(kw in user_query.lower() for kw in igcse_subjects_intents):
        canonical_answer = (
            'IGCSE (Grades 9–10) covers core subjects. For AS/A Level (Grades 11–12), available subjects include Design & Tech, History, Computer Science, Enterprise, Art & Design, Physics, Chemistry, Biology, Combined Sciences, English First & Second Language, French, and Math.'
        )
        prompt = (
            f"A user asked about the subjects available for IGCSE and AS/A Level. Here is the official answer: {canonical_answer}\n"
            "Please explain this in your own words, elaborate, or summarize as needed."
        )
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are a helpful school assistant chatbot."},
                      {"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.7,
        )
        content = response.choices[0].message.content
        return content.strip() if content else canonical_answer

    # Step 0.8: Intent-based Q&A for "How are learners with special needs supported?"
    special_needs_intents = [
        "how are learners with special needs supported",
        "special needs support",
        "prakriti special needs",
        "bridge programme",
        "support for special needs",
        "inclusive education prakriti",
        "special educators prakriti",
        "therapists prakriti",
        "parent support prakriti",
        "how does prakriti help special needs",
        "prakriti inclusion",
        "prakriti support for disabilities",
        "prakriti learning support",
        "prakriti therapy",
        "prakriti special education",
    ]
    if any(kw in user_query.lower() for kw in special_needs_intents):
        canonical_answer = (
            'Prakriti runs a Bridge Programme with an inclusive curriculum. Children with diverse needs learn together. Special educators, therapists, and parent support systems are in place.'
        )
        prompt = (
            f"A user asked about support for learners with special needs. Here is the official answer: {canonical_answer}\n"
            "Please explain this in your own words, elaborate, or summarize as needed."
        )
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are a helpful school assistant chatbot."},
                      {"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.7,
        )
        content = response.choices[0].message.content
        return content.strip() if content else canonical_answer

    # Step 0.9: Intent-based Q&A for "What sports, arts, and enrichment activities are available?"
    enrichment_activities_intents = [
        "what sports, arts, and enrichment activities are available",
        "sports at prakriti",
        "arts at prakriti",
        "enrichment activities prakriti",
        "prakriti sports",
        "prakriti arts",
        "prakriti enrichment",
        "activities at prakriti",
        "prakriti extracurricular",
        "prakriti co-curricular",
        "prakriti after school",
        "prakriti clubs",
        "prakriti music",
        "prakriti theater",
        "prakriti stem",
        "prakriti design lab",
        "prakriti mindfulness",
        "prakriti meditation",
        "prakriti maker projects",
        "prakriti farm outings",
        "prakriti field trips",
    ]
    if any(kw in user_query.lower() for kw in enrichment_activities_intents):
        canonical_answer = (
            'Prakriti integrates sports, visual & performing arts, music, theater, STEM/design labs, farm outings, meditation/mindfulness, and maker projects across all grades.'
        )
        prompt = (
            f"A user asked about sports, arts, and enrichment activities at Prakriti. Here is the official answer: {canonical_answer}\n"
            "Please explain this in your own words, elaborate, or summarize as needed."
        )
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are a helpful school assistant chatbot."},
                      {"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.7,
        )
        content = response.choices[0].message.content
        return content.strip() if content else canonical_answer

    # Step 0.10: Intent-based Q&A for "What are the fees for different grades?"
    fees_intents = [
        "what are the fees for different grades",
        "prakriti fee structure",
        "school fees",
        "prakriti fees",
        "grade wise fees",
        "admission charges",
        "fee for nursery",
        "fee for grade 1",
        "fee for grade 12",
        "prakriti admission fee",
        "prakriti tuition",
        "prakriti security deposit",
        "prakriti monthly fee",
        "prakriti one time charges",
        "prakriti payment",
        "prakriti fee breakdown",
        "prakriti fee details",
        "prakriti fee for 2024",
        "prakriti fee for 2025",
    ]
    if any(kw in user_query.lower() for kw in fees_intents):
        canonical_answer = (
            '(2024–25 fee structure)\n'
            '| Grade | Monthly Fee (₹) | Security Deposit (₹, refundable) |\n'
            '|---|---|---|\n'
            '| Pre-Nursery–KG | 21,000 | 60,000 |\n'
            '| Grade I–V | 25,400 | 75,000 |\n'
            '| Grade VI–VIII | 28,000 | 90,000 |\n'
            '| Grade IX | 31,200 | 100,000 |\n'
            '| Grade X | 32,400 | 100,000 |\n'
            '| Grade XI–XII | 35,000 | 100,000 |\n'
            '| Admission charges (one-time, non-refundable) | – | 125,000'
        )
        prompt = (
            f"A user asked about the fees for different grades. Here is the official answer (including a table):\n{canonical_answer}\n"
            "Please explain this in your own words, summarize the fee structure, and mention the admission charges."
        )
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are a helpful school assistant chatbot."},
                      {"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.7,
        )
        content = response.choices[0].message.content
        return content.strip() if content else canonical_answer

    # Step 0.11: Intent-based Q&A for "Where is Prakriti School located?" with Google Map embed
    location_intents = [
        "where is prakriti school located",
        "prakriti school location",
        "prakriti address",
        "prakriti location",
        "school address",
        "prakriti map",
        "how to reach prakriti",
        "prakriti school directions",
        "prakriti school google map",
        "prakriti school route",
        "prakriti school navigation",
        "prakriti school in greater noida",
        "prakriti school on expressway",
        "prakriti school ncr",
    ]
    if any(kw in user_query.lower() for kw in location_intents):
        canonical_answer = (
            'Prakriti is located on the Noida Expressway in Greater Noida, NCR.'
        )
        prompt = (
            f"A user asked about the location of Prakriti School. Here is the official answer: {canonical_answer}\n"
            "Please explain this in your own words, elaborate, or summarize as needed."
        )
        response = await openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are a helpful school assistant chatbot."},
                      {"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.7,
        )
        content = response.choices[0].message.content
        # Google Maps embed URL for Prakriti School
        map_url = "https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3502.123456789!2d77.123456!3d28.123456!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x390ce4b123456789:0xabcdefabcdefabcd!2sPrakriti%20School!5e0!3m2!1sen!2sin!4v1710000000000!5m2!1sen!2sin"
        return [content.strip() if content else canonical_answer, {"type": "map", "url": map_url}]

    # Step 2: Fallback to LLM
    print("[Chatbot] Answer from GPT-4")
    prompt = f"User: {user_query}\nAI:"
    response = await openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "You are a helpful school assistant chatbot."},
                  {"role": "user", "content": user_query}],
        max_tokens=400,
        temperature=0.7,
    )
    content = response.choices[0].message.content
    return content.strip() if content else "Sorry, I couldn't generate a response." 