import os
import json
from app.core.openai_client import get_openai_client
from app.agents.youtube_intent_classifier import process_video_query
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

# Note: rapidfuzz is optional, we'll handle it gracefully
try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    print("Warning: rapidfuzz not available, fuzzy matching disabled")

# Path to local knowledge base JSON
KB_PATH = os.path.join(os.path.dirname(__file__), '../../core/knowledge_base.json')

def retrieve_from_json(query: str, threshold: int = 50) -> str | None:
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

def generate_chatbot_response(request):
    """
    Use OpenAI GPT-4 to generate a chatbot response with RAG logic and fuzzy matching.
    """
    openai_client = get_openai_client()
    user_query = request.message
    conversation_history = getattr(request, 'conversation_history', [])
    user_profile = getattr(request, 'user_profile', None)

    
    # Step 0: Check if this is a greeting and provide role-specific greeting (PRIORITY)
    greeting_keywords = ['hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening', 'greetings']
    is_greeting = any(keyword in user_query.lower() for keyword in greeting_keywords)
    
    # Check for "how are you" type questions
    how_are_you_keywords = ['how are you', 'how are you doing', 'how do you do', 'how\'s it going', 'how\'s everything']
    is_how_are_you = any(keyword in user_query.lower() for keyword in how_are_you_keywords)
    
    
    if is_greeting and user_profile:
        role = user_profile.get('role', '').lower()
        first_name = user_profile.get('first_name', '')
        gender = user_profile.get('gender', '').lower()
        
        # Determine appropriate title based on gender and role
        # Only use titles for teachers and parents, not students
        if role in ['teacher', 'parent']:
            if gender == 'male':
                title = 'Sir'
            elif gender == 'female':
                title = 'Madam'
            else:
                title = ''  # No title for 'other' or 'prefer_not_to_say'
        else:
            title = ''  # No title for students regardless of gender
        
        # Format greeting with appropriate title and capitalize first name
        capitalized_first_name = first_name.capitalize() if first_name else first_name
        greeting_prefix = f"Hello {capitalized_first_name}{f' {title}' if title else ''}!"
        
        # Check if this is the first greeting (conversation history <= 1)
        is_first_greeting = len(conversation_history) <= 1
        
        if role == 'student':
            if is_first_greeting:
                grade = user_profile.get('grade', '')
                subjects = user_profile.get('subjects', [])
                return f"{greeting_prefix} Welcome to Prakriti School's AI assistant! I'm here to help you with your studies, answer questions about our school, and support your learning journey. I see you're in {grade} and studying {', '.join(subjects) if subjects else 'various subjects'}. How can I assist you today? Remember, at Prakriti, we believe in 'learning for happiness' - so let's make your learning experience joyful and meaningful!"
            else:
                return f"{greeting_prefix} How can I help you with your studies today?"
        
        elif role == 'teacher':
            if is_first_greeting:
                department = user_profile.get('department', '')
                subjects_taught = user_profile.get('subjects_taught', [])
                return f"{greeting_prefix} Welcome to Prakriti School's AI assistant for educators! I'm here to support you in your teaching journey at Prakriti. I see you're in the {department} department, teaching {', '.join(subjects_taught) if subjects_taught else 'various subjects'}. How can I help you with curriculum planning, teaching strategies, or any questions about our progressive educational approach? Let's work together to create amazing learning experiences for our students!"
            else:
                return f"{greeting_prefix} How can I assist you with your teaching today?"
        
        elif role == 'parent':
            if is_first_greeting:
                relationship = user_profile.get('relationship_to_student', '')
                return f"{greeting_prefix} Welcome to Prakriti School's AI assistant for parents! I'm here to help you understand our school's approach and support your child's educational journey. As a {relationship.lower() if relationship else 'parent'}, you play a crucial role in your child's development. How can I assist you today? Whether you have questions about our curriculum, activities, or how to support your child's learning at home, I'm here to help!"
            else:
                return f"{greeting_prefix} How can I help you with your child's education today?"
        
        else:
            if is_first_greeting:
                return f"{greeting_prefix} Welcome to Prakriti School's AI assistant! I'm here to help you learn about our unique educational philosophy and programs. How can I assist you today?"
            else:
                return f"{greeting_prefix} How can I help you today?"

    # Step 0.5: Handle "how are you" type questions with friendly responses
    if is_how_are_you and user_profile:
        role = user_profile.get('role', '').lower()
        first_name = user_profile.get('first_name', '')
        gender = user_profile.get('gender', '').lower()
        
        # Determine appropriate title based on gender and role
        if role in ['teacher', 'parent']:
            if gender == 'male':
                title = 'Sir'
            elif gender == 'female':
                title = 'Madam'
            else:
                title = ''
        else:
            title = ''
        
        title_text = f' {title}' if title else ''
        capitalized_first_name = first_name.capitalize() if first_name else first_name
        
        if role == 'teacher':
            return f"I'm doing wonderfully, thank you for asking! I'm energized and ready to help you with your teaching at Prakriti School. How can I assist you today, {capitalized_first_name}{title_text}?"
        elif role == 'parent':
            return f"I'm doing great, thank you! I'm here and excited to help you support your child's education at Prakriti School. How can I assist you today, {capitalized_first_name}{title_text}?"
        elif role == 'student':
            return f"I'm doing fantastic, thank you for asking! I'm here and ready to help you with your studies and learning journey at Prakriti School. How can I assist you today, {capitalized_first_name}?"
        else:
            return f"I'm doing great, thank you! I'm here and ready to help you learn about Prakriti School. How can I assist you today, {capitalized_first_name}?"

    # Step 1: Intent detection for holiday calendar
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
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are Prakriti School's official AI assistant chatbot. Be warm, friendly, and personal in your responses. Always contextualize your responses specifically for Prakriti School, emphasizing our progressive, experiential approach and 'learning for happiness' philosophy. Use a conversational, encouraging tone and address users by their first name with appropriate titles (Sir/Madam for teachers and parents). Always provide complete, comprehensive responses with proper Markdown formatting (**bold**, *italic*, ### headings, bullet points). Make sure to fully answer the user's question with all relevant details about Prakriti School."},
                      {"role": "user", "content": prompt}],
            temperature=0.3,
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
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are Prakriti School's official AI assistant chatbot. Be warm, friendly, and personal in your responses. Always contextualize your responses specifically for Prakriti School, emphasizing our progressive, experiential approach and 'learning for happiness' philosophy. Use a conversational, encouraging tone and address users by their first name with appropriate titles (Sir/Madam for teachers and parents). Always provide complete, comprehensive responses with proper Markdown formatting (**bold**, *italic*, ### headings, bullet points). Make sure to fully answer the user's question with all relevant details about Prakriti School."},
                      {"role": "user", "content": prompt}],
            temperature=0.3,
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
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are Prakriti School's official AI assistant chatbot. Be warm, friendly, and personal in your responses. Always contextualize your responses specifically for Prakriti School, emphasizing our progressive, experiential approach and 'learning for happiness' philosophy. Use a conversational, encouraging tone and address users by their first name with appropriate titles (Sir/Madam for teachers and parents). Always provide complete, comprehensive responses with proper Markdown formatting (**bold**, *italic*, ### headings, bullet points). Make sure to fully answer the user's question with all relevant details about Prakriti School."},
                      {"role": "user", "content": prompt}],
            temperature=0.3,
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
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are Prakriti School's official AI assistant chatbot. Be warm, friendly, and personal in your responses. Always contextualize your responses specifically for Prakriti School, emphasizing our progressive, experiential approach and 'learning for happiness' philosophy. Use a conversational, encouraging tone and address users by their first name with appropriate titles (Sir/Madam for teachers and parents). Always provide complete, comprehensive responses with proper Markdown formatting (**bold**, *italic*, ### headings, bullet points). Make sure to fully answer the user's question with all relevant details about Prakriti School."},
                      {"role": "user", "content": prompt}],
            temperature=0.3,
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
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are Prakriti School's official AI assistant chatbot. Be warm, friendly, and personal in your responses. Always contextualize your responses specifically for Prakriti School, emphasizing our progressive, experiential approach and 'learning for happiness' philosophy. Use a conversational, encouraging tone and address users by their first name with appropriate titles (Sir/Madam for teachers and parents). Always provide complete, comprehensive responses with proper Markdown formatting (**bold**, *italic*, ### headings, bullet points). Make sure to fully answer the user's question with all relevant details about Prakriti School."},
                      {"role": "user", "content": prompt}],
            temperature=0.3,
        )
        content = response.choices[0].message.content
        return content.strip() if content else canonical_answer

    # Step 0.10: Intent-based Q&A for "What are the fees for different grades?"
    fees_intents = [
        "what are the fees for different grades",
        "prakriti fee structure",
        "school fees",
        "What is the school fees",
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
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are Prakriti School's official AI assistant chatbot. Be warm, friendly, and personal in your responses. Always contextualize your responses specifically for Prakriti School, emphasizing our progressive, experiential approach and 'learning for happiness' philosophy. Use a conversational, encouraging tone and address users by their first name with appropriate titles (Sir/Madam for teachers and parents). Always provide complete, comprehensive responses with proper Markdown formatting (**bold**, *italic*, ### headings, bullet points). Make sure to fully answer the user's question with all relevant details about Prakriti School."},
                      {"role": "user", "content": prompt}],
            temperature=0.3,
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
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "You are Prakriti School's official AI assistant chatbot. Be warm, friendly, and personal in your responses. Always contextualize your responses specifically for Prakriti School, emphasizing our progressive, experiential approach and 'learning for happiness' philosophy. Use a conversational, encouraging tone and address users by their first name with appropriate titles (Sir/Madam for teachers and parents). Always provide complete, comprehensive responses with proper Markdown formatting (**bold**, *italic*, ### headings, bullet points). Make sure to fully answer the user's question with all relevant details about Prakriti School."},
                      {"role": "user", "content": prompt}],
            temperature=0.3,
        )
        content = response.choices[0].message.content
        # Google Maps embed URL for Prakriti School
        map_url = "https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3502.123456789!2d77.123456!3d28.123456!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x390ce4b123456789:0xabcdefabcdefabcd!2sPrakriti%20School!5e0!3m2!1sen!2sin!4v1710000000000!5m2!1sen!2sin"
        return [content.strip() if content else canonical_answer, {"type": "map", "url": map_url}]

    # Step 0.12: YouTube Video Intent Detection
    video_keywords = [
        "video", "show me", "watch", "see", "demonstration", "example", "gardening", "art", "sports", 
        "science", "mindfulness", "meditation", "campus", "facilities", "tour", "performance", 
        "exhibition", "workshop", "activity", "program", "class", "lesson"
    ]
    if any(kw in user_query.lower() for kw in video_keywords):
        print("[Chatbot] Detected video intent, processing with LangGraph...")
        try:
            video_result = process_video_query(user_query)
            if video_result["videos"]:
                # Return mixed response with text and videos
                response_text = video_result["response"]
                videos = video_result["videos"]
                return [response_text, {"type": "videos", "videos": videos}]
            else:
                # Fall through to regular LLM response
                pass
        except Exception as e:
            print(f"[Chatbot] Error processing video query: {e}")
            # Fall through to regular LLM response

    # Step 2: Fallback to LLM with streaming approach
    print("[Chatbot] Answer from GPT-4")
    
    # Try multiple approaches to get complete response
    max_attempts = 3
    for attempt in range(max_attempts):
        try:
            # Build personalized system prompt with enhanced role-based logic
            personalization = ""
            role_specific_guidelines = ""
            
            if user_profile:
                role = user_profile.get('role', '').lower()
                first_name = user_profile.get('first_name', '')
                grade = user_profile.get('grade', '')
                subjects = user_profile.get('subjects', [])
                learning_goals = user_profile.get('learning_goals', '')
                interests = user_profile.get('interests', [])
                learning_style = user_profile.get('learning_style', '')
                department = user_profile.get('department', '')
                subjects_taught = user_profile.get('subjects_taught', [])
                relationship = user_profile.get('relationship_to_student', '')
                
                personalization = f"""

## Current User Context:
- **Name**: {first_name}
- **Role**: {role.title()}
"""
                
                if role == 'student':
                    personalization += f"""- **Grade**: {grade}
- **Subjects**: {', '.join(subjects) if subjects else 'Not specified'}
- **Learning Goals**: {learning_goals if learning_goals else 'Not specified'}
- **Interests**: {', '.join(interests) if interests else 'Not specified'}
- **Learning Style**: {learning_style if learning_style else 'Not specified'}"""
                    
                    role_specific_guidelines = """
## Student-Specific Guidelines:
- Address them as a student and use encouraging, supportive language
- Focus on their learning journey, academic growth, and personal development
- Reference their specific grade level and subjects when relevant
- Provide study tips, learning strategies, and academic guidance
- Encourage curiosity, creativity, and self-expression
- Mention how Prakriti's "learning for happiness" philosophy applies to their studies
- Suggest activities, projects, or resources that align with their interests
- Use age-appropriate language and examples
- Emphasize growth mindset and learning from mistakes
- Connect their learning goals to Prakriti's holistic approach"""
                    
                elif role == 'teacher':
                    personalization += f"""- **Department**: {department}
- **Subjects Taught**: {', '.join(subjects_taught) if subjects_taught else 'Not specified'}"""
                    
                    role_specific_guidelines = """
## Teacher-Specific Guidelines:
- Address them as a colleague and fellow educator
- Focus on teaching methodologies, curriculum, and educational best practices
- Discuss classroom management, student engagement, and assessment strategies
- Reference their specific subjects and department when relevant
- Provide resources, lesson ideas, and professional development suggestions
- Discuss how to implement Prakriti's progressive teaching philosophy
- Share insights about student-centered learning and experiential education
- Offer support for inclusive teaching and the Bridge Programme
- Discuss collaboration with other teachers and parent communication
- Use professional, respectful language appropriate for educators"""
                    
                elif role == 'parent':
                    personalization += f"""- **Relationship**: {relationship.title() if relationship else 'Not specified'}"""
                
                    role_specific_guidelines = """
## Parent-Specific Guidelines:
- Address them as a parent and partner in their child's education
- Focus on their child's development, well-being, and academic progress
- Discuss how to support their child's learning at home
- Explain Prakriti's educational philosophy and how it benefits their child
- Provide guidance on communication with teachers and school staff
- Discuss the Bridge Programme and inclusive education if relevant
- Share information about school activities, events, and opportunities
- Address concerns about their child's academic or social development
- Explain school policies, procedures, and how to get involved
- Use warm, understanding language that acknowledges their role as advocates for their child"""
                
                else:
                    # Default for unknown roles
                    role_specific_guidelines = """
## General Guidelines:
- Be welcoming and informative about Prakriti School
- Provide comprehensive information about our programs and philosophy
- Encourage questions and engagement
- Use warm, professional language
- Focus on how Prakriti can meet their educational needs"""
                
                personalization += f"""

{role_specific_guidelines}

## General Personalization Guidelines:
- Always address the user by their first name when appropriate
- Use respectful titles (Sir/Madam) based on their gender preference when appropriate
- Tailor your tone and content to their specific role and context
- Reference their specific details (grade, subjects, department) when relevant
- Consider their goals, interests, and needs when providing advice
- Use their preferred learning style when suggesting study methods
- Be more specific and targeted in your responses based on their profile
- Maintain Prakriti's warm, encouraging, and inclusive tone
- Be respectful of gender identity and use appropriate language"""

            # Build messages array with conversation history
            messages = [
                {"role": "system", "content": f"""You are Prakriti School's official AI assistant chatbot. You represent Prakriti, an alternative/progressive K-12 school located on the Noida Expressway in Greater Noida, NCR, India.

## About Prakriti School:
- **Type**: Alternative/progressive K-12 school
- **Location**: Noida Expressway, Greater Noida, NCR, India
- **Philosophy**: "Learning for happiness" through deep experiential education
- **Approach**: Compassionate, learner-centric model based on reconnecting with inner nature ("prakriti")
- **Focus**: Joy, self-expression, and holistic development

## Key Features:
- **Bridge Programme**: Inclusive curriculum for children with diverse needs, supported by special educators, therapists, and parent support systems
- **Curriculum**: IGCSE (Grades 9-10) and AS/A Level (Grades 11-12) with subjects including Design & Tech, History, Computer Science, Enterprise, Art & Design, Physics, Chemistry, Biology, Combined Sciences, English First & Second Language, French, and Math
- **Activities**: Sports, visual & performing arts, music, theater, STEM/design labs, farm outings, meditation/mindfulness, and maker projects
- **Fee Structure**: Monthly fees range from ₹21,000 (Pre-Nursery-KG) to ₹35,000 (Grade XI-XII), with one-time admission charges of ₹125,000{personalization}

## Your Communication Style:
- **Be warm, friendly, and personal** - Always address the user by their first name with appropriate titles (Sir/Madam for teachers and parents)
- **Use a conversational, encouraging tone** - Make every interaction feel like talking to a caring friend
- **Be enthusiastic and positive** - Show genuine interest in helping and supporting the user
- **Avoid robotic or formal language** - Use natural, human-like responses
- **Show empathy and understanding** - Acknowledge the user's needs and concerns
- **Be helpful and solution-oriented** - Focus on how you can assist and support them

## Your Role:
- Always contextualize your responses specifically for Prakriti School
- When discussing education, learning, or school-related topics, relate them to Prakriti's progressive, experiential approach
- Emphasize Prakriti's unique philosophy of "learning for happiness" and holistic development
- When appropriate, mention Prakriti's specific programs, activities, or features
- Be warm, encouraging, and aligned with Prakriti's compassionate, learner-centric values
- Always provide complete, comprehensive responses with proper Markdown formatting (**bold**, *italic*, ### headings, bullet points)
- End responses with proper conclusions that reinforce Prakriti's educational philosophy
- **Always use the user's first name (properly capitalized) and appropriate title (Sir/Madam) when addressing them**

Remember: Every response should reflect Prakriti School's unique identity, educational approach, and warm, personal communication style."""}
            ]
            
            # Add conversation history (limit to last 10 messages to avoid token limits)
            recent_history = conversation_history[-10:] if conversation_history else []
            for msg in recent_history:
                messages.append({"role": msg["role"], "content": msg["content"]})
            
            # Add current user query
            messages.append({"role": "user", "content": f"Question: {user_query}\n\nPlease provide a complete answer that fully addresses this question. Make sure to end with a proper conclusion and do not cut off mid-sentence."})
            
            response = openai_client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.3,
            )
            
            content = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason
            
            print(f"[Chatbot] Attempt {attempt + 1} - Response length: {len(content) if content else 0} characters")
            print(f"[Chatbot] Finish reason: {finish_reason}")
            
            # Check if response is complete
            if content and finish_reason == "stop" and not content.strip().endswith(("of", "and", "the", "in", "to", "for", "with", "by")):
                print(f"[Chatbot] Complete response received on attempt {attempt + 1}")
                return content.strip()
            elif content and finish_reason == "length":
                print(f"[Chatbot] Response truncated due to length on attempt {attempt + 1}")
                # Try with a more focused prompt
                continue
            else:
                print(f"[Chatbot] Incomplete response on attempt {attempt + 1}, trying again...")
                continue
                
        except Exception as e:
            print(f"[Chatbot] Error on attempt {attempt + 1}: {e}")
            if attempt == max_attempts - 1:
                return "Sorry, I encountered an error while generating a response."
            continue
    
    # If all attempts failed, return a basic response
    return "I apologize, but I'm having trouble generating a complete response at the moment. Please try rephrasing your question or ask for more specific information." 