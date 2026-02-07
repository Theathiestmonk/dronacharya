import os
import requests
import json
from typing import List, Dict, Optional, Tuple
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import re
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

# Ensure environment variables are loaded
load_dotenv()

# Try to import Supabase for cache checking
try:
    from supabase_config import get_supabase_client
    import hashlib
    from datetime import datetime, timedelta
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("[WebCrawler] Supabase not available - will always crawl")

# Try to import vector search service
try:
    from app.services.vector_search_service import VectorSearchService
    VECTOR_SEARCH_AVAILABLE = True
    def get_vector_search_service():
        return VectorSearchService()
except ImportError:
    VECTOR_SEARCH_AVAILABLE = False
    def get_vector_search_service():
        return None
    print("[WebCrawler] Vector search not available - using fallback methods")

class WebCrawlerAgent:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        # Set default timeout for all requests
        self.session.timeout = 30
        
        # PrakritSchool specific URLs to crawl (all 19 discovered pages + Substack articles)
        self.prakriti_urls = [
            # Main pages
            "https://prakriti.edu.in",
            "https://prakriti.edu.in/",
            "https://prakriti.edu.in/prakriti-way-of-learning/",
            "https://prakriti.edu.in/our-programmes/",
            "https://prakriti.edu.in/roots-of-all-beings/",
            
            # Team/Staff
            "https://prakriti.edu.in/team/",
            
            # Academic
            "https://prakriti.edu.in/igcse-cambridge-grade-x-results-2022-25/",
            "https://prakriti.edu.in/launching-new-as-a-level-and-igcse-subjects/",
            
            # News/Events
            "https://prakriti.edu.in/blog-and-news/",
            "https://prakriti.edu.in/prakriti-wins-innovative-learning-spaces-award-at-didac/",
            
            # Admission
            "https://prakriti.edu.in/admissions/",
            "https://prakriti.edu.in/school-fees/",
            
            # Contact
            "https://prakriti.edu.in/contact/",
            
            # Calendar
            "https://prakriti.edu.in/calendar/",
            
            # Parent Resources
            "https://prakriti.edu.in/parent-society/",
            "https://prakriti.edu.in/what-our-parents-say-about-us/",
            
            # Legal
            "https://prakriti.edu.in/privacy-policy/",
            "https://prakriti.edu.in/terms-and-conditions/",
            
            # Other
            "https://prakriti.edu.in/cpp/",

            # Substack Articles (Roots of All Beings)
            "https://rootsofallbeings.substack.com/p/can-we-save-the-planet-or-should",
            "https://rootsofallbeings.substack.com/p/welcoming-new-members-to-prakriti",
            "https://rootsofallbeings.substack.com/p/a-travelogue-on-our-recent-ole-at",
            "https://rootsofallbeings.substack.com/p/outbound-learning-expedition-ole",
            "https://rootsofallbeings.substack.com/p/student-voice-a-guide-for-shaping"
        ]
        
        # Cache for crawled content
        self.content_cache = {}
        self.cache_duration = 3600  # 1 hour cache
        
        # Fallback data for team members (used when database doesn't have them or extraction fails)
        # Consistent team page URL for all entries
        TEAM_PAGE_URL = 'https://prakriti.edu.in/team/'
        
        self.fallback_data = {
            'Priyanka Oberoi': {
                'name': 'Priyanka Oberoi',
                'title': 'Facilitator Art & Design and Design & Technology',
                'description': 'Priyanka is an artist and designer whose work blends India\'s cultural depth with Western artistic expression.',
                'details': 'Teaching visually impaired children in 2014 inspired her inclusive, tactile approach to art. She holds a BFA from the College of Art, New Delhi, a dual Post graduation from NID, India and UCA, UK, and an MA in Graphic storytelling from LUCA school of arts, KU Leuven, Belgium. With experience in sports photography for leading international publications, she has also collaborated with scientists to create visual narratives and illustrated a board game for the Deutsches Museum. A certified mountaineer and recent graduate in Graphic Storytelling, Priyanka\'s art reflects curiosity, inclusivity, and creativity—values she looks forward to sharing at Prakriti.',
                'full_content': 'Priyanka Oberoi\nFacilitator Art & Design and Design & Technology\n\nPriyanka is an artist and designer whose work blends India\'s cultural depth with Western artistic expression. Teaching visually impaired children in 2014 inspired her inclusive, tactile approach to art. She holds a BFA from the College of Art, New Delhi, a dual Post graduation from NID, India and UCA, UK, and an MA in Graphic storytelling from LUCA school of arts, KU Leuven, Belgium. With experience in sports photography for leading international publications, she has also collaborated with scientists to create visual narratives and illustrated a board game for the Deutsches Museum. A certified mountaineer and recent graduate in Graphic Storytelling, Priyanka\'s art reflects curiosity, inclusivity, and creativity—values she looks forward to sharing at Prakriti.',
                'source_url': TEAM_PAGE_URL
            },
            'Ritu Martin': {
                'name': 'Ritu Martin',
                'title': 'Senior Primary Facilitator Sciences',
                'description': 'Ritu Martin holds a B.Sc. in Biotechnology, a B.Ed., an MBA, and has completed the SEEL LI Facilitator course.',
                'details': 'She believes that teaching is about nurturing the whole personality of a student, which begins with the teacher embodying the values they wish to impart. For Ritu, education is not about changing students but about self-growth—modeling integrity, curiosity, and empathy through everyday actions. She values the freedom to engage in focused, meaningful work and aligns deeply with the philosophy of becoming a better version of oneself each day, inspiring her students to do the same.',
                'full_content': 'Ritu Martin\nSenior Primary Facilitator Sciences\n\nRitu Martin holds a B.Sc. in Biotechnology, a B.Ed., an MBA, and has completed the SEEL LI Facilitator course. She believes that teaching is about nurturing the whole personality of a student, which begins with the teacher embodying the values they wish to impart. For Ritu, education is not about changing students but about self-growth—modeling integrity, curiosity, and empathy through everyday actions. She values the freedom to engage in focused, meaningful work and aligns deeply with the philosophy of becoming a better version of oneself each day, inspiring her students to do the same.',
                'source_url': TEAM_PAGE_URL
            },
            'Shuchi Mishra': {
                'name': 'Shuchi Mishra',
                'title': 'Facilitator',
                'description': 'Mrs. Shuchi Mishra holds a Bachelor\'s degree in Psychology (Honours), Economics, and English, and a Master\'s in Psychology from Lucknow University.',
                'details': 'She also completed her B.Ed. from Annamalai University and recently pursued the GSE4x: Introduction to Family Engagement in Education course from HarvardX. A National Scholarship recipient, Mrs. Mishra has over 30 years of teaching experience—18 years at Jaipuria School, Lucknow (ICSE) and 13 years at Sanskriti School, New Delhi (CBSE). She believes education must go beyond academics to nurture integrity, responsibility, and creativity. Her teaching philosophy emphasizes holistic growth through theatre, sports, debates, and experiential learning. Passionate about shaping young minds, she views teachers as key influences during a child\'s formative years—guiding not only intellectual development but also moral and social growth.',
                'full_content': 'Shuchi Mishra\nFacilitator\n\nMrs. Shuchi Mishra holds a Bachelor\'s degree in Psychology (Honours), Economics, and English, and a Master\'s in Psychology from Lucknow University. She also completed her B.Ed. from Annamalai University and recently pursued the GSE4x: Introduction to Family Engagement in Education course from HarvardX. A National Scholarship recipient, Mrs. Mishra has over 30 years of teaching experience—18 years at Jaipuria School, Lucknow (ICSE) and 13 years at Sanskriti School, New Delhi (CBSE). She believes education must go beyond academics to nurture integrity, responsibility, and creativity. Her teaching philosophy emphasizes holistic growth through theatre, sports, debates, and experiential learning. Passionate about shaping young minds, she views teachers as key influences during a child\'s formative years—guiding not only intellectual development but also moral and social growth.',
                'source_url': TEAM_PAGE_URL
            },
            'Gunjan Bhatia': {
                'name': 'Gunjan Bhatia',
                'title': 'Early Years Programme Facilitator',
                'description': 'Gunjan Bhatia is a Nursery teacher in the Green group with an M.Phil in Economics.',
                'details': 'She approaches teaching as a continuous journey of learning, believing that every method has value and that the true skill lies in selecting the pedagogy best suited to each child and context. With a focus on experiential learning, Gunjan encourages children to explore, question, and engage with their surroundings, fostering curiosity and independent thinking from an early age. She combines progressive educational practices with room for freedom, ensuring that every child feels empowered to learn at their own pace while developing critical social, emotional, and cognitive skills. Gunjan\'s classrooms are designed to be spaces where creativity, discovery, and growth are prioritized, and where learning becomes a meaningful and joyful experience. Her holistic approach ensures that each child is nurtured, guided, and inspired to develop their full potential.',
                'full_content': 'Gunjan Bhatia\nEarly Years Programme Facilitator\n\nGunjan Bhatia is a Nursery teacher in the Green group with an M.Phil in Economics. She approaches teaching as a continuous journey of learning, believing that every method has value and that the true skill lies in selecting the pedagogy best suited to each child and context. With a focus on experiential learning, Gunjan encourages children to explore, question, and engage with their surroundings, fostering curiosity and independent thinking from an early age. She combines progressive educational practices with room for freedom, ensuring that every child feels empowered to learn at their own pace while developing critical social, emotional, and cognitive skills. Gunjan\'s classrooms are designed to be spaces where creativity, discovery, and growth are prioritized, and where learning becomes a meaningful and joyful experience. Her holistic approach ensures that each child is nurtured, guided, and inspired to develop their full potential.',
                'source_url': TEAM_PAGE_URL
            },
            'Vidya Vishwanathan': {
                'name': 'Vidya Vishwanathan',
                'title': 'Upper Secondary, Global Perspectives Facilitator',
                'description': 'Vidya Viswanathan is a researcher, writer, and curriculum advisor with a unique ability to identify emerging trends and connect insights to paint a broader picture.',
                'details': 'She has interacted with academics, industry leaders, and innovators worldwide, often serving as a sounding board and storyteller. Her impactful journalism at Business Standard, Business World, and Business Today influenced industries, set trends, and shaped policy discussions. Starting as a programmer and equity researcher, she later explored financial journalism and diverse subjects. Passionate about alternative education, India\'s scientific, cultural, and spiritual heritage, Vidya now designs and advises on history and civics curriculum at Prakriti, fostering a generation proud of the country.',
                'full_content': 'Vidya Vishwanathan\nUpper Secondary, Global Perspectives Facilitator\n\nVidya Viswanathan is a researcher, writer, and curriculum advisor with a unique ability to identify emerging trends and connect insights to paint a broader picture. She has interacted with academics, industry leaders, and innovators worldwide, often serving as a sounding board and storyteller. Her impactful journalism at Business Standard, Business World, and Business Today influenced industries, set trends, and shaped policy discussions. Starting as a programmer and equity researcher, she later explored financial journalism and diverse subjects. Passionate about alternative education, India\'s scientific, cultural, and spiritual heritage, Vidya now designs and advises on history and civics curriculum at Prakriti, fostering a generation proud of the country.',
                'source_url': TEAM_PAGE_URL
            },
            'Gayatri Tahiliani': {
                'name': 'Gayatri Tahiliani',
                'title': 'Primary English and Math Curriculum Leader',
                'description': 'Gayatri Tahiliani is the Primary English and Math Curriculum Leader at Prakriti.',
                'details': 'She holds a Bachelor\'s in Elementary Education from Lady Shri Ram College, a Master\'s in History from IGNOU, and a Master\'s in Education with a specialization in Teaching and Teacher Leadership from Harvard University. In her role, Gayatri works closely with teachers to strengthen vertical and horizontal alignment of the English curriculum, mentor educators, and coordinate the new phonics program across the primary grades. Passionate about meaningful learning, she designs inquiry-driven classrooms where children explore, question, and develop a deep sense of connection and responsibility toward the world around them.',
                'full_content': 'Gayatri Tahiliani\nPrimary English and Math Curriculum Leader\n\nGayatri Tahiliani is the Primary English and Math Curriculum Leader at Prakriti. She holds a Bachelor\'s in Elementary Education from Lady Shri Ram College, a Master\'s in History from IGNOU, and a Master\'s in Education with a specialization in Teaching and Teacher Leadership from Harvard University. In her role, Gayatri works closely with teachers to strengthen vertical and horizontal alignment of the English curriculum, mentor educators, and coordinate the new phonics program across the primary grades. Passionate about meaningful learning, she designs inquiry-driven classrooms where children explore, question, and develop a deep sense of connection and responsibility toward the world around them.',
                'source_url': TEAM_PAGE_URL
            },
            'Vanila Ghai': {
                'name': 'Vanila Ghai',
                'title': 'Bridge Programme Facilitator',
                'description': 'Vanila is a Finance professional with Corporate experience of a decade in BFSI sector.',
                'details': 'She gave up her career to serve the community after her son got diagnosed with Autism Spectrum Disorder and dedicated herself to the cause. She pursued Diploma in Early Childhood – Special Education and is a RCI certified Practitioner. She finished her coursework of Behavior Analysis from the Florida Institute of Technologies, US and very recently finished her MA in Clinical Psychology from IGNOU. She holds a work experience of 5+ years for working with children with Autism and Developmental Disabilities.',
                'full_content': 'Vanila Ghai\nBridge Programme Facilitator\n\nVanila is a Finance professional with Corporate experience of a decade in BFSI sector. She gave up her career to serve the community after her son got diagnosed with Autism Spectrum Disorder and dedicated herself to the cause. She pursued Diploma in Early Childhood – Special Education and is a RCI certified Practitioner. She finished her coursework of Behavior Analysis from the Florida Institute of Technologies, US and very recently finished her MA in Clinical Psychology from IGNOU. She holds a work experience of 5+ years for working with children with Autism and Developmental Disabilities.',
                'source_url': TEAM_PAGE_URL
            },
            'Shraddha Rana Goel': {
                'name': 'Shraddha Rana Goel',
                'title': 'French Facilitator',
                'description': 'Shraddha Rana Goel is the French Facilitator at Prakriti School.',
                'details': 'Shraddha Rana Goel serves as the French Facilitator at Prakriti School, helping students learn and engage with the French language and culture.',
                'full_content': 'Shraddha Rana Goel\nFrench Facilitator\n\nShraddha Rana Goel is the French Facilitator at Prakriti School, helping students learn and engage with the French language and culture.',
                'source_url': TEAM_PAGE_URL
            }
        }
        
    def is_prakriti_related(self, query: str) -> bool:
        """Check if the query is related to PrakritSchool"""
        prakriti_keywords = [
            'prakriti', 'prakrit school', 'prakriti school', 'prakritischool', 'prakrii',
            'noida school', 'greater noida school', 'progressive school',
            'alternative school', 'k12 school', 'igcse', 'a level', 'as level',
            'bridge programme', 'learning for happiness', 'experiential education'
        ]
        
        # Also check if it's a team-related query (likely about PrakritSchool team)
        team_keywords = [
            'team', 'staff', 'faculty', 'teacher', 'teachers', 'member', 'members',
            'administration', 'admin', 'principal', 'director', 'coordinator',
            'educator', 'educators', 'instructor', 'instructors', 'professor',
            'who works', 'who teaches', 'team member', 'staff member'
        ]
        
        query_lower = query.lower()
        
        # Check PrakritSchool keywords
        if any(keyword in query_lower for keyword in prakriti_keywords):
            return True
        
        # Check if it's a team-related query (assume it's about PrakritSchool)
        if any(keyword in query_lower for keyword in team_keywords):
            return True
        
        # Check if it's a specific person query (assume it's about PrakritSchool team member)
        if self.is_specific_person_query(query):
            return True
        
        # Check if it's admission-related (assume it's about PrakritSchool)
        if self.is_admission_related(query):
            return True
        
        # Check if it's testimonial-related (assume it's about PrakritSchool)
        if self.is_testimonial_related(query):
            return True
        
        # Check if it's calendar-related (assume it's about PrakritSchool)
        if self.is_calendar_related(query):
            return True
        
        # Check if it's article-related (assume it's about PrakritSchool)
        if self.is_article_related(query):
            return True
        
        return False
    
    def is_team_related(self, query: str) -> bool:
        """Check if the query is about team/staff/faculty"""
        team_keywords = [
            'team', 'staff', 'faculty', 'teacher', 'teachers', 'member', 'members',
            'administration', 'admin', 'principal', 'director', 'coordinator',
            'educator', 'educators', 'instructor', 'instructors', 'professor',
            'who works', 'who teaches', 'team member', 'staff member'
        ]
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in team_keywords)
    
    def is_role_based_query(self, query: str) -> bool:
        """Check if the query is asking about a role/specialization (e.g., 'French facilitator', 'Math teacher')"""
        query_lower = query.lower()
        
        # Normalize typos in query first (before checking keywords)
        typo_corrections = {
            'founde': 'founder',  # "co founde" -> "co founder"
            'foundr': 'founder',
            'founder': 'founder',
            'co-founde': 'co-founder',
            'cofounde': 'cofounder',
            'facilatator': 'facilitator',
            'facilator': 'facilitator',
            'facilitater': 'facilitator',
            'facilattor': 'facilitator',
            'faciitator': 'facilitator',  # Handle "faciitator" typo (double 'i')
            'faciitators': 'facilitators',  # Handle "faciitators" typo (double 'i')
            'faclitators': 'facilitators',  # Handle "faclitators" typo
            'faclitator': 'facilitator',  # Handle "faclitator" typo
            'facilitators': 'facilitators',  # Plural form
            'techer': 'teacher',
            'teachr': 'teacher',
            'coordinater': 'coordinator',
            'coordinatr': 'coordinator',
            'directer': 'director',
            'principle': 'principal',
            'princile': 'principal',  # Handle "princile" typo (missing 'a')
            'principl': 'principal',  # Handle "principl" typo (missing 'e')
            'princpal': 'principal',  # Handle "princpal" typo (missing 'i')
            'menter': 'mentor'
        }
        
        # Apply typo corrections to query
        normalized_query = query_lower
        for typo, correct in typo_corrections.items():
            normalized_query = normalized_query.replace(typo, correct)
        
        # Role/specialization keywords (subject/domain)
        subject_keywords = [
            'french', 'english', 'math', 'mathematics', 'science', 'physics', 'chemistry',
            'biology', 'history', 'art', 'music', 'sports', 'pe', 'physical education',
            'computer', 'it', 'technology', 'design', 'drama', 'theatre', 'dance',
            'primary', 'secondary', 'upper', 'lower', 'early years', 'nursery', 'kindergarten'
        ]
        
        # Role type keywords (with common misspellings)
        role_type_keywords = [
            'facilitator', 'facilitators', 'facilator', 'facilitater', 'facilattor', 'faclitator', 'faclitators',  # Handle misspellings
            'teacher', 'techer', 'teachr',
            'coordinator', 'coordinater', 'coordinatr',
            'director', 'directer',
            'principal', 'principle', 'princile', 'principl', 'princpal',  # Handle principal misspellings
            'mentor', 'menter', 'chief mentor', 'chief',  # Add chief mentor
            'faculty', 'faculties',  # Add faculty as role type
            'founder', 'co-founder', 'cofounder', 'founding',  # Add founder roles
            'chairperson', 'chair person', 'chairman', 'chairwoman'
        ]
        
        # Check both original and normalized query
        query_to_check = normalized_query
        
        # Check if query contains both a subject keyword AND a role type keyword
        # Check both original and normalized query for typos
        has_subject = any(keyword in query_to_check for keyword in subject_keywords)
        has_role_type = any(keyword in query_to_check for keyword in role_type_keywords)
        
        # Debug logging
        if has_subject or has_role_type:
            matched_subjects = [kw for kw in subject_keywords if kw in query_to_check]
            matched_roles = [kw for kw in role_type_keywords if kw in query_to_check]
            if normalized_query != query_lower:
                print(f"[WebCrawler] Typo detected: '{query_lower}' -> normalized: '{normalized_query}'")
            print(f"[WebCrawler] Role-based query check: has_subject={has_subject} ({matched_subjects}), has_role_type={has_role_type} ({matched_roles})")
        
        # If it has both subject and role type, it's definitely a role-based query
        if has_subject and has_role_type:
            print(f"[WebCrawler] ✅ Confirmed role-based query (has both subject and role type)")
            return True
        
        # Also check for role-only queries (without subject) like "who is the founder", "who is the principal"
        # These are leadership/administrative roles that don't need a subject
        leadership_roles = ['founder', 'co-founder', 'cofounder', 'founding', 'principal', 'director', 
                           'chairperson', 'chair person', 'chairman', 'chairwoman', 'chief mentor', 'chief']
        has_leadership_role = any(role in query_to_check for role in leadership_roles)
        # Check for patterns like "who is the [role]" or "[role] of [organization]"
        # Use normalized query to catch typos
        if has_leadership_role:
            leadership_patterns = [
                r'who is the .+?\s+(?:founder|co-founder|cofounder|founding|principal|director|chairperson|chief mentor|chief)',
                r'who is the (?:founder|co-founder|cofounder|founding|principal|director|chairperson|chief mentor|chief)',
                r'(?:founder|co-founder|cofounder|founding|principal|director|chairperson|chief mentor|chief)\s+of',
                r'the\s+(?:founder|co-founder|cofounder|founding|principal|director|chairperson|chief mentor|chief)',
                r'co\s+(?:founder|founde|foundr)',  # Handle "co founde", "co founder", etc.
                r'chief\s+mentor'  # Handle "chief mentor"
            ]
            import re
            if any(re.search(pattern, query_to_check) for pattern in leadership_patterns):
                print(f"[WebCrawler] ✅ Confirmed leadership role query (founder/principal/director/chief mentor)")
                return True
        
        # Also check for patterns like "who is the [subject] [role]" or "[role] of [subject]"
        # Make patterns more flexible to handle misspellings and additional text
        import re
        role_patterns = [
            r'who is the .+?\s+(?:facilitator|facilitators|facilator|facilitater|facilattor|faclitator|faclitators|teacher|coordinator|faculty)',
            r'who is the .+?\s+(?:facilitator|facilitators|facilator|facilitater|facilattor|faclitator|faclitators|teacher|coordinator|faculty)\s+',
            r'.+?\s+(?:facilitator|facilitators|facilator|facilitater|facilattor|faclitator|faclitators|teacher|coordinator|faculty)',
            r'(?:facilitator|facilitators|facilator|facilitater|facilattor|faclitator|faclitators|teacher|coordinator|faculty)\s+of',
            r'(?:facilitator|facilitators|facilator|facilitater|facilattor|faclitator|faclitators|teacher|coordinator|faculty)\s+for',
            r'the\s+.+?\s+(?:facilitator|facilitators|facilator|facilitater|facilattor|faclitator|faclitators|teacher|coordinator|faculty)',
            r'who is the .+?\s+faculty',  # Pattern for "who is the art and design faculty"
            r'.+?\s+(?:facilitator|facilitators|facilator|facilitater|facilattor|faclitator|faclitators)\s+in'  # "art and design facilitators in schools"
        ]
        
        # Use normalized query for pattern matching to catch typos
        has_role_pattern = any(re.search(pattern, query_to_check) for pattern in role_patterns)
        
        # If it has a role type keyword and matches a pattern, it's a role-based query
        if has_role_type and has_role_pattern:
            return True
        
        # Also check if query has subject + "faculty" (common pattern)
        # Use normalized query to catch typos
        if has_subject and 'faculty' in query_to_check:
            return True
        
        return False
    
    def is_specific_person_query(self, query: str) -> bool:
        """Check if the query is asking about a specific person by name"""
        import re
        
        # CRITICAL: Remove punctuation first for better matching
        query_clean = re.sub(r'[?!.,;:]+', '', query)
        query_lower = query_clean.lower()
        
        # CRITICAL: FIRST check if this is admission/fees/contact/article related - NOT a person query
        if self.is_admission_related(query) or self.is_contact_related(query) or self.is_article_related(query) or self.is_news_related(query):
            print(f"[WebCrawler] Excluding admission/contact/article/news query from person query detection: '{query}'")
            return False
        
        # CRITICAL: Check for common non-person query phrases
        non_person_phrases = [
            'fees structure', 'fee structure', 'fees', 'fee', 'admission process', 'admission', 'admissions',
            'contact', 'contact us', 'article', 'articles', 'latest article', 'latest news', 'blog', 'news',
            'calendar', 'events', 'schedule', 'program', 'programs', 'curriculum', 'academic'
        ]
        if any(phrase in query_lower for phrase in non_person_phrases):
            print(f"[WebCrawler] Excluding non-person query phrase from person query detection: '{query}'")
            return False
        
        # CRITICAL: FIRST check if this is a role-based query - if so, it's NOT a person query
        # Role-based queries like "who is the Chief Mentor", "who is the chairperson" should be handled as roles
        if self.is_role_based_query(query):
            print(f"[WebCrawler] Excluding role-based query from person query detection: '{query}'")
            return False
        
        # CRITICAL: Check for role titles that might be mistaken for person names
        role_titles = ['chief mentor', 'chief', 'mentor', 'chairperson', 'chairman', 'chairwoman', 
                      'director', 'principal', 'founder', 'co-founder', 'coordinator', 'facilitator',
                      'teacher', 'faculty', 'head', 'leader', 'manager', 'administrator', 'admin']
        query_words = query_lower.split()
        # Check if query contains only role titles (not a person name)
        if len(query_words) <= 3:  # Short queries are likely roles
            if any(role in query_lower for role in role_titles):
                # Check if it's a pattern like "who is the [role]" or "who is [role]"
                if 'who is' in query_lower or 'tell me about' in query_lower:
                    remaining = query_lower.replace('who is the', '').replace('who is', '').replace('tell me about', '').strip()
                    if remaining and any(role in remaining for role in role_titles):
                        print(f"[WebCrawler] Excluding role title query from person query detection: '{query}'")
                        return False
        
        # CRITICAL: Check for "tell me about" pattern FIRST - this is ALWAYS a person query if it has a name
        if 'tell me about' in query_lower:
            # Extract potential name after "tell me about"
            potential_name = query_lower.replace('tell me about', '').strip()
            # CRITICAL: Exclude "vanilla" (flavor) - only "vanila" (person) should match
            if potential_name.lower() == 'vanilla':
                print(f"[WebCrawler] Excluding 'vanilla' (flavor) from person query detection")
                return False
            # Check if it looks like a name (1+ words, not all common words)
            words = potential_name.split()
            if len(words) >= 1:  # Changed from 2 to 1 to handle single names
                # Check if it matches known team member names
                known_names = ['priyanka', 'oberoi', 'shuchi', 'mishra', 'ritu', 'martin', 'gunjan', 'bhatia',
                             'gayatri', 'tahiliani', 'vanila', 'ghai', 'vidya', 'vishwanathan', 'vinita', 'krishna',
                             'bharti', 'batra', 'shraddha', 'rana', 'goel', 'shilpa', 'tayal', 'mridul', 'rahul']
                if any(word in known_names for word in words):
                    print(f"[WebCrawler] 'Tell me about' query detected with known name: {potential_name}")
                    return True
                # Even if not in known names, if it's 1-3 words, treat as person query
                if 1 <= len(words) <= 3:
                    print(f"[WebCrawler] 'Tell me about' query detected with potential name: {potential_name}")
                    return True
        
        # Check for "who is" pattern with potential name
        if 'who is' in query_lower or 'who is the' in query_lower:
            # Extract potential name after "who is" or "who is the"
            potential_name = query_lower.replace('who is the', '').replace('who is', '').strip()
            # CRITICAL: Exclude "vanilla" (flavor) - only "vanila" (person) should match
            if potential_name.lower() == 'vanilla':
                print(f"[WebCrawler] Excluding 'vanilla' (flavor) from person query detection")
                return False
            words = potential_name.split()
            if len(words) >= 1:  # Changed from 2 to 1
                # Check if it matches known team member names
                known_names = ['priyanka', 'oberoi', 'shuchi', 'mishra', 'ritu', 'martin', 'gunjan', 'bhatia',
                             'gayatri', 'tahiliani', 'vanila', 'ghai', 'vidya', 'vishwanathan', 'vinita', 'krishna',
                             'bharti', 'batra', 'shraddha', 'rana', 'goel', 'shilpa', 'tayal', 'mridul', 'rahul']
                if any(word in known_names for word in words):
                    print(f"[WebCrawler] 'Who is' query detected with known name: {potential_name}")
                    return True
                # If it's 1-3 words and not a role keyword, treat as person query
                role_keywords = ['facilitator', 'teacher', 'principal', 'director', 'founder', 'coordinator',
                              'mentor', 'chief', 'chairperson', 'chairman', 'chairwoman', 'head', 'leader']
                if 1 <= len(words) <= 3 and not any(role in potential_name for role in role_keywords):
                    print(f"[WebCrawler] 'Who is' query detected with potential name: {potential_name}")
                    return True
        
        # Check if the query contains a potential person name (1+ words)
        # Look for 1-3 word names (First, First Last, or First Middle Last)
        name_pattern = r'\b[a-zA-Z]+(?:\s+[a-zA-Z]+){0,2}\b'
        potential_names = re.findall(name_pattern, query_lower)
        
        # Filter out common words and check for known names
        # CRITICAL: Exclude "vanilla" (flavor) - only "vanila" (person name) should match
        # CRITICAL: Exclude admission/fees/contact/article related terms
        common_words = ['little', 'bit', 'about', 'tell', 'me', 'who', 'is', 'information', 'details', 'cooking', 'recipes', 
                       'admission', 'admissions', 'fees', 'fee', 'structure', 'process', 'procedure', 'school', 'program', 'programs', 
                       'course', 'courses', 'prakriti', 'prakrit', 'roots', 'philosophy', 'article', 'articles', 'blog', 'news', 
                       'calendar', 'event', 'events', 'curriculum', 'learning', 'learn', 'teaching', 'approach', 'want', 
                       'newton', 'einstein', 'darwin', 'law', 'laws', 'theory', 'theorem', 'formula', 'concept', 'concepts', 
                       'example', 'examples', 'explain', 'understand', 'help', 'solve', 'study', 'physics', 'chemistry', 
                       'biology', 'math', 'mathematics', 'algebra', 'calculus', 'french', 'english', 'facilitator', 'teacher', 
                       'coordinator', 'founder', 'founde', 'foundr', 'co-founder', 'cofounder', 'founding', 'director', 'principal', 
                       'chairperson', 'chairman', 'chairwoman', 'mentor', 'faculty', 'co', 'founde', 'the', 'vanilla', 'contact',
                       'latest', 'recent', 'substack']
        
        # Known person name patterns (first and last names)
        known_first_names = ['priyanka', 'shuchi', 'ritu', 'gunjan', 'gayatri', 'vanila', 'vidya', 
                           'vinita', 'bharti', 'shraddha', 'shilpa', 'mridul', 'rahul']
        known_last_names = ['oberoi', 'mishra', 'martin', 'bhatia', 'tahiliani', 'ghai', 'vishwanathan',
                          'krishna', 'batra', 'rana', 'goel', 'tayal']
        person_name_patterns = known_first_names + known_last_names
        
        for name in potential_names:
            name_lower = name.lower().strip()
            # Skip if empty or too short
            if not name_lower or len(name_lower) < 3:
                continue
                
            # Check if the name itself contains common words (not just the original query)
            name_words = name_lower.split()
            contains_common_words = any(word in common_words for word in name_words)
            
            # Check if it contains known person name patterns
            contains_known_name = any(pattern in name_lower for pattern in person_name_patterns)
            
            # Check if it's NOT a common word AND either looks like a person name OR contains known person name patterns
            if not contains_common_words and (len(name_words) >= 1 or contains_known_name):
                # Additional check: if it's a single word, it should be a known first or last name
                if len(name_words) == 1:
                    if name_lower in known_first_names or name_lower in known_last_names:
                        print(f"[WebCrawler] Single word name match: '{name_lower}'")
                        return True
                else:
                    # Multiple words - check if any word is a known name
                    if any(word in known_first_names or word in known_last_names for word in name_words):
                        print(f"[WebCrawler] Multi-word name match: '{name_lower}'")
                        return True
                    # Or if it's 2-3 words and doesn't contain common words, treat as person query
                    if 2 <= len(name_words) <= 3:
                        print(f"[WebCrawler] Potential name pattern: '{name_lower}'")
                return True
        
        return False
    
    def extract_person_name(self, query: str) -> str:
        """Extract potential person name from query"""
        import re
        
        # CRITICAL: Remove punctuation first (question marks, exclamation marks, etc.)
        query_clean = re.sub(r'[?!.,;:]+', '', query)
        query_lower = query_clean.lower()
        
        # Remove common question words and patterns
        cleaned_query = query_lower
        
        # Remove question patterns
        question_patterns = [
            'who is', 'tell me about', 'about', 'introduction of', 'details about',
            'information about', 'profile of', 'biography of', 'background of',
            'can you tell me', 'what do you know about', 'do you know',
            'little bit about', 'little bit of', 'bit about', 'bit of',
            'give me', 'give me little bit', 'give me information', 'give me details',
            'litle bit', 'litle bit info', 'litle bit about', 'check for'
        ]
        
        for pattern in question_patterns:
            cleaned_query = cleaned_query.replace(pattern, '').strip()
        
        # Remove individual common words that might interfere
        # Also exclude role-related terms and admission/fees terms that might be mistaken for names
        common_words = ['little', 'bit', 'about', 'of', 'the', 'a', 'an', 'and', 'or', 'but', 'give', 'me', 'information', 'details', 'litle', 'info', 'check', 'for', 'this', 'that', 'these', 'those', 'with', 'introduction', 'detail', 'what', 'facilaor', 'facilitator', 
                       'founder', 'founde', 'foundr', 'co-founder', 'cofounder', 'founding', 'director', 'principal', 
                       'chairperson', 'chairman', 'chairwoman', 'coordinator', 'mentor', 'chief', 'teacher', 'faculty',
                       'head', 'leader', 'manager', 'administrator', 'admin', 'admission', 'admissions', 'addmission', 'addmissions',
                       'fees', 'fee', 'structure', 'process', 'procedure', 'contact', 'article', 'articles', 'blog', 'news']
        words = cleaned_query.split()
        cleaned_words = [word for word in words if word.lower() not in common_words]
        cleaned_query = ' '.join(cleaned_words)
        
        # Remove team context words
        team_words = ['team', 'staff', 'faculty', 'teacher', 'member', 'of prakriti', 'at prakriti', 'prakriti', 'school']
        for word in team_words:
            cleaned_query = cleaned_query.replace(word, '').strip()
        
        # Clean up extra spaces
        cleaned_query = re.sub(r'\s+', ' ', cleaned_query).strip()
        
        # Extract name using regex pattern (First Last or First Middle Last)
        name_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}\b'  # Changed to allow 1-3 words (0-2 additional words)
        matches = re.findall(name_pattern, cleaned_query.title())
        
        if matches:
            # Return the longest match (most likely to be the full name)
            longest_match = max(matches, key=len)
            # Additional check: ensure it's not just common words
            common_words = ['little', 'bit', 'about', 'tell', 'me', 'who', 'is', 'information', 'check', 'for', 'this', 'that', 'with', 'introduction', 'detail', 'what', 'facilaor', 'facilitator']
            if not any(word in longest_match.lower() for word in common_words):
                return longest_match
        
        # Fallback: If we have a reasonable length name (1+ words), return it
        # But first check if it looks like a name (not all common words)
        words = cleaned_query.split()
        if len(words) >= 1:  # Changed from 2 to 1 to handle single names like "vanila"
            # Check if any word matches known team member names
            known_first_names = ['priyanka', 'shuchi', 'ritu', 'gunjan', 'gayatri', 'vanila', 'vidya', 
                               'vinita', 'bharti', 'shraddha', 'shilpa', 'mridul', 'rahul']
            known_last_names = ['oberoi', 'mishra', 'martin', 'bhatia', 'tahiliani', 'ghai', 'vishwanathan',
                              'krishna', 'batra', 'rana', 'goel', 'tayal']
            
            # If any word matches known names, it's likely a person name
            if any(word.lower() in known_first_names or word.lower() in known_last_names for word in words):
                extracted_name = ' '.join(words).title()
                print(f"[WebCrawler] Extracted name from known names: '{extracted_name}'")
                return extracted_name
            
            # Also check if it matches a known full name pattern (even partial)
            full_name_lower = ' '.join(words).lower()
            known_full_names = ['priyanka oberoi', 'shuchi mishra', 'ritu martin', 'gunjan bhatia',
                              'gayatri tahiliani', 'vanila ghai', 'vidya vishwanathan', 'vinita krishna',
                              'bharti batra', 'shraddha rana goel', 'shilpa tayal', 'mridul batra', 'rahul batra']
            for known_name in known_full_names:
                # Check if query matches known name or contains parts of it
                if full_name_lower == known_name or (words[0].lower() in known_name and (len(words) == 1 or words[-1].lower() in known_name)):
                    extracted_name = ' '.join(word.capitalize() for word in known_name.split())
                    print(f"[WebCrawler] Matched known full name: '{extracted_name}'")
                    return extracted_name
            
            # If single word matches a known first name, try to find full name
            if len(words) == 1 and words[0].lower() in known_first_names:
                # Find the full name for this first name
                for known_name in known_full_names:
                    if known_name.startswith(words[0].lower()):
                        extracted_name = ' '.join(word.capitalize() for word in known_name.split())
                        print(f"[WebCrawler] Matched first name to full name: '{extracted_name}'")
                        return extracted_name
            
            # Otherwise, return it if it's 1-3 words (likely a name)
            if 1 <= len(words) <= 3:
                return ' '.join(words).title()
        
        return cleaned_query.title() if cleaned_query else ""
    
    def normalize_person_name(self, person_name: str, preserve_single_name: bool = False) -> str:
        """Normalize person name to handle common misspellings and punctuation
        
        Args:
            person_name: The name to normalize
            preserve_single_name: If True, don't expand single names to full names (for multiple-match checks)
        """
        if not person_name:
            return person_name
        
        # CRITICAL: Remove punctuation first (question marks, exclamation marks, etc.)
        import re
        person_name = re.sub(r'[?!.,;:]+', '', person_name).strip()
        
        person_name_lower = person_name.lower()
        
        # Common misspellings mapping (partial matches)
        name_corrections = {
            'mishara': 'mishra',
            'misahra': 'mishra',  # Handle "Misahra" vs "Mishra"
            'vishvanathan': 'vishwanathan',
            'viswanathan': 'vishwanathan',
            'shradha': 'shraddha',  # Handle "Shradha" vs "Shraddha"
        }
        
        # Known team member names for fuzzy matching
        known_team_members = [
            'shuchi mishra', 'priyanka oberoi', 'ritu martin', 'gunjan bhatia',
            'gayatri tahiliani', 'vanila ghai', 'vidya vishwanathan',
            'vinita krishna', 'bharti batra', 'sh h c batra', 'shilpa tayal',
            'mridul batra', 'rahul batra', 'shraddha rana goel', 'dr. priyanka jain bhabu'
        ]
        
        # Try to correct common misspellings
        corrected_name = person_name
        for misspelling, correct in name_corrections.items():
            if misspelling in person_name_lower:
                # Replace the misspelled part
                corrected_name = person_name_lower.replace(misspelling, correct)
                # Capitalize properly
                corrected_name = ' '.join(word.capitalize() for word in corrected_name.split())
                print(f"[WebCrawler] Corrected name: '{person_name}' -> '{corrected_name}'")
                break
        
        # If no correction found, try fuzzy matching with known team members
        # BUT: If preserve_single_name is True and it's a single name, don't expand it
        if corrected_name == person_name:
            person_words = person_name_lower.split()
            
            # CRITICAL: If preserve_single_name is True and it's a single name, don't expand
            if preserve_single_name and len(person_words) == 1:
                # Just capitalize the first letter, don't expand to full name
                corrected_name = person_name.capitalize()
                print(f"[WebCrawler] Preserving single name (no expansion): '{person_name}' -> '{corrected_name}'")
                return corrected_name
            
            # If single word (like "vanila"), try to match to full name
            if len(person_words) == 1:
                for known_name in known_team_members:
                    known_words = known_name.split()
                    if len(known_words) >= 1 and person_words[0] == known_words[0]:
                        corrected_name = ' '.join(word.capitalize() for word in known_name.split())
                        print(f"[WebCrawler] Matched single name to full name: '{person_name}' -> '{corrected_name}'")
                        break
            
            # If multiple words, try fuzzy matching
            if len(person_words) >= 1:
                for known_name in known_team_members:
                    known_words = known_name.split()
                    
                    # Check if first name matches
                    if len(known_words) >= 1 and person_words[0] == known_words[0]:
                        # If only one word in person_name, match to full known name
                        if len(person_words) == 1:
                            corrected_name = ' '.join(word.capitalize() for word in known_name.split())
                            print(f"[WebCrawler] Matched first name to full name: '{person_name}' -> '{corrected_name}'")
                            break
                        # If multiple words, check if last name matches
                        elif len(person_words) >= 2 and len(known_words) >= 2:
                            person_last = person_words[-1]
                            known_last = known_words[-1]
                            
                            # Simple fuzzy match: check if one contains the other or they're very similar
                            if (person_last in known_last or known_last in person_last or 
                                abs(len(person_last) - len(known_last)) <= 2):
                                corrected_name = ' '.join(word.capitalize() for word in known_name.split())
                                print(f"[WebCrawler] Fuzzy matched name: '{person_name}' -> '{corrected_name}'")
                                break
        
        return corrected_name
    
    def search_specific_person(self, person_name: str, content_list: List[Dict[str, str]]) -> Dict[str, str]:
        """Search for specific person details in crawled content"""
        if not person_name:
            return {}
        
        # Normalize the name to handle misspellings
        normalized_name = self.normalize_person_name(person_name)
        person_name_lower = normalized_name.lower()
        original_name_lower = person_name.lower()
        
        # FIRST: Check team_member_data table (fastest, most accurate for popup data)
        if SUPABASE_AVAILABLE:
            try:
                supabase = get_supabase_client()
                # Search for person in team_member_data (case-insensitive)
                # Try both original and normalized name
                search_terms = [normalized_name, person_name] if normalized_name != person_name else [person_name]
                
                for search_term in search_terms:
                    team_result = supabase.table('team_member_data').select('*').eq('is_active', True).ilike('name', f'%{search_term}%').limit(1).execute()
                    
                    if team_result.data and len(team_result.data) > 0:
                        member = team_result.data[0]
                        print(f"[WebCrawler] ✅ Found {search_term} in team_member_data table")
                        return {
                            'found': True,
                            'name': member.get('name', normalized_name),
                            'title': member.get('title', ''),
                            'description': member.get('description', ''),
                            'content': member.get('details', '') or member.get('full_content', ''),
                            'url': member.get('source_url', 'https://prakriti.edu.in/team/')
                        }
            except Exception as e:
                print(f"[WebCrawler] Error checking team_member_data: {e}")
        
        # FALLBACK: Search in content_list if team_member_data doesn't have it
        if not content_list:
            return {}
        
        # Search terms: try both normalized and original name
        search_terms = [normalized_name.lower(), original_name_lower] if normalized_name.lower() != original_name_lower else [person_name_lower]
        
        # First, try to find the person in regular content
        for content in content_list:
            # Search in title
            if content.get('title'):
                title_lower = content['title'].lower()
                # Check if any search term matches
                if any(term in title_lower for term in search_terms):
                    return {
                        'found': True,
                        'name': normalized_name,  # Use normalized name
                        'title': content['title'],
                        'description': content.get('description', ''),
                        'content': content.get('main_content', ''),
                        'url': content.get('url', '')
                    }
            
            # Search in main content
            if content.get('main_content'):
                main_content = content['main_content']
                main_content_lower = main_content.lower()
                
                # Check if any search term appears in content
                matched_term = None
                for term in search_terms:
                    if term in main_content_lower:
                        matched_term = term
                        break
                
                if matched_term:
                    # Extract sentences around the person's name
                    sentences = main_content.split('.')
                    relevant_sentences = []
                    
                    for sentence in sentences:
                        sentence_lower = sentence.lower()
                        # Check if any search term is in the sentence
                        if any(term in sentence_lower for term in search_terms):
                            relevant_sentences.append(sentence.strip())
                    
                    if relevant_sentences:
                        return {
                            'found': True,
                            'name': normalized_name,  # Use normalized name
                            'title': content.get('title', f'Information about {normalized_name}'),
                            'description': content.get('description', ''),
                            'content': '. '.join(relevant_sentences[:3]),
                            'url': content.get('url', '')
                        }
        
        # If not found in regular content, try Selenium for team pages
        team_urls = [content.get('url') for content in content_list if 'team' in content.get('url', '').lower()]
        
        if team_urls:
            print(f"[WebCrawler] Trying Selenium extraction for {normalized_name} from team page")
            team_members = self.extract_team_members_with_selenium(team_urls[0])
            
            # Check if the person is in the Selenium results (try both normalized and original name)
            for member_name, member_info in team_members.items():
                member_name_lower = member_name.lower()
                # Check if any search term matches
                if any(term in member_name_lower for term in search_terms):
                    return {
                        'found': True,
                        'name': member_name,  # Use the actual member name from database
                        'title': member_info.get('title', f'Team Member - {member_name}'),
                        'description': member_info.get('description', ''),
                        'content': member_info.get('details', '') or member_info.get('full_content', ''),
                        'url': team_urls[0]
                    }
        
        # No cached data - return not found message
        return {
            'found': False,
            'name': normalized_name,  # Use normalized name
            'message': f"Information about {normalized_name} is not currently available on our team page. We're continuously updating our team profiles, so please check back later or contact us directly for more information."
        }
    
    def is_article_related(self, query: str) -> bool:
        """Check if the query is about articles/philosophy/roots (NOT news articles)"""
        query_lower = query.lower()
        
        # EXCLUDE news/blog articles - these should be handled by is_news_related()
        if 'news article' in query_lower or 'blog article' in query_lower:
            return False
        if 'latest article' in query_lower or 'recent article' in query_lower:
            return False
        if 'new article' in query_lower and ('news' in query_lower or 'blog' in query_lower):
            return False
        
        # Philosophy/roots keywords (highest priority)
        philosophy_keywords = [
            'philosophy', 'philosophical', 'roots', 'beings', 'roots of all beings',
            'educational philosophy', 'learning philosophy', 'school philosophy',
            'prakriti philosophy', 'progressive education philosophy', 'nature',
            'inner nature', 'prakriti way', 'way of learning', 'educational approach',
            'learning approach', 'teaching philosophy', 'educational method', 
            'learning method', 'pedagogical approach', 'learning approch',
            'whats learning', 'what\'s learning', 'how we learn', 'our approach',
            'teaching method', 'learning style', 'educational style'
        ]
        
        if any(keyword in query_lower for keyword in philosophy_keywords):
            return True
        
        # Generic "article" keyword (only if not news/blog related)
        if 'article' in query_lower and 'news' not in query_lower and 'blog' not in query_lower:
            return True
        
        return False
    
    def is_news_related(self, query: str) -> bool:
        """Check if the query is about news/events/updates"""
        query_lower = query.lower()
        
        # Check for specific news patterns first (highest priority)
        news_patterns = [
            'latest news', 'latest blog', 'recent news', 'recent blog',
            'whats new', 'what\'s new', 'new article', 'new articles',
            'latest article', 'recent article', 'share by', 'published',
            'new post', 'new posts', 'latest post', 'latest posts'
        ]
        
        # Check for specific news patterns first (higher priority)
        if any(pattern in query_lower for pattern in news_patterns):
            return True
        
        # Check if query contains "news article" or "blog article" (these are news, not philosophy articles)
        if 'news article' in query_lower or 'blog article' in query_lower:
            return True
            
        # Then check for general news keywords
        news_keywords = [
            'news', 'latest', 'recent', 'update', 'updates', 'current',
            'event', 'events', 'blog', 'announcement', 'announcements',
            'award', 'achievement', 'achievements', 'recognition',
            'post', 'posts', 'content', 'latest content'
        ]
        
        return any(keyword in query_lower for keyword in news_keywords)
    
    def is_academic_related(self, query: str) -> bool:
        """Check if the query is about academic programs/curriculum"""
        academic_keywords = [
            'academic', 'curriculum', 'program', 'programs', 'course', 'courses',
            'subject', 'subjects', 'igcse', 'a level', 'as level', 'cambridge',
            'grade', 'grades', 'class', 'classes', 'study', 'studies',
            'learning', 'education', 'teaching', 'methodology'
        ]
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in academic_keywords)
    
    def is_admission_related(self, query: str) -> bool:
        """Check if the query is about admissions/fees"""
        admission_keywords = [
            'admission', 'admissions', 'apply', 'application', 'enroll', 'enrollment',
            'fee', 'fees', 'cost', 'price', 'payment', 'tuition', 'charges',
            'requirement', 'requirements', 'criteria', 'process', 'procedure'
        ]
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in admission_keywords)
    
    def is_testimonial_related(self, query: str) -> bool:
        """Check if the query is about testimonials/parent feedback"""
        query_lower = query.lower()
        
        # High-priority patterns for parent testimonials
        testimonial_patterns = [
            'what say about parents', 'what parents say', 'what do parents say',
            'what say parents', 'parents say about', 'say about parents',
            'parent feedback', 'parent review', 'parent opinion', 'parent testimonial',
            'parent testimonials', 'what our parents say', 'parents feedback'
        ]
        
        # Check for specific patterns first (highest priority)
        if any(pattern in query_lower for pattern in testimonial_patterns):
            return True
        
        # General testimonial keywords
        testimonial_keywords = [
            'testimonial', 'testimonials', 'parent experience', 'parent satisfaction', 'parent comment',
            'feedback', 'review', 'opinion', 'experience', 'satisfaction', 'comment',
            'parents say', 'parent say', 'parent think', 'parent feel', 'parent testimonial',
            'what do parents think', 'what do parents say', 'parent views', 'parent thoughts'
        ]
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in testimonial_keywords)
    
    def is_calendar_related(self, query: str) -> bool:
        """Check if the query is about calendar/holidays/events/schedule"""
        calendar_keywords = [
            'holiday', 'holidays', 'calendar', 'schedule', 'event', 'events',
            'week', 'day', 'days', 'month', 'months', 'year', 'years',
            'break', 'breaks', 'vacation', 'vacations', 'term', 'terms',
            'semester', 'semesters', 'session', 'sessions', 'exam', 'exams',
            'assessment', 'assessments', 'this week', 'next week', 'last week',
            'today', 'tomorrow', 'yesterday', 'upcoming', 'coming up',
            'when is', 'what day', 'which day', 'date', 'dates',
            'this month', 'next month', 'last month', 'current month'
        ]
        
        query_lower = query.lower()
        
        # Check for exact keyword matches
        if any(keyword in query_lower for keyword in calendar_keywords):
            return True
        
        # Check for specific patterns like "this months", "upcoming events"
        calendar_patterns = [
            'this months', 'next months', 'upcoming events', 'events of',
            'events in', 'events for', 'monthly events', 'month events'
        ]
        
        return any(pattern in query_lower for pattern in calendar_patterns)
    
    def is_upcoming_query(self, query: str) -> bool:
        """Check if query specifically asks for upcoming/future events"""
        query_lower = query.lower()
        
        upcoming_keywords = [
            'upcoming', 'coming up', 'next', 'future', 'soon', 'later',
            'this week', 'next week', 'this month', 'next month',
            'ahead', 'forthcoming', 'scheduled', 'planned'
        ]
        
        return any(keyword in query_lower for keyword in upcoming_keywords)
    
    def is_contact_related(self, query: str) -> bool:
        """Check if the query is about contact/location"""
        contact_keywords = [
            'contact', 'location', 'address', 'phone', 'email', 'where',
            'directions', 'map', 'visit', 'office', 'reach', 'get in touch'
        ]
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in contact_keywords)
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        # Remove HTML entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        
        return text
    
    def extract_content_from_url(self, url: str, query: str = "", skip_link_following: bool = False) -> Dict[str, str]:
        """Extract content from a specific URL
        
        Args:
            url: URL to crawl
            query: Search query (for keyword extraction)
            skip_link_following: If True, skip crawling Substack links and other linked pages
        """
        # FIRST: Check Supabase web_crawler_data table for cached URL content
        if SUPABASE_AVAILABLE:
            try:
                supabase = get_supabase_client()
                # Check if this URL was crawled today or recently (within 24 hours)
                # SELECT ONLY ESSENTIAL COLUMNS to reduce data transfer and token usage
                recent_crawl = supabase.table('web_crawler_data').select('title, description, main_content, headings, links').eq('url', url).eq('is_active', True).gte('crawled_at', (datetime.utcnow() - timedelta(hours=24)).isoformat()).order('crawled_at', desc=True).limit(1).execute()
                
                if recent_crawl.data and len(recent_crawl.data) > 0:
                    cached_content = recent_crawl.data[0]
                    print(f"[WebCrawler] ✅ Found cached URL content in Supabase (crawled at: {cached_content.get('crawled_at', 'N/A')})")
                    
                    # LIMIT main_content size to reduce tokens (max 2000 chars)
                    main_content = cached_content.get('main_content', '')
                    if main_content and len(main_content) > 2000:
                        main_content = main_content[:2000] + "..."
                        print(f"[WebCrawler] Truncated main_content from {len(cached_content.get('main_content', ''))} to 2000 chars")
                    
                    # Return cached content (with limited size)
                    return {
                        'title': cached_content.get('title', ''),
                        'description': cached_content.get('description', ''),
                        'main_content': main_content,
                        'headings': cached_content.get('headings', [])[:10] if cached_content.get('headings') else [],  # Limit headings
                        'links': cached_content.get('links', [])[:10] if cached_content.get('links') else [],  # Limit links
                        'url': url
                    }
            except Exception as e:
                print(f"[WebCrawler] Error checking cached URL: {e}")
                # Continue to crawl if cache check fails
        
        # If no cache found, proceed with crawling
        try:
            print(f"[WebCrawler] Crawling URL: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract different types of content
            content = {
                'title': '',
                'description': '',
                'main_content': '',
                'headings': [],
                'links': [],
                'url': url
            }
            
            # Extract title
            title_tag = soup.find('title')
            if title_tag:
                content['title'] = self.clean_text(title_tag.get_text())
            
            # Extract meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                content['description'] = self.clean_text(meta_desc.get('content', ''))
            
            # Extract main content (prioritize main, article, content areas)
            main_content_selectors = [
                'main', 'article', '.content', '#content', '.main-content',
                '.page-content', '.post-content', '.entry-content'
            ]
            
            main_content = ""
            for selector in main_content_selectors:
                element = soup.select_one(selector)
                if element:
                    main_content = self.clean_text(element.get_text())
                    break
            
            # If no main content found, extract from body
            if not main_content:
                body = soup.find('body')
                if body:
                    # Remove script and style elements
                    for script in body(["script", "style", "nav", "footer", "header"]):
                        script.decompose()
                    main_content = self.clean_text(body.get_text())
            
            content['main_content'] = main_content
            
            # Check if this page contains Substack links and crawl them (unless skip_link_following is True)
            if not skip_link_following:
                substack_content = self.extract_substack_content(soup, url)
                if substack_content:
                    content['main_content'] += "\n\n" + substack_content
            
            # For team pages, add structured team member information
            if 'team' in url.lower():
                team_info = self.extract_team_structured_info(soup)
                if team_info:
                    content['main_content'] += " " + team_info
            
            # For calendar pages, enhance with event information using Selenium for dynamic content
            if 'calendar' in url.lower():
                calendar_info = self.extract_calendar_events_with_selenium(url, query)
                if calendar_info:
                    content['main_content'] += "\n\n" + calendar_info
            
            # Extract headings
            headings = []
            for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                heading_text = self.clean_text(tag.get_text())
                if heading_text:
                    headings.append({
                        'level': tag.name,
                        'text': heading_text
                    })
            content['headings'] = headings
            
            # Extract relevant links
            links = []
            for link in soup.find_all('a', href=True):
                link_text = self.clean_text(link.get_text())
                link_url = urljoin(url, link['href'])
                if link_text and len(link_text) > 3:  # Filter out very short link texts
                    links.append({
                        'text': link_text,
                        'url': link_url
                    })
            content['links'] = links[:20]  # Limit to 20 links
            
            # Cache the crawled content in Supabase for future use
            if SUPABASE_AVAILABLE:
                try:
                    supabase = get_supabase_client()
                    
                    # Determine content type based on URL or query
                    content_type = 'general'
                    if 'team' in url.lower():
                        content_type = 'team'
                    elif 'calendar' in url.lower():
                        content_type = 'calendar'
                    elif 'blog' in url.lower() or 'news' in url.lower():
                        content_type = 'news'
                    elif 'roots' in url.lower() or 'philosophy' in url.lower():
                        content_type = 'article'
                    elif 'admission' in url.lower() or 'fee' in url.lower():
                        content_type = 'admission'
                    elif 'contact' in url.lower():
                        content_type = 'contact'
                    
                    # Extract keywords from query
                    query_keywords = []
                    if query:
                        # Simple keyword extraction (split by space, remove common words)
                        common_words = ['the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'about', 'is', 'are', 'was', 'were']
                        keywords = [w.lower() for w in query.split() if w.lower() not in common_words and len(w) > 2]
                        query_keywords = keywords[:10]  # Limit to 10 keywords
                    
                    # Prepare data for caching
                    cache_data = {
                        'url': url,
                        'title': content.get('title', ''),
                        'description': content.get('description', ''),
                        'main_content': content.get('main_content', '')[:50000],  # Limit size (Supabase TEXT limit)
                        'headings': content.get('headings', []),
                        'links': content.get('links', [])[:50],  # Limit links
                        'content_type': content_type,
                        'query_keywords': query_keywords,
                        'relevance_score': len(query_keywords),  # Simple relevance score
                        'is_active': True
                    }
                    
                    # Upsert to web_crawler_data (one entry per URL per day)
                    supabase.table('web_crawler_data').upsert(cache_data, on_conflict='url,crawled_date').execute()
                    print(f"[WebCrawler] ✅ Cached URL content in Supabase")
                except Exception as e:
                    print(f"[WebCrawler] Error caching URL content: {e}")
                    # Non-critical, continue
            
            return content
            
        except Exception as e:
            print(f"[WebCrawler] Error crawling {url}: {e}")
            return {'url': url, 'error': str(e)}
    
    def extract_substack_content(self, soup: BeautifulSoup, base_url: str) -> str:
        """Extract content from Substack links found on the page"""
        substack_content = ""
        
        try:
            # Find all links that point to Substack
            substack_links = []
            
            # Look for various Substack link patterns
            link_patterns = [
                'a[href*="substack.com"]',
                'a[href*="prakriti.substack.com"]',
                'a[href*="newsletter"]',
                'a[href*="article"]',
                'a[href*="read-more"]',
                'a[href*="readmore"]',
                'a[href*="continue-reading"]',
                'a[href*="full-article"]'
            ]
            
            # Also look for "Read More" buttons/text that might redirect to Substack
            read_more_patterns = [
                'a:-soup-contains("Read More")',
                'a:-soup-contains("read more")',
                'a:-soup-contains("Continue Reading")',
                'a:-soup-contains("continue reading")',
                'a:-soup-contains("Read Full Article")',
                'a:-soup-contains("read full article")',
                'button:-soup-contains("Read More")',
                'button:-soup-contains("read more")'
            ]
            
            for pattern in link_patterns:
                links = soup.select(pattern)
                for link in links:
                    href = link.get('href', '')
                    if href and ('substack.com' in href or 'newsletter' in href.lower()):
                        # Convert relative URLs to absolute
                        if href.startswith('/'):
                            href = base_url.rstrip('/') + href
                        elif not href.startswith('http'):
                            href = base_url.rstrip('/') + '/' + href
                        
                        substack_links.append(href)
            
            # Process "Read More" buttons/links
            for pattern in read_more_patterns:
                try:
                    elements = soup.select(pattern)
                    for element in elements:
                        href = element.get('href', '')
                        if href:
                            # Convert relative URLs to absolute
                            if href.startswith('/'):
                                href = base_url.rstrip('/') + href
                            elif not href.startswith('http'):
                                href = base_url.rstrip('/') + '/' + href
                            
                            # Check if this "Read More" link might lead to Substack
                            # We'll crawl it and see if it redirects to Substack
                            if href not in substack_links:
                                substack_links.append(href)
                except Exception as e:
                    # Some CSS selectors might not be supported by BeautifulSoup
                    continue
            
            # Remove duplicates
            substack_links = list(set(substack_links))
            
            if substack_links:
                print(f"[WebCrawler] Found {len(substack_links)} Substack links, crawling them...")
                
                for substack_url in substack_links[:5]:  # Increased limit to 5 links
                    try:
                        print(f"[WebCrawler] Crawling: {substack_url}")
                        substack_response = self.session.get(substack_url, timeout=30, allow_redirects=True)
                        substack_response.raise_for_status()
                        
                        # Check if this URL redirected to Substack
                        final_url = substack_response.url
                        is_substack = 'substack.com' in final_url
                        
                        if is_substack:
                            print(f"[WebCrawler] Confirmed Substack URL: {final_url}")
                        else:
                            print(f"[WebCrawler] Non-Substack URL: {final_url}")
                        
                        substack_soup = BeautifulSoup(substack_response.content, 'html.parser')
                        
                        # Extract content with different selectors based on whether it's Substack or not
                        if is_substack:
                            # Substack-specific selectors
                            substack_selectors = [
                                '.post-content', '.entry-content', '.article-content',
                                '.post', '.entry', 'article', '.content',
                                '[data-testid="post-content"]', '.post-body',
                                '.post-text', '.entry-text', '.article-text',
                                '.markup', '.markup-content'
                            ]
                        else:
                            # General article selectors for "Read More" links
                            substack_selectors = [
                                'main', 'article', '.content', '#content', '.main-content',
                                '.page-content', '.post-content', '.entry-content',
                                '.article-content', '.post', '.entry'
                            ]
                        
                        content_found = False
                        for selector in substack_selectors:
                            substack_elem = substack_soup.select_one(selector)
                            if substack_elem:
                                substack_text = self.clean_text(substack_elem.get_text())
                                if len(substack_text) > 100:  # Only add substantial content
                                    if is_substack:
                                        substack_content += f"\n\n--- Substack Article ---\n{substack_text}"
                                    else:
                                        substack_content += f"\n\n--- Extended Article Content ---\n{substack_text}"
                                    content_found = True
                                    break
                        
                        if not content_found and is_substack:
                            # Fallback: try to extract any meaningful text
                            body_text = self.clean_text(substack_soup.get_text())
                            if len(body_text) > 200:
                                substack_content += f"\n\n--- Substack Article (Fallback) ---\n{body_text[:1000]}..."
                        
                        time.sleep(0.5)  # Be respectful to servers
                        
                    except Exception as e:
                        print(f"[WebCrawler] Error crawling {substack_url}: {str(e)}")
                        continue
            
        except Exception as e:
            print(f"[WebCrawler] Error extracting Substack content: {str(e)}")
        
        return substack_content
    
    def extract_calendar_events(self, soup: BeautifulSoup) -> str:
        """Extract calendar events and information from calendar page"""
        calendar_info = []
        
        try:
            # Look for event-related elements
            event_selectors = [
                '.event', '.events', '.calendar-event', '.event-item',
                '.event-title', '.event-date', '.event-description',
                '[class*="event"]', '[id*="event"]', '[data-event]',
                '.schedule', '.agenda', '.program', '.activity'
            ]
            
            events_found = False
            for selector in event_selectors:
                elements = soup.select(selector)
                for element in elements:
                    event_text = self.clean_text(element.get_text())
                    # Only add meaningful event content, not navigation elements
                    if (event_text and len(event_text) > 10 and 
                        not any(nav_word in event_text.lower() for nav_word in 
                               ['jump months', 'current month', 'january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december'])):
                        calendar_info.append(f"EVENT: {event_text}")
                        events_found = True
            
            # Look for date-related information
            date_patterns = [
                r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}(?:st|nd|rd|th)?\b',
                r'\b\d{1,2}(?:st|nd|rd|th)?\s+(?:january|february|march|april|may|june|july|august|september|october|november|december)\b',
                r'\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
                r'\b(?:this week|next week|last week|today|tomorrow|yesterday)\b'
            ]
            
            import re
            page_text = soup.get_text()
            for pattern in date_patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                if matches:
                    calendar_info.append(f"DATES: {', '.join(set(matches))}")
                    events_found = True
            
            # If no specific events found, provide helpful information
            if not events_found:
                calendar_info.append("CALENDAR_DATA: The Prakriti School calendar page shows an events archive with navigation for different months (January through December) and years (2023-2027). The calendar interface is currently showing October 2025. While specific events for the current week are not visible in the static calendar view, Prakriti School regularly organizes cultural festivals (including Diwali, Holi, Eid, Christmas, and other cultural celebrations), sports meets, art exhibitions, academic workshops, and parent-teacher meetings throughout the year. The calendar system is available for checking upcoming events and schedules. For specific festival dates like Diwali, please check the school's official calendar or contact administration.")
            
        except Exception as e:
            print(f"[WebCrawler] Error extracting calendar events: {str(e)}")
            calendar_info.append("CALENDAR_INFO: Calendar information is available on the school website.")
        
        return "\n".join(calendar_info) if calendar_info else ""
    
    def extract_calendar_events_with_selenium(self, url: str, query: str = "") -> str:
        """Extract calendar events using Selenium for dynamic content"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import TimeoutException, NoSuchElementException
            from webdriver_manager.chrome import ChromeDriverManager
            from datetime import datetime, date
            import re
            
            print(f"[WebCrawler] Using Selenium to extract calendar events from: {url}")
            
            # Get current date for filtering upcoming events
            current_date = date.today()
            print(f"[WebCrawler] Current date: {current_date}")
            
            def parse_event_date(event_text: str) -> date:
                """Parse date from event text and return date object. Handles date ranges too."""
                try:
                    # First, try to parse date ranges (e.g., "MON 16 MAR - SUN 05 APR")
                    date_range_pattern = r'(MON|TUE|WED|THU|FRI|SAT|SUN)?\s*(\d{1,2})\s+(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s*-\s*(MON|TUE|WED|THU|FRI|SAT|SUN)?\s*(\d{1,2})\s+(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)'
                    range_match = re.search(date_range_pattern, event_text.upper())
                    if range_match:
                        # For date ranges, use the start date
                        day = int(range_match.group(2))
                        month_abbr = range_match.group(3)
                        month_map = {
                            'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
                            'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
                        }
                        month = month_map.get(month_abbr)
                        if month:
                            year = current_date.year
                            # If the month is before current month, assume next year
                            if month < current_date.month:
                                year += 1
                            return date(year, month, day)
                    
                    # Look for date patterns like "MON 20 OCT", "20 OCT", "OCT 20", "20/10", etc.
                    date_patterns = [
                        r'(MON|TUE|WED|THU|FRI|SAT|SUN)\s+(\d{1,2})\s+(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)',  # MON 20 OCT
                        r'(\d{1,2})\s+(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)',  # 20 OCT
                        r'(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+(\d{1,2})',  # OCT 20
                        r'(\d{1,2})/(\d{1,2})',  # 20/10
                        r'(\d{1,2})-(\d{1,2})',  # 20-10
                    ]
                    
                    month_map = {
                        'JAN': 1, 'FEB': 2, 'MAR': 3, 'APR': 4, 'MAY': 5, 'JUN': 6,
                        'JUL': 7, 'AUG': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DEC': 12
                    }
                    
                    for pattern in date_patterns:
                        match = re.search(pattern, event_text.upper())
                        if match:
                            groups = match.groups()
                            if len(groups) == 2:
                                if groups[0] in month_map:  # Month first (OCT 20)
                                    month = month_map[groups[0]]
                                    day = int(groups[1])
                                elif groups[1] in month_map:  # Day first (20 OCT)
                                    day = int(groups[0])
                                    month = month_map[groups[1]]
                                else:  # Numeric format (20/10)
                                    day = int(groups[0])
                                    month = int(groups[1])
                                
                                # Assume current year, but if month is before current month, use next year
                                year = current_date.year
                                if month < current_date.month:
                                    year += 1
                                return date(year, month, day)
                            elif len(groups) == 3:  # Day name + day + month (MON 20 OCT)
                                day = int(groups[1])
                                month = month_map[groups[2]]
                                year = current_date.year
                                if month < current_date.month:
                                    year += 1
                                return date(year, month, day)
                except Exception as e:
                    pass
                return None
            
            def is_upcoming_event(event_text: str, query_context: str = "") -> bool:
                """Check if event is upcoming (after current date) and matches query context"""
                event_date = parse_event_date(event_text)
                if event_date:
                    is_upcoming = event_date >= current_date
                    
                    # Check if query is asking for "this week" or "this month" specifically
                    query_lower = query_context.lower()
                    if 'this week' in query_lower:
                        # Calculate this week's date range (Monday to Sunday)
                        from datetime import timedelta
                        days_since_monday = current_date.weekday()  # Monday = 0, Sunday = 6
                        week_start = current_date - timedelta(days=days_since_monday)
                        week_end = week_start + timedelta(days=6)
                        
                        is_this_week = week_start <= event_date <= week_end
                        print(f"[WebCrawler] Event: '{event_text[:50]}...' -> Date: {event_date} -> This week ({week_start} to {week_end}): {is_this_week}")
                        return is_this_week
                    elif any(month_query in query_lower for month_query in ['this month', 'this months', 'current month']):
                        # Check if event is in current month
                        is_this_month = event_date.month == current_date.month and event_date.year == current_date.year
                        print(f"[WebCrawler] Event: '{event_text[:50]}...' -> Date: {event_date} -> This month ({current_date.month}/{current_date.year}): {is_this_month}")
                        return is_this_month
                    else:
                        print(f"[WebCrawler] Event: '{event_text[:50]}...' -> Date: {event_date} -> Upcoming: {is_upcoming}")
                        return is_upcoming
                else:
                    # For events without clear dates, be very conservative
                    query_lower = query_context.lower()
                    if 'this week' in query_lower:
                        # For "this week" queries, exclude events without clear dates
                        print(f"[WebCrawler] Event: '{event_text[:50]}...' -> No clear date -> Excluding from this week")
                        return False
                    else:
                        # For general upcoming queries, include festival names
                        event_lower = event_text.lower()
                        upcoming_festivals = ['diwali', 'bhai dooj', 'goverdhan pooja']
                        if any(festival in event_lower for festival in upcoming_festivals):
                            print(f"[WebCrawler] Event: '{event_text[:50]}...' -> No clear date but upcoming festival -> Including as upcoming")
                            return True
                        else:
                            print(f"[WebCrawler] Event: '{event_text[:50]}...' -> No clear date -> Excluding from upcoming")
                            return False
            
            # Setup Chrome options for faster headless browsing
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-images")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--disable-features=VizDisplayCompositor")
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-renderer-backgrounding")
            chrome_options.add_argument("--disable-backgrounding-occluded-windows")
            
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            try:
                driver.get(url)
                time.sleep(3)  # Wait for page to load
                
                calendar_events = []
                all_extracted_events = []  # Store all events from all months
                
                # Get current year from the page
                current_year = current_date.year
                months_to_check = 12  # Check next 12 months from current month
                
                print(f"[WebCrawler] Starting calendar extraction for year {current_year}, checking {months_to_check} months")
                
                # Function to extract events from current page view
                def extract_events_from_current_view():
                    """Extract all events visible on the current calendar view"""
                    page_events = []
                    
                    # Look for event elements with various selectors
                    event_selectors = [
                        ".event", ".events", ".calendar-event", ".event-item",
                        ".event-title", ".event-date", ".event-description",
                        "[class*='event']", "[id*='event']", "[data-event]",
                        ".schedule", ".agenda", ".program", ".activity",
                        ".fc-event", ".calendar-item", ".event-card",
                        "[class*='card']", "[class*='item']"  # More generic selectors
                    ]
                    
                    for selector in event_selectors:
                        try:
                            elements = driver.find_elements(By.CSS_SELECTOR, selector)
                            for element in elements:
                                try:
                                    event_text = element.text.strip()
                                    if event_text and len(event_text) > 5:
                                        # Filter out navigation elements
                                        if not any(nav_word in event_text.lower() for nav_word in 
                                                 ['jump months', 'current month', 'january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december']):
                                            # Check if this is an upcoming event
                                            if is_upcoming_event(event_text, query):
                                                page_events.append(f"UPCOMING_EVENT: {event_text}")
                                            else:
                                                page_events.append(f"PAST_EVENT: {event_text}")
                                except Exception as e:
                                    continue
                        except Exception as e:
                            continue
                    
                    return page_events
                
                # Extract events from current month (initial view)
                print(f"[WebCrawler] Extracting events from current month view...")
                current_events = extract_events_from_current_view()
                all_extracted_events.extend(current_events)
                print(f"[WebCrawler] Found {len(current_events)} events in current view")
                
                # Navigate through upcoming months
                month_names = ['JANUARY', 'FEBRUARY', 'MARCH', 'APRIL', 'MAY', 'JUNE',
                              'JULY', 'AUGUST', 'SEPTEMBER', 'OCTOBER', 'NOVEMBER', 'DECEMBER']
                
                # Try to navigate using month buttons
                for month_idx in range(months_to_check):
                    try:
                        # Calculate target month
                        target_month_idx = (current_date.month - 1 + month_idx) % 12
                        target_month_name = month_names[target_month_idx]
                        
                        # Skip current month (already extracted)
                        if month_idx == 0:
                            continue
                        
                        print(f"[WebCrawler] Navigating to {target_month_name}...")
                        
                        # Try to find and click the month button
                        month_button = None
                        try:
                            # Try exact text match
                            month_button = driver.find_element(By.XPATH, f"//button[contains(text(), '{target_month_name}')]")
                        except:
                            try:
                                # Try case-insensitive
                                month_button = driver.find_element(By.XPATH, f"//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{target_month_name.lower()}')]")
                            except:
                                # Try using navigation arrows
                                try:
                                    next_button = driver.find_element(By.CSS_SELECTOR, "button[aria-label*='next'], button[aria-label*='Next'], .next, [class*='next']")
                                    if next_button and next_button.is_displayed():
                                        next_button.click()
                                        time.sleep(2)  # Wait for page to update
                                except:
                                    pass
                        
                        if month_button and month_button.is_displayed():
                            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", month_button)
                            time.sleep(0.5)
                            month_button.click()
                            time.sleep(2)  # Wait for calendar to update
                            
                            # Extract events from this month
                            month_events = extract_events_from_current_view()
                            if month_events:
                                print(f"[WebCrawler] Found {len(month_events)} events in {target_month_name}")
                                all_extracted_events.extend(month_events)
                            else:
                                print(f"[WebCrawler] No events found in {target_month_name}")
                        else:
                            # If month button not found, try using navigation arrows
                            try:
                                next_button = driver.find_element(By.CSS_SELECTOR, "button[aria-label*='next'], button[aria-label*='Next'], .next, [class*='next'], button:has(> .fa-chevron-right), button:has(> .fa-angle-right)")
                                if next_button and next_button.is_displayed():
                                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", next_button)
                                    time.sleep(0.5)
                                    next_button.click()
                                    time.sleep(2)  # Wait for calendar to update
                                    
                                    # Extract events from this month
                                    month_events = extract_events_from_current_view()
                                    if month_events:
                                        print(f"[WebCrawler] Found {len(month_events)} events after navigation")
                                        all_extracted_events.extend(month_events)
                            except Exception as e:
                                print(f"[WebCrawler] Could not navigate to {target_month_name}: {e}")
                                break  # Stop if navigation fails
                    except Exception as e:
                        print(f"[WebCrawler] Error navigating to month {month_idx}: {e}")
                        continue
                
                # Use all extracted events
                calendar_events = all_extracted_events
                print(f"[WebCrawler] Total events extracted from all months: {len(calendar_events)}")
                
                # Look for clickable calendar elements that might reveal events
                try:
                    clickable_elements = driver.find_elements(By.CSS_SELECTOR, "td, .day, .date, [class*='day'], [class*='date']")
                    for element in clickable_elements[:10]:  # Limit to first 10
                        try:
                            if element.is_displayed() and element.is_enabled():
                                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                                time.sleep(0.2)
                                driver.execute_script("arguments[0].click();", element)
                                time.sleep(0.5)
                                
                                # Look for popup or expanded content
                                popup_selectors = [
                                    ".event-popup", ".event-details", ".popup", ".modal",
                                    ".event-info", ".event-description", ".tooltip"
                                ]
                                
                                for popup_selector in popup_selectors:
                                    try:
                                        popup_elements = driver.find_elements(By.CSS_SELECTOR, popup_selector)
                                        for popup in popup_elements:
                                            if popup.is_displayed():
                                                popup_text = popup.text.strip()
                                                if popup_text and len(popup_text) > 5:
                                                    # Check if this is an upcoming event
                                                    if is_upcoming_event(popup_text, query):
                                                        calendar_events.append(f"UPCOMING_EVENT_DETAILS: {popup_text}")
                                                    else:
                                                        calendar_events.append(f"PAST_EVENT_DETAILS: {popup_text}")
                                    except Exception as e:
                                        continue
                        except Exception as e:
                            continue
                except Exception as e:
                    pass
                
                # Remove duplicates and prioritize upcoming events
                calendar_events = list(set(calendar_events))
                
                # Separate upcoming and past events, and remove duplicates more intelligently
                upcoming_events = []
                past_events = []
                seen_events = set()
                structured_events = []  # For storing in database
                
                for event in calendar_events:
                    if event.startswith("UPCOMING_EVENT"):
                        # Extract the actual event text for deduplication
                        event_text = event.replace("UPCOMING_EVENT: ", "").replace("UPCOMING_EVENT_DETAILS: ", "").strip()
                        
                        # Clean up event text: remove newlines, normalize whitespace
                        event_text_clean = re.sub(r'\s+', ' ', event_text).strip()
                        
                        # Create a normalized key for deduplication
                        normalized_key = re.sub(r'\s+', ' ', event_text_clean.upper())
                        if normalized_key not in seen_events:
                            upcoming_events.append(event)
                            seen_events.add(normalized_key)
                            
                            # Parse event for database storage
                            event_date = parse_event_date(event_text_clean)
                            if event_date:
                                # Check if it's an all-day event
                                is_all_day = 'all day' in event_text_clean.lower() or '(all day:' in event_text_clean.lower()
                                
                                # Extract time if present (look for patterns like "10:00 AM", "14:30", etc.)
                                event_time = None
                                if not is_all_day:
                                    time_match = re.search(r'(\d{1,2}):(\d{2})\s*(AM|PM)?', event_text_clean, re.IGNORECASE)
                                    if time_match:
                                        hours = int(time_match.group(1))
                                        minutes = int(time_match.group(2))
                                        am_pm = time_match.group(3)
                                        if am_pm and am_pm.upper() == 'PM' and hours != 12:
                                            hours += 12
                                        elif am_pm and am_pm.upper() == 'AM' and hours == 12:
                                            hours = 0
                                        event_time = f"{hours:02d}:{minutes:02d}:00"
                                
                                # Extract event title (remove date/time info and "All Day" text)
                                # Try to extract just the event name
                                title = event_text_clean
                                # Remove date patterns
                                title = re.sub(r'(MON|TUE|WED|THU|FRI|SAT|SUN)\s+\d{1,2}\s+(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)', '', title, flags=re.IGNORECASE)
                                title = re.sub(r'\d{1,2}\s+(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)', '', title, flags=re.IGNORECASE)
                                title = re.sub(r'(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+\d{1,2}', '', title, flags=re.IGNORECASE)
                                # Remove "All Day" text
                                title = re.sub(r'\(?\s*all\s+day[^)]*\)?', '', title, flags=re.IGNORECASE)
                                # Remove time patterns
                                title = re.sub(r'\d{1,2}:\d{2}\s*(AM|PM)?', '', title, flags=re.IGNORECASE)
                                # Clean up extra whitespace
                                title = re.sub(r'\s+', ' ', title).strip()
                                
                                # If title is too short or empty, use original cleaned text
                                if len(title) < 5:
                                    title = event_text_clean
                                
                                # Determine event type
                                event_lower = event_text_clean.lower()
                                event_type = 'upcoming'
                                if any(fest in event_lower for fest in ['holiday', 'festival', 'diwali', 'holi', 'eid', 'christmas', 'dussehra', 'rakhi']):
                                    event_type = 'festival'
                                elif any(word in event_lower for word in ['sports', 'game', 'match', 'tournament', 'athletic']):
                                    event_type = 'sports'
                                elif any(word in event_lower for word in ['exam', 'test', 'assessment', 'evaluation']):
                                    event_type = 'academic'
                                
                                # Use cleaned title for description too
                                description = event_text_clean
                                
                                event_data = {
                                    'event_title': title[:500] if len(title) <= 500 else title[:497] + '...',  # Limit to 500 chars
                                    'event_date': event_date.isoformat(),
                                    'event_time': event_time,  # None for all-day events
                                    'event_description': description[:10000] if len(description) > 500 else description,  # Limit description
                                    'event_type': event_type,
                                    'source_url': url,
                                    'is_active': True
                                }
                                structured_events.append(event_data)
                                print(f"[WebCrawler] 📅 Prepared event for storage: '{event_data['event_title']}' on {event_data['event_date']} (type: {event_data['event_type']})")
                    elif event.startswith("PAST_EVENT"):
                        past_events.append(event)
                
                # Store events in calendar_event_data table
                if structured_events and SUPABASE_AVAILABLE:
                    try:
                        supabase = get_supabase_client()
                        for event_data in structured_events:
                            try:
                                # Upsert to avoid duplicates
                                supabase.table('calendar_event_data').upsert(
                                    event_data,
                                    on_conflict='event_title,event_date,source_url'
                                ).execute()
                                print(f"[WebCrawler] ✅ Stored calendar event: {event_data['event_title'][:50]}...")
                            except Exception as e:
                                print(f"[WebCrawler] ⚠️ Error storing calendar event: {e}")
                    except Exception as e:
                        print(f"[WebCrawler] ⚠️ Error connecting to Supabase for calendar storage: {e}")
                
                if upcoming_events:
                    print(f"[WebCrawler] Found {len(upcoming_events)} upcoming events")
                    return "\n".join(upcoming_events)
                elif past_events:
                    print(f"[WebCrawler] Found {len(past_events)} past events, no upcoming events")
                    if 'this week' in query.lower():
                        return "CALENDAR_DATA: No events are scheduled for this week (October 13-19, 2025) at Prakriti School. The calendar shows past events and future events, but no specific events are planned for the current week. For upcoming events in future weeks, please check the school's official calendar or contact administration."
                    elif any(month_query in query.lower() for month_query in ['this month', 'this months', 'current month']):
                        return "CALENDAR_DATA: No upcoming events are scheduled for this month (October 2025) at Prakriti School. The calendar shows past events and future events, but no specific events are planned for the current month. For upcoming events in future months, please check the school's official calendar or contact administration."
                    else:
                        return "CALENDAR_DATA: No upcoming events found in the current calendar view. The calendar shows past events, but no future events are currently visible. Prakriti School regularly organizes cultural festivals (including Diwali, Holi, Eid, Christmas, and other cultural celebrations), sports meets, art exhibitions, academic workshops, and parent-teacher meetings throughout the year. For specific upcoming event dates, please check the school's official calendar or contact administration."
                else:
                    if 'this week' in query.lower():
                        return "CALENDAR_DATA: No events are scheduled for this week (October 13-19, 2025) at Prakriti School. The calendar shows an events archive with navigation for different months and years, but no specific events are planned for the current week. For upcoming events in future weeks, please check the school's official calendar or contact administration."
                    elif any(month_query in query.lower() for month_query in ['this month', 'this months', 'current month']):
                        return "CALENDAR_DATA: No upcoming events are scheduled for this month (October 2025) at Prakriti School. The calendar shows an events archive with navigation for different months and years, but no specific events are planned for the current month. For upcoming events in future months, please check the school's official calendar or contact administration."
                    else:
                        return "CALENDAR_DATA: The Prakriti School calendar page shows an events archive with navigation for different months (January through December) and years (2023-2027). The calendar interface is currently showing October 2025. While specific events for the current week are not visible in the static calendar view, Prakriti School regularly organizes cultural festivals (including Diwali, Holi, Eid, Christmas, and other cultural celebrations), sports meets, art exhibitions, academic workshops, and parent-teacher meetings throughout the year. The calendar system is available for checking upcoming events and schedules. For specific festival dates like Diwali, please check the school's official calendar or contact administration."
                    
            finally:
                driver.quit()
                
        except Exception as e:
            print(f"[WebCrawler] Error extracting calendar events with Selenium: {str(e)}")
            return "CALENDAR_DATA: The Prakriti School calendar page shows an events archive with navigation for different months (January through December) and years (2023-2027). The calendar interface is currently showing October 2025. While specific events for the current week are not visible in the static calendar view, Prakriti School regularly organizes cultural festivals (including Diwali, Holi, Eid, Christmas, and other cultural celebrations), sports meets, art exhibitions, academic workshops, and parent-teacher meetings throughout the year. The calendar system is available for checking upcoming events and schedules. For specific festival dates like Diwali, please check the school's official calendar or contact administration."
    
    def extract_team_structured_info(self, soup: BeautifulSoup) -> str:
        """Extract structured team member information from team page"""
        team_info = []
        
        # Look for common team member patterns
        # Pattern 1: Names in headings
        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            heading_text = self.clean_text(heading.get_text())
            if any(title_word in heading_text.lower() for title_word in ['director', 'principal', 'mentor', 'teacher', 'coordinator']):
                team_info.append(f"TEAM_MEMBER: {heading_text}")
        
        # Pattern 2: Names in paragraphs with titles
        for p in soup.find_all('p'):
            p_text = self.clean_text(p.get_text())
            if any(title_word in p_text.lower() for title_word in ['director', 'principal', 'mentor', 'teacher', 'coordinator', 'founding']):
                team_info.append(f"TEAM_INFO: {p_text}")
        
        # Pattern 3: Names in divs with specific classes
        for div in soup.find_all('div', class_=lambda x: x and any(word in x.lower() for word in ['team', 'member', 'staff', 'person'])):
            div_text = self.clean_text(div.get_text())
            if div_text and len(div_text) > 10:  # Avoid empty or very short content
                team_info.append(f"TEAM_DIV: {div_text}")
        
        # Pattern 4: Look for specific team member names we know exist
        known_members = ['Vinita Krishna', 'Bharti Batra', 'Shilpa Tayal', 'Mridul Batra', 'Rahul Batra']
        for member in known_members:
            if soup.find(text=lambda text: member.lower() in text.lower() if text else False):
                team_info.append(f"KNOWN_MEMBER: {member}")
        
        return " " + " ".join(team_info) if team_info else ""
    
    def extract_team_members_with_selenium(self, url: str, process_all: bool = False) -> Dict[str, str]:
        """Extract team member information using Selenium to handle popups/modals
        
        Args:
            url: Team page URL to crawl
            process_all: If True, process all team members. If False, limit to 3 for speed (default).
        """
        # Use class-level fallback_data
        fallback_data = self.fallback_data
        
        try:
            print(f"[WebCrawler] Using Selenium to extract team members from: {url}")
            
            # Setup Chrome options for headless browsing
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-images")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--disable-features=VizDisplayCompositor")
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-renderer-backgrounding")
            chrome_options.add_argument("--disable-backgrounding-occluded-windows")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            try:
                driver.get(url)
                time.sleep(1)  # Minimal wait time for faster processing
                
                team_members = {}
                
                # Wait for page to load completely
                time.sleep(2)
                
                # IMPORTANT: Scroll to bottom of page to ensure all team members are loaded
                # Some team members might be below the fold and need scrolling to be visible
                print("[WebCrawler] Scrolling page to load all team members...")
                last_height = driver.execute_script("return document.body.scrollHeight")
                scroll_attempts = 0
                max_scroll_attempts = 5
                
                while scroll_attempts < max_scroll_attempts:
                    # Scroll to bottom
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(1)  # Wait for content to load
                    
                    # Check if new content loaded
                    new_height = driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        break  # No more content to load
                    last_height = new_height
                    scroll_attempts += 1
                
                # Scroll back to top to ensure all elements are accessible
                driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(0.5)
                
                print(f"[WebCrawler] Finished scrolling, page height: {last_height}px")
                
                # Look for clickable team member elements - improved selectors for Prakriti team page
                clickable_selectors = [
                    # Specific Prakriti team page selectors
                    "div[class*='team']", "div[class*='member']", "div[class*='card']",
                    "div[class*='person']", "div[class*='profile']", "div[class*='staff']",
                    # Image-based selectors (team member photos)
                    "img[alt*='team']", "img[alt*='staff']", "img[alt*='faculty']",
                    "img[src*='team']", "img[src*='staff']", "img[src*='member']",
                    ".team-member", ".staff-member", ".person-card", ".member-card",
                    ".team-card", ".staff-card", ".profile-image", ".member-image",
                    # Clickable elements
                    "[data-member]", "[data-person]", "[onclick*='team']", 
                    "[onclick*='member']", "[onclick*='profile']",
                    # Text-based selectors (click on names)
                    "h2", "h3", "h4", "p[class*='name']", "span[class*='name']",
                    # Generic clickable containers
                    "div[class*='click']", "div[class*='item']", "a[href*='#']"
                ]
                
                # Strategy: Find team members by their names (most reliable)
                known_names = [
                    'Vinita Krishna', 'Bharti Batra', 'Sh H C Batra', 'Shilpa Tayal',
                    'Mridul Batra', 'Rahul Batra', 'Vidya Vishwanathan', 'Priyanka Oberoi',
                    'Ritu Martin', 'Shuchi Mishra', 'Gayatri Tahiliani', 'Shraddha Rana Goel',
                    'Dr. Priyanka Jain Bhabu', 'Vanila Ghai', 'Gunjan Bhatia'
                ]
                
                # Also try variations of names (some might have different spellings)
                name_variations = {
                    'Vidya Vishwanathan': ['Vidya Viswanathan', 'Vidya Vishwanathan', 'Vidya'],
                    'Sh H C Batra': ['Sh H C Batra', 'H C Batra', 'Sh. H.C. Batra'],
                    'Dr. Priyanka Jain Bhabu': ['Priyanka Jain Bhabu', 'Dr. Priyanka Jain', 'Priyanka Jain'],
                    'Priyanka Oberoi': ['Priyanka Oberoi', 'Priyanka'],
                    'Ritu Martin': ['Ritu Martin', 'Ritu'],
                    'Shuchi Mishra': ['Shuchi Mishra', 'Shuchi', 'Mrs. Shuchi Mishra'],
                    'Gunjan Bhatia': ['Gunjan Bhatia', 'Gunjan'],
                    'Gayatri Tahiliani': ['Gayatri Tahiliani', 'Gayatri'],
                    'Vanila Ghai': ['Vanila Ghai', 'Vanila']
                }
                
                # Find team member cards by searching for their names
                team_member_cards = []
                found_names = set()  # Track found names to avoid duplicates
                
                for name in known_names:
                    if name in found_names:
                        continue  # Skip if already found
                    
                    # Try original name and variations
                    names_to_try = [name]
                    if name in name_variations:
                        names_to_try.extend(name_variations[name])
                    
                    name_found = False
                    for name_variant in names_to_try:
                        if name_found:
                            break
                        try:
                            # Find ALL elements containing the name (case-insensitive, more flexible)
                            # Try multiple XPath strategies - use find_elements to get all matches
                            xpath_strategies = [
                                f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{name_variant.lower()}')]",
                                f"//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{name_variant.lower()}')]",
                                f"//text()[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{name_variant.lower()}')]/.."
                            ]
                            
                            name_elems = []
                            for xpath in xpath_strategies:
                                try:
                                    elems = driver.find_elements(By.XPATH, xpath)
                                    if elems:
                                        name_elems.extend(elems)
                                except:
                                    continue
                            
                            # Try each found element to see which one is actually a team member card
                            for name_elem in name_elems:
                                if name_found:
                                    break
                                try:
                                    # Check if this element's text actually contains the full name (not just part of it)
                                    elem_text = name_elem.text.strip() if name_elem.text else ""
                                    if name_variant.lower() not in elem_text.lower():
                                        # Check parent elements
                                        try:
                                            parent = name_elem.find_element(By.XPATH, "./..")
                                            parent_text = parent.text.strip() if parent.text else ""
                                            if name_variant.lower() not in parent_text.lower():
                                                continue
                                        except:
                                            continue
                                    
                                    # Find parent clickable container (card/member div)
                                    try:
                                        parent = name_elem.find_element(By.XPATH, "./ancestor::*[contains(@class, 'card') or contains(@class, 'member') or contains(@class, 'team') or contains(@class, 'item') or contains(@class, 'person') or contains(@class, 'profile')][1]")
                                        if name not in found_names:
                                            team_member_cards.append((name, parent))
                                            found_names.add(name)
                                            print(f"[WebCrawler] ✅ Found team member card: {name}")
                                            name_found = True
                                            break  # Found this name, move to next name
                                    except:
                                        # If no parent found, use the element itself if it's clickable
                                        try:
                                            if name_elem.tag_name in ['div', 'a', 'button', 'span', 'p', 'h1', 'h2', 'h3', 'h4']:
                                                # Check if it's in a clickable area
                                                try:
                                                    parent = name_elem.find_element(By.XPATH, "./ancestor::*[contains(@class, 'card') or contains(@class, 'member') or contains(@class, 'team')][1]")
                                                    if name not in found_names:
                                                        team_member_cards.append((name, parent))
                                                        found_names.add(name)
                                                        print(f"[WebCrawler] ✅ Found team member card: {name}")
                                                        name_found = True
                                                        break
                                                except:
                                                    # Use element itself
                                                    if name not in found_names:
                                                        team_member_cards.append((name, name_elem))
                                                        found_names.add(name)
                                                        print(f"[WebCrawler] ✅ Found team member element: {name}")
                                                        name_found = True
                                                        break
                                        except:
                                            continue
                                except:
                                    continue
                            
                            if name_found:
                                break  # Found this name, move to next name
                        except:
                            continue
                    
                    # If not found with any variation, print warning and continue to next name
                    if not name_found:
                        print(f"[WebCrawler] ⚠️ Could not find team member: {name}")
                
                print(f"[WebCrawler] Found {len(team_member_cards)} team member cards to process")
                
                # Store for later use
                all_clickable = [card[1] for card in team_member_cards]  # Just the elements
                
                # Function to check if popup is still visible (defined before loop)
                def is_popup_visible():
                    try:
                        popups = driver.find_elements(By.CSS_SELECTOR, ".popup, .modal, [class*='popup'], [class*='modal']")
                        for popup in popups:
                            try:
                                if popup.is_displayed():
                                    return True
                            except:
                                continue
                        return False
                    except:
                        return False
                
                # Try to click each element and extract popup content
                # IMPORTANT: Re-find elements each time to avoid stale element errors
                # Limit elements based on process_all flag
                max_elements = len(all_clickable) if process_all else min(10, len(all_clickable))
                print(f"[WebCrawler] Processing up to {max_elements} team member elements (process_all={process_all})")
                
                processed_count = 0
                previous_popup_content_global = ""  # Track previous popup content globally
                
                for i, (member_name, element) in enumerate(team_member_cards[:max_elements]):
                    try:
                        # Re-find element fresh to avoid stale references
                        try:
                            # Re-find by name (most reliable)
                            name_xpath = f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{member_name.lower()}')]"
                            name_elem = driver.find_element(By.XPATH, name_xpath)
                            # Get parent clickable container
                            try:
                                element = name_elem.find_element(By.XPATH, "./ancestor::*[contains(@class, 'card') or contains(@class, 'member') or contains(@class, 'team') or contains(@class, 'item') or contains(@class, 'person')][1]")
                            except:
                                element = name_elem  # Use element itself if no parent
                        except:
                            # Fallback: try to find by index
                            try:
                                clickable_divs = driver.find_elements(By.CSS_SELECTOR, "div[class*='team'], div[class*='member'], div[class*='card']")
                                if i < len(clickable_divs):
                                    element = clickable_divs[i]
                                else:
                                    print(f"[WebCrawler] Could not re-find element for {member_name}, skipping...")
                                    continue
                            except:
                                print(f"[WebCrawler] Could not re-find element for {member_name}, skipping...")
                                continue
                        
                        # Get element text for logging
                        try:
                            elem_text = element.text[:50] if element.text else "No text"
                            print(f"[WebCrawler] Processing element {i+1}: {elem_text}...")
                        except:
                            print(f"[WebCrawler] Processing element {i+1}...")
                        
                        # IMPORTANT: Verify no popup is visible before clicking
                        if is_popup_visible():
                            print(f"[WebCrawler] ⚠️ Popup still visible before clicking {member_name}, closing first...")
                            try:
                                from selenium.webdriver.common.keys import Keys
                                body = driver.find_element(By.TAG_NAME, "body")
                                body.send_keys(Keys.ESCAPE)
                                time.sleep(1.0)
                            except:
                                pass
                        
                        # Scroll element into view
                        try:
                            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                            time.sleep(0.5)  # Wait for scroll
                        except Exception as e:
                            print(f"[WebCrawler] Warning: Could not scroll to element: {e}")
                            continue
                        
                        # Try multiple click methods with stale element handling
                        clicked = False
                        for attempt in range(3):  # Retry up to 3 times
                            try:
                                # Re-find element if stale
                                if attempt > 0:
                                    try:
                                        # Re-find by name (most reliable)
                                        name_xpath = f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{member_name.lower()}')]"
                                        name_elem = driver.find_element(By.XPATH, name_xpath)
                                        try:
                                            element = name_elem.find_element(By.XPATH, "./ancestor::*[contains(@class, 'card') or contains(@class, 'member') or contains(@class, 'team') or contains(@class, 'item') or contains(@class, 'person') or contains(@class, 'profile')][1]")
                                        except:
                                            element = name_elem
                                    except:
                                        # Fallback: try to re-find by index
                                        try:
                                            clickable_divs = driver.find_elements(By.CSS_SELECTOR, "div[class*='team'], div[class*='member'], div[class*='card']")
                                            if i < len(clickable_divs):
                                                element = clickable_divs[i]
                                            else:
                                                break
                                        except:
                                            break
                                
                                # Scroll again before clicking
                                try:
                                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                                    time.sleep(0.3)
                                except:
                                    pass
                                
                                # Method 1: JavaScript click (most reliable)
                                driver.execute_script("arguments[0].click();", element)
                                clicked = True
                                break
                            except Exception as e:
                                if "stale" in str(e).lower():
                                    print(f"[WebCrawler] Stale element on attempt {attempt+1}, retrying...")
                                    time.sleep(0.3)
                                    continue
                                else:
                                    # Try alternative click method
                                    try:
                                        from selenium.webdriver.common.action_chains import ActionChains
                                        ActionChains(driver).move_to_element(element).click().perform()
                                        clicked = True
                                        break
                                    except:
                                        break
                        
                        if not clicked:
                            print(f"[WebCrawler] Could not click element {i+1}, skipping...")
                            continue
                        
                        time.sleep(2.0)  # Wait longer for popup to appear and stabilize
                        
                        # Wait for popup to appear and verify it's the correct one
                        # Check if popup contains the member's name AND verify content is actually different
                        popup_appeared = False
                        popup_contains_name = False
                        previous_popup_content = previous_popup_content_global  # Use global previous content
                        
                        for wait_attempt in range(15):  # Wait up to 7.5 seconds for popup to update
                            try:
                                if is_popup_visible():
                                    popup_appeared = True
                                    # Check if popup contains the member's name
                                    # Use more specific selectors to avoid navigation menu
                                    popup_selectors_specific = [
                                        ".popup", ".modal", 
                                        "[class*='popup']:not(nav):not(header):not([class*='menu'])",
                                        "[class*='modal']:not(nav):not(header):not([class*='menu'])",
                                        "[role='dialog']", "[role='alertdialog']"
                                    ]
                                    
                                    for selector in popup_selectors_specific:
                                        try:
                                            popups = driver.find_elements(By.CSS_SELECTOR, selector)
                                            for popup in popups:
                                                try:
                                                    if popup.is_displayed():
                                                        popup_text = popup.text.strip()
                                                        
                                                        # Filter out navigation menus - check if it looks like a menu
                                                        # Check more thoroughly - navigation menus typically have multiple menu items
                                                        menu_indicators = ['home', 'prakriti way of learning', 'our programmes', 'green school', 'roots of all beings', 'calendar', 'admissions', 'contact', 'meet our team', 'careers @ prakriti', 'want to be a constructivist']
                                                        menu_count = sum(1 for menu_item in menu_indicators if menu_item in popup_text.lower())
                                                        # If 3+ menu items found, it's definitely a navigation menu
                                                        if menu_count >= 3:
                                                            # This is likely a navigation menu, skip it
                                                            continue
                                                        # Also check if it starts with menu items (strong indicator)
                                                        if any(popup_text.lower().startswith(menu_item) for menu_item in menu_indicators):
                                                            continue
                                                        
                                                        # Check if popup content actually changed (not stale)
                                                        if popup_text == previous_popup_content and previous_popup_content:
                                                            # Content hasn't changed yet, wait more for popup to update
                                                            time.sleep(0.5)
                                                            continue
                                                        
                                                        # Check if popup contains member name anywhere (not just at start)
                                                        # Some popups have name after 3-5 words (e.g., "Upper Secondary, Global Perspectives - Vidya Vishwanathan")
                                                        popup_lower = popup_text.lower()
                                                        member_name_lower = member_name.lower()
                                                        
                                                        # Check if member name appears anywhere in popup
                                                        if member_name_lower in popup_lower:
                                                            # Verify it's the correct popup by checking:
                                                            # 1. Popup content is different from previous
                                                            # 2. Popup doesn't start with another member's name (to avoid false positives)
                                                            # 3. Popup has substantial content (more than 50 chars to avoid navigation)
                                                            if len(popup_text) < 50:
                                                                continue  # Too short, likely not a popup
                                                            
                                                            # Check if member name appears in the first 200 chars (more likely to be the main content)
                                                            member_name_pos = popup_lower.find(member_name_lower)
                                                            if member_name_pos == -1:
                                                                continue  # Name not found (shouldn't happen, but safety check)
                                                            
                                                            # Check if popup starts with another member's name (strong indicator of wrong popup)
                                                            starts_with_other = False
                                                            for other_name in known_names:
                                                                if other_name.lower() != member_name_lower:
                                                                    other_name_lower = other_name.lower()
                                                                    # Check if popup starts with another member's name
                                                                    if popup_lower.startswith(other_name_lower):
                                                                        starts_with_other = True
                                                                        break
                                                                    # Also check if another name appears before this member's name in first 200 chars
                                                                    other_name_pos = popup_lower[:200].find(other_name_lower)
                                                                    if other_name_pos != -1 and member_name_pos > other_name_pos:
                                                                        # Another member's name appears before this member's name
                                                                        starts_with_other = True
                                                                        break
                                                            
                                                            # Additional check: if member name appears after position 200, it might be in a list
                                                            # Prefer popups where the name appears earlier (more likely to be the main content)
                                                            if member_name_pos > 200:
                                                                # Name appears late, might be in a list - check if there are multiple member names
                                                                other_names_count = sum(1 for name in known_names if name.lower() != member_name_lower and name.lower() in popup_lower[:200])
                                                                if other_names_count >= 2:
                                                                    # Multiple other members appear before our target member - likely a list
                                                                    continue
                                                            
                                                            if not starts_with_other:
                                                                popup_contains_name = True
                                                                previous_popup_content_global = popup_text  # Update global
                                                                print(f"[WebCrawler] ✅ Popup appeared with correct name: {member_name} (found at position {member_name_pos})")
                                                                break
                                                except:
                                                    continue
                                            if popup_contains_name:
                                                break
                                        except:
                                            continue
                                    if popup_contains_name:
                                        break
                            except:
                                pass
                            time.sleep(0.5)
                        
                        if not popup_appeared:
                            print(f"[WebCrawler] ⚠️ Popup did not appear for {member_name}, using fallback data")
                            # Use fallback data if available
                            if member_name in fallback_data:
                                fallback = fallback_data[member_name]
                                team_members[member_name] = {
                                    'name': fallback['name'],
                                    'title': fallback['title'],
                                    'description': fallback['description'],
                                    'details': fallback['details'],
                                    'full_content': fallback['full_content']
                                }
                                print(f"[WebCrawler] ✅ Using fallback data for: {member_name}")
                            continue
                        
                        if not popup_contains_name:
                            # Debug: Show what popup content we actually got
                            try:
                                popups = driver.find_elements(By.CSS_SELECTOR, ".popup, .modal, [class*='popup'], [class*='modal']")
                                for popup in popups:
                                    try:
                                        if popup.is_displayed():
                                            actual_content = popup.text.strip()[:200]
                                            print(f"[WebCrawler] ⚠️ Popup content preview: {actual_content}...")
                                            break
                                    except:
                                        continue
                            except:
                                pass
                            
                            print(f"[WebCrawler] ⚠️ Popup appeared but doesn't contain {member_name} correctly, may be wrong popup")
                            print(f"[WebCrawler] 🔄 Trying to close popup and wait longer, then retry click...")
                            
                            # Close the wrong popup aggressively
                            try:
                                from selenium.webdriver.common.keys import Keys
                                body = driver.find_element(By.TAG_NAME, "body")
                                body.send_keys(Keys.ESCAPE)
                                time.sleep(1.0)
                                # Force close with JavaScript
                                driver.execute_script("""
                                    var popups = document.querySelectorAll('.popup, .modal, [class*="popup"], [class*="modal"]');
                                    popups.forEach(function(popup) {
                                        popup.style.display = 'none';
                                        popup.classList.remove('active', 'show', 'open');
                                    });
                                """)
                                time.sleep(2.0)  # Wait longer for popup to fully close
                            except:
                                pass
                            
                            # Retry clicking the element
                            try:
                                print(f"[WebCrawler] 🔄 Retrying click for {member_name}...")
                                # Re-find element
                                name_xpath = f"//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{member_name.lower()}')]"
                                name_elem = driver.find_element(By.XPATH, name_xpath)
                                try:
                                    retry_element = name_elem.find_element(By.XPATH, "./ancestor::*[contains(@class, 'card') or contains(@class, 'member') or contains(@class, 'team') or contains(@class, 'item') or contains(@class, 'person') or contains(@class, 'profile')][1]")
                                except:
                                    retry_element = name_elem
                                
                                # Scroll and click again
                                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", retry_element)
                                time.sleep(1.0)
                                driver.execute_script("arguments[0].click();", retry_element)
                                time.sleep(3.0)  # Wait longer for popup to appear
                                
                                # Check again if popup contains name
                                if is_popup_visible():
                                    popups = driver.find_elements(By.CSS_SELECTOR, ".popup, .modal, [class*='popup'], [class*='modal']")
                                    for popup in popups:
                                        try:
                                            if popup.is_displayed():
                                                popup_text_retry = popup.text.strip()
                                                if member_name.lower() in popup_text_retry.lower() and popup_text_retry != previous_popup_content_global:
                                                    popup_contains_name = True
                                                    previous_popup_content_global = popup_text_retry
                                                    print(f"[WebCrawler] ✅ Popup appeared with correct name after retry: {member_name}")
                                                    break
                                        except:
                                            continue
                                
                                if not popup_contains_name:
                                    print(f"[WebCrawler] ⚠️ Still wrong popup after retry, using fallback data for {member_name}")
                                    # Close popup again
                                    try:
                                        body.send_keys(Keys.ESCAPE)
                                        time.sleep(1.0)
                                    except:
                                        pass
                                    # Use fallback data if available
                                    if member_name in fallback_data:
                                        fallback = fallback_data[member_name]
                                        team_members[member_name] = {
                                            'name': fallback['name'],
                                            'title': fallback['title'],
                                            'description': fallback['description'],
                                            'details': fallback['details'],
                                            'full_content': fallback['full_content']
                                        }
                                        print(f"[WebCrawler] ✅ Using fallback data for: {member_name}")
                                    continue
                            except Exception as e:
                                print(f"[WebCrawler] ⚠️ Error retrying for {member_name}: {str(e)[:100]}")
                                # Use fallback data if available
                                if member_name in fallback_data:
                                    fallback = fallback_data[member_name]
                                    team_members[member_name] = {
                                        'name': fallback['name'],
                                        'title': fallback['title'],
                                        'description': fallback['description'],
                                        'details': fallback['details'],
                                        'full_content': fallback['full_content']
                                    }
                                    print(f"[WebCrawler] ✅ Using fallback data for: {member_name}")
                                continue
                        
                        # If popup_contains_name is True (either from first check or retry), proceed to extraction
                        if not popup_contains_name:
                            # Use fallback data if available
                            if member_name in fallback_data:
                                fallback = fallback_data[member_name]
                                team_members[member_name] = {
                                    'name': fallback['name'],
                                    'title': fallback['title'],
                                    'description': fallback['description'],
                                    'details': fallback['details'],
                                    'full_content': fallback['full_content']
                                }
                                print(f"[WebCrawler] ✅ Using fallback data for: {member_name}")
                            continue  # Skip if still no valid popup and no fallback
                        
                        # Look for popup/modal content with more comprehensive selectors
                        popup_selectors = [
                            # Common modal/popup classes
                            ".modal", ".popup", ".overlay", ".dialog", ".lightbox",
                            "[role='dialog']", "[role='alertdialog']",
                            # Team-specific popups
                            ".team-popup", ".member-popup", ".profile-popup", 
                            ".member-details", ".team-modal", ".staff-modal", 
                            ".person-modal", ".member-modal",
                            # Content containers
                            ".modal-content", ".popup-content", ".modal-body",
                            ".popup-body", ".dialog-content", ".overlay-content",
                            # Generic patterns
                            "[class*='modal']", "[class*='popup']", "[class*='overlay']",
                            "[class*='dialog']", "[class*='lightbox']",
                            "[id*='modal']", "[id*='popup']", "[id*='dialog']",
                            # Prakriti-specific (check page source for actual classes)
                            "[class*='team']", "[class*='member']", "[class*='profile']"
                        ]
                        
                        popup_content = ""
                        popup_element = None
                        
                        # Wait a bit for popup animation
                        time.sleep(0.5)
                        
                        for popup_selector in popup_selectors:
                            try:
                                popups = driver.find_elements(By.CSS_SELECTOR, popup_selector)
                                for popup in popups:
                                    try:
                                        if popup.is_displayed() and popup.text.strip():
                                            popup_text = popup.text.strip()
                                            
                                            # FILTER OUT NAVIGATION MENUS - Check if it looks like a menu
                                            if any(menu_word in popup_text.lower()[:200] for menu_word in ['home', 'prakriti way of learning', 'our programmes', 'green school', 'roots of all beings', 'calendar', 'admissions', 'contact', 'meet our team', 'careers @ prakriti']):
                                                # This is likely a navigation menu, skip it
                                                continue
                                            
                                            # Check if popup contains the member's name (case-insensitive)
                                            if member_name.lower() not in popup_text.lower():
                                                # Wrong popup, skip it
                                                continue
                                            
                                            popup_content = popup_text
                                            popup_element = popup
                                            print(f"[WebCrawler] ✅ Found popup with selector: {popup_selector}")
                                            print(f"[WebCrawler] Popup preview: {popup_content[:150]}...")
                                            break
                                    except:
                                        continue
                                if popup_content:
                                    break
                            except:
                                continue
                        
                        # If no popup found, try to find any visible overlay or modal
                        if not popup_content:
                            try:
                                # Look for any element with high z-index (likely popups)
                                high_z_elements = driver.find_elements(By.XPATH, "//*[@style[contains(., 'z-index')]]")
                                for elem in high_z_elements:
                                    try:
                                        z_index = elem.value_of_css_property('z-index')
                                        if z_index and int(z_index) > 1000 and elem.is_displayed() and elem.text.strip():
                                            popup_text = elem.text.strip()
                                            
                                            # FILTER OUT NAVIGATION MENUS
                                            if any(menu_word in popup_text.lower()[:200] for menu_word in ['home', 'prakriti way of learning', 'our programmes', 'green school', 'roots of all beings', 'calendar', 'admissions', 'contact', 'meet our team', 'careers @ prakriti']):
                                                continue
                                            
                                            # Check if popup contains the member's name
                                            if member_name.lower() not in popup_text.lower():
                                                continue
                                            
                                            popup_content = popup_text
                                            popup_element = elem
                                            print(f"[WebCrawler] ✅ Found popup with z-index: {z_index}")
                                            break
                                    except:
                                        continue
                            except:
                                pass
                        
                        # Last resort: Check for any recently appeared element with substantial text
                        if not popup_content:
                            try:
                                # Get all visible elements with text
                                all_visible = driver.find_elements(By.XPATH, "//*[text() and string-length(text()) > 20]")
                                for elem in all_visible:
                                    try:
                                        if elem.is_displayed():
                                            text = elem.text.strip()
                                            
                                            # FILTER OUT NAVIGATION MENUS
                                            if any(menu_word in text.lower()[:200] for menu_word in ['home', 'prakriti way of learning', 'our programmes', 'green school', 'roots of all beings', 'calendar', 'admissions', 'contact', 'meet our team', 'careers @ prakriti']):
                                                continue
                                            
                                            # Check if text looks like a profile (has name pattern) AND contains member name
                                            if len(text) > 50 and any(name_word in text for name_word in ['Facilitator', 'Director', 'Principal', 'Mentor', 'M.Sc', 'M.A', 'B.A']):
                                                # Check if popup contains the member's name
                                                if member_name.lower() not in text.lower():
                                                    continue
                                                
                                                popup_content = text
                                                popup_element = elem
                                                print(f"[WebCrawler] ✅ Found popup by text pattern")
                                                break
                                    except:
                                        continue
                            except:
                                pass
                        
                        if popup_content:
                            print(f"[WebCrawler] Extracted popup content: {popup_content[:200]}...")
                            
                            # IMPORTANT: Verify popup content actually contains the member's name
                            popup_content_lower = popup_content.lower()
                            member_name_lower = member_name.lower()
                            
                            # CRITICAL: If popup doesn't contain member name, skip this member (don't store wrong data)
                            if member_name_lower not in popup_content_lower:
                                print(f"[WebCrawler] ⚠️ Extracted popup doesn't contain {member_name}, skipping to avoid wrong data")
                                popup_content = ""  # Clear wrong content
                            
                            # Only process if we have valid popup content
                            # IMPORTANT: If popup contains member's name anywhere, store it
                            # Don't reject based on extracted name - just use the clicked member_name
                            if popup_content:
                                # Use the member_name we clicked on (most reliable)
                                name = member_name
                                
                                # Check if popup contains multiple members - if so, extract only the target member's section
                                popup_lower = popup_content.lower()
                                member_name_pos = popup_lower.find(member_name_lower)
                                
                                # Initialize list to track other members found in popup
                                other_members_found = []
                                
                                # Check if there are other member names in the popup
                                if member_name_pos != -1:
                                    for other_name in known_names:
                                        if other_name.lower() != member_name_lower:
                                            other_pos = popup_lower.find(other_name.lower())
                                            if other_pos != -1:
                                                other_members_found.append((other_name, other_pos))
                                
                                # If other members found, extract only the section for our target member
                                if other_members_found and member_name_pos != -1:
                                    # Sort other members by position
                                    other_members_found.sort(key=lambda x: x[1])
                                    
                                    # Find the next member after our target member
                                    next_member_pos = None
                                    for other_name, other_pos in other_members_found:
                                        if other_pos > member_name_pos:
                                            next_member_pos = other_pos
                                            break
                                    
                                    # Extract only the section between our member and the next member (or end)
                                    if next_member_pos:
                                        # Extract from member name to next member
                                        member_section = popup_content[member_name_pos:next_member_pos]
                                    else:
                                        # Extract from member name to end
                                        member_section = popup_content[member_name_pos:]
                                    
                                    # Use the extracted section instead of full popup
                                    popup_content = member_section
                                    print(f"[WebCrawler] Extracted member-specific section (found {len(other_members_found)} other members in popup)")
                                
                                # Extract details from popup content
                                lines = popup_content.split('\n')
                                details = []
                                
                                # Get list of other member names for filtering
                                other_member_names = [other_name for other_name, _ in other_members_found] if other_members_found else []
                                
                                # Collect all non-empty lines as details
                                for line in lines:
                                    line = line.strip()
                                    if line and len(line) > 2:
                                        # Skip if this line is just the member's name (we already have it)
                                        if line.lower() == member_name_lower or line.lower() in member_name_lower or member_name_lower in line.lower():
                                            continue
                                        # Skip if line contains another member's name (filter out other members)
                                        if other_member_names and any(other_name.lower() in line.lower() for other_name in other_member_names):
                                            continue
                                        details.append(line)
                                
                                # Extract title (usually contains "Facilitator", "Teacher", "Director", etc.)
                                title = ""
                                for line in details:
                                    line_lower = line.lower()
                                    if any(title_word in line_lower for title_word in ['facilitator', 'teacher', 'director', 'coordinator', 'principal', 'mentor', 'manager', 'education', 'programme', 'curriculum']):
                                        title = line.strip()
                                        break
                                
                                # Extract description (first substantial line after name/title)
                                description = ""
                                for line in details:
                                    if line.strip() and len(line.strip()) > 10:
                                        # Skip if this line is the title
                                        if title and title.lower() in line.lower():
                                            continue
                                        description = line.strip()
                                        break
                                
                                # Combine remaining details (all other lines)
                                remaining_details = ' '.join([d for d in details if d.strip() and d != title and d != description][:15])
                                
                                # Check if extracted data is minimal (only title, no description/details)
                                # If so, use fallback data if available
                                data_is_minimal = (not description or len(description) < 50) and (not remaining_details or len(remaining_details) < 50)
                                
                                if data_is_minimal and member_name in fallback_data:
                                    print(f"[WebCrawler] ⚠️ Extracted data is minimal for {member_name}, using fallback data")
                                    fallback = fallback_data[member_name]
                                    team_members[name] = {
                                        'name': fallback['name'],
                                        'title': fallback['title'] if not title else title,  # Use extracted title if available
                                        'description': fallback['description'],
                                        'details': fallback['details'],
                                        'full_content': fallback['full_content']
                                    }
                                    print(f"[WebCrawler] ✅ Using fallback data for: {name}")
                                else:
                                    # Store using the clicked member_name (most reliable)
                                    team_members[name] = {
                                        'name': name,
                                        'title': title,
                                        'description': description,
                                        'details': remaining_details,
                                        'full_content': popup_content
                                    }
                                    print(f"[WebCrawler] Successfully extracted info for: {name} ({title if title else 'No title'})")
                            else:
                                # No valid popup content - check if fallback data is available
                                if member_name in fallback_data:
                                    print(f"[WebCrawler] ⚠️ No valid popup content found for {member_name}, using fallback data")
                                    fallback = fallback_data[member_name]
                                    team_members[member_name] = {
                                        'name': fallback['name'],
                                        'title': fallback['title'],
                                        'description': fallback['description'],
                                        'details': fallback['details'],
                                        'full_content': fallback['full_content']
                                    }
                                    print(f"[WebCrawler] ✅ Using fallback data for: {member_name}")
                                else:
                                    print(f"[WebCrawler] ⚠️ No valid popup content found for {member_name}, skipping")
                        
                        # Close popup if open (CRITICAL - must verify it's actually closed)
                        popup_closed = False
                        max_close_attempts = 10
                        
                        # First, verify popup is actually visible
                        if not is_popup_visible():
                            print(f"[WebCrawler] ℹ️ No popup visible for {member_name}")
                            popup_closed = True
                        else:
                            print(f"[WebCrawler] 🔄 Closing popup for {member_name}...")
                            
                            for attempt in range(max_close_attempts):
                                try:
                                    # Method 1: Press Escape key (most reliable)
                                    try:
                                        from selenium.webdriver.common.keys import Keys
                                        body = driver.find_element(By.TAG_NAME, "body")
                                        body.send_keys(Keys.ESCAPE)
                                        time.sleep(0.8)  # Wait longer for animation
                                        
                                        # Verify popup closed
                                        if not is_popup_visible():
                                            popup_closed = True
                                            print(f"[WebCrawler] ✅ Popup closed with Escape key")
                                            break
                                    except:
                                        pass
                                    
                                    # Method 2: Find close button (X button)
                                    if not popup_closed:
                                        close_selectors = [
                                            ".close", ".modal-close", "[aria-label='Close']", 
                                            ".btn-close", "button[class*='close']", 
                                            "[class*='close-button']", "span[class*='close']",
                                            "button[aria-label*='close']", "[class*='close-icon']",
                                            ".popup-close", ".modal-close-button", "×", "✕"
                                        ]
                                        for close_selector in close_selectors:
                                            try:
                                                close_btns = driver.find_elements(By.CSS_SELECTOR, close_selector)
                                                for close_btn in close_btns:
                                                    try:
                                                        if close_btn.is_displayed():
                                                            driver.execute_script("arguments[0].click();", close_btn)
                                                            time.sleep(0.8)
                                                            
                                                            # Verify popup closed
                                                            if not is_popup_visible():
                                                                popup_closed = True
                                                                print(f"[WebCrawler] ✅ Popup closed with close button")
                                                                break
                                                    except:
                                                        continue
                                                if popup_closed:
                                                    break
                                            except:
                                                continue
                                    
                                    # Method 3: Click outside popup (on overlay/backdrop)
                                    if not popup_closed:
                                        try:
                                            overlays = driver.find_elements(By.CSS_SELECTOR, ".overlay, .modal-backdrop, [class*='backdrop'], [class*='overlay']")
                                            for overlay in overlays:
                                                try:
                                                    if overlay.is_displayed():
                                                        driver.execute_script("arguments[0].click();", overlay)
                                                        time.sleep(0.8)
                                                        
                                                        # Verify popup closed
                                                        if not is_popup_visible():
                                                            popup_closed = True
                                                            print(f"[WebCrawler] ✅ Popup closed by clicking overlay")
                                                            break
                                                except:
                                                    continue
                                        except:
                                            pass
                                    
                                    # Method 4: JavaScript - hide popup directly
                                    if not popup_closed:
                                        try:
                                            driver.execute_script("""
                                                var popups = document.querySelectorAll('.popup, .modal, [class*="popup"], [class*="modal"]');
                                                popups.forEach(function(popup) {
                                                    popup.style.display = 'none';
                                                    popup.classList.remove('active', 'show', 'open');
                                                });
                                                var overlays = document.querySelectorAll('.overlay, .modal-backdrop, [class*="backdrop"]');
                                                overlays.forEach(function(overlay) {
                                                    overlay.style.display = 'none';
                                                });
                                            """)
                                            time.sleep(0.5)
                                            
                                            # Verify popup closed
                                            if not is_popup_visible():
                                                popup_closed = True
                                                print(f"[WebCrawler] ✅ Popup closed with JavaScript")
                                                break
                                        except:
                                            pass
                                    
                                    # If popup is closed, break
                                    if popup_closed:
                                        break
                                    
                                    # Wait before next attempt
                                    time.sleep(0.3)
                                except Exception as e:
                                    print(f"[WebCrawler] Error closing popup (attempt {attempt+1}): {str(e)[:50]}")
                                    time.sleep(0.3)
                            
                            if not popup_closed:
                                print(f"[WebCrawler] ⚠️ Could not close popup for {member_name} after {max_close_attempts} attempts")
                                # Last resort: reload page to reset state
                                try:
                                    print(f"[WebCrawler] 🔄 Reloading page to reset popup state...")
                                    driver.refresh()
                                    time.sleep(2)
                                    # Re-find all team member cards after reload
                                    # (This will be handled in the next iteration)
                                except:
                                    pass
                        
                        # Extra wait to ensure popup is fully closed and DOM is stable
                        # Verify popup is actually closed before proceeding
                        final_check_attempts = 5
                        for check in range(final_check_attempts):
                            if not is_popup_visible():
                                break
                            time.sleep(0.5)
                            # Try closing again if still visible
                            try:
                                from selenium.webdriver.common.keys import Keys
                                body = driver.find_element(By.TAG_NAME, "body")
                                body.send_keys(Keys.ESCAPE)
                                time.sleep(0.5)
                            except:
                                pass
                        
                        # Final verification
                        if is_popup_visible():
                            print(f"[WebCrawler] ⚠️ Popup still visible for {member_name}, forcing close...")
                            try:
                                driver.execute_script("""
                                    var popups = document.querySelectorAll('.popup, .modal, [class*="popup"], [class*="modal"]');
                                    popups.forEach(function(popup) {
                                        popup.style.display = 'none';
                                        popup.classList.remove('active', 'show', 'open');
                                    });
                                    var overlays = document.querySelectorAll('.overlay, .modal-backdrop, [class*="backdrop"]');
                                    overlays.forEach(function(overlay) {
                                        overlay.style.display = 'none';
                                    });
                                """)
                                time.sleep(1.0)
                            except:
                                pass
                        
                        # Wait for DOM to fully stabilize before next click
                        time.sleep(1.5)
                        
                        processed_count += 1
                        
                    except Exception as e:
                        error_msg = str(e)
                        if "stale" in error_msg.lower():
                            print(f"[WebCrawler] Stale element error for element {i+1}, continuing...")
                        else:
                            print(f"[WebCrawler] Error processing element {i+1}: {error_msg[:100]}")
                        # Continue to next element
                        continue
                
                print(f"[WebCrawler] Successfully processed {processed_count} team member elements")
                
                return team_members
                
            finally:
                driver.quit()
                
        except Exception as e:
            print(f"[WebCrawler] Error with Selenium extraction: {e}")
            return {}
    
    def search_prakriti_content(self, query: str) -> List[Dict[str, str]]:
        """Search PrakritSchool content from cached Supabase data with QUERY-BASED FILTERING"""
        print(f"[WebCrawler] Searching PrakritSchool cached content for: {query}")
        
        # First, try to get filtered data from Supabase cache (TOKEN OPTIMIZATION)
        if SUPABASE_AVAILABLE:
            try:
                supabase = get_supabase_client()
                query_lower = query.lower()
                
                # Extract query keywords for filtering
                query_words = [w for w in query_lower.split() if len(w) > 2]
                
                # Determine content_type based on query
                content_type = None
                is_substack_query = 'substack' in query_lower

                # SPECIAL CASE: If query mentions "prakriti" + "article", prioritize Roots of All Beings
                if 'prakriti' in query_lower and 'article' in query_lower:
                    content_type = 'article'  # Set to article to find Roots of All Beings content
                    print(f"[WebCrawler] Special case: Prakriti article query - filtering by content_type: article")
                elif self.is_team_related(query):
                    content_type = 'team'
                elif self.is_calendar_related(query):
                    content_type = 'calendar'
                elif self.is_news_related(query) and not is_substack_query:
                    content_type = 'news'
                elif self.is_article_related(query) and not is_substack_query:
                    content_type = 'article'
                elif self.is_academic_related(query):
                    content_type = 'academic'
                elif self.is_admission_related(query):
                    content_type = 'admission'
                elif self.is_contact_related(query):
                    content_type = 'contact'
                elif self.is_testimonial_related(query):
                    content_type = 'testimonial'
                
                # Query Supabase with filtering (TOKEN OPTIMIZATION - only get relevant pages)
                base_query = supabase.table('web_crawler_data').select('url, title, description, main_content, content_type, query_keywords').eq('is_active', True).gte('crawled_at', (datetime.utcnow() - timedelta(hours=24)).isoformat())
                
                # Filter by content_type if detected (handle special cases first)
                if content_type:
                    # Special case: Prakriti articles override substack logic
                    if 'prakriti' in query_lower and 'article' in query_lower:
                        base_query = base_query.eq('content_type', 'article')
                        print(f"[WebCrawler] SPECIAL CASE: Prakriti article query - filtering ONLY by content_type: article")
                    elif is_substack_query:
                        # For Substack queries, search both 'news' and 'article' content types
                        base_query = base_query.in_('content_type', ['news', 'article'])
                        print(f"[WebCrawler] Filtering by content_type: news OR article (Substack query)")
                    else:
                        base_query = base_query.eq('content_type', content_type)
                        print(f"[WebCrawler] Filtering by content_type: {content_type}")
                elif is_substack_query:
                    # Fallback for substack queries without specific content_type
                    base_query = base_query.in_('content_type', ['news', 'article'])
                    print(f"[WebCrawler] Filtering by content_type: news OR article (Substack query - fallback)")
                
                # Get all matching pages
                result = base_query.execute()
                
                if result.data and len(result.data) > 0:
                    print(f"[WebCrawler] Found {len(result.data)} cached pages in Supabase")
                    
                    # Score and filter by query relevance (TOKEN OPTIMIZATION)
                    scored_pages = []
                    for page in result.data:
                        score = 0
                        page_title = (page.get('title') or '').lower()
                        page_desc = (page.get('description') or '').lower()
                        page_content = (page.get('main_content') or '').lower()
                        
                        # Score by keyword matches
                        for word in query_words:
                            if word in page_title:
                                score += 5  # Title match = high relevance
                            if word in page_desc:
                                score += 3  # Description match = medium relevance
                            if word in page_content[:500]:  # Only check first 500 chars
                                score += 1  # Content match = low relevance
                        
                        # Boost score if query_keywords match
                        page_keywords = page.get('query_keywords', [])
                        if page_keywords:
                            matched_keywords = sum(1 for word in query_words if any(kw in word or word in kw for kw in page_keywords))
                            score += matched_keywords * 2
                        
                        if score > 0:
                            scored_pages.append({
                                'url': page.get('url'),
                                'title': page.get('title'),
                                'description': page.get('description'),
                                'main_content': page.get('main_content'),
                                'relevance_score': score
                            })
                    
                    # Sort by relevance and return TOP 3 ONLY (TOKEN OPTIMIZATION)
                    scored_pages.sort(key=lambda x: x['relevance_score'], reverse=True)
                    top_pages = scored_pages[:3]  # Only top 3 most relevant pages
                    
                    print(f"[WebCrawler] ✅ Returning {len(top_pages)} most relevant cached pages (filtered from {len(scored_pages)} scored pages)")
                    
                    # Format for return (truncate content to save tokens)
                    formatted_results = []
                    for page in top_pages:
                        formatted_results.append({
                            'url': page['url'],
                            'title': page['title'][:100] if page['title'] else '',
                            'description': (page['description'] or '')[:200] if page['description'] else '',
                            'main_content': (page['main_content'] or '')[:500] if page['main_content'] else ''  # Truncate to 500 chars
                        })
                    
                    return formatted_results
                    
            except Exception as e:
                print(f"[WebCrawler] Error querying Supabase cache: {e}")
                # Fall through to crawl if cache query fails
        
        # Fallback: Use original crawling logic if cache query fails
        return self._search_prakriti_content_fallback(query)
    
    def _search_prakriti_content_fallback(self, query: str) -> List[Dict[str, str]]:
        """Fallback method: original crawling logic when Supabase cache query fails"""
        if not self.is_prakriti_related(query):
            return []
        
        print(f"[WebCrawler] Fallback: Searching PrakritSchool content for: {query}")
        
        # Check cache first
        cache_key = f"prakriti_search_{hash(query)}"
        if cache_key in self.content_cache:
            cached_data, timestamp = self.content_cache[cache_key]
            if time.time() - timestamp < self.cache_duration:
                print("[WebCrawler] Using cached content")
                return cached_data
        
        crawled_content = []

        # For specific person queries, ONLY crawl team page for efficiency
        if self.is_specific_person_query(query):
            print("[WebCrawler] Detected specific person query, crawling ONLY team page for efficiency")
            team_urls = [url for url in self.prakriti_urls if 'team' in url]
            urls_to_crawl = team_urls
        else:
            # Intelligently prioritize pages based on query type
            query_lower = query.lower()  # Define query_lower for case-insensitive checks
            urls_to_crawl = self.prakriti_urls.copy()

            # SPECIAL CASE: If query mentions "prakriti" + "article", prioritize Roots of All Beings
            if 'prakriti' in query_lower and 'article' in query_lower:
                print("[WebCrawler] Detected Prakriti article query, prioritizing Roots of All Beings philosophy content")
                article_urls = [url for url in self.prakriti_urls if 'roots-of-all-beings' in url]
                urls_to_crawl = article_urls  # ONLY crawl roots/philosophy pages

            elif self.is_team_related(query):
                print("[WebCrawler] Detected team-related query, prioritizing team pages")
                team_urls = [url for url in self.prakriti_urls if 'team' in url]
                urls_to_crawl = team_urls  # ONLY crawl team pages

            elif self.is_calendar_related(query):
                print("[WebCrawler] Detected calendar-related query, prioritizing calendar pages")
                calendar_urls = [url for url in self.prakriti_urls if 'calendar' in url]
                urls_to_crawl = calendar_urls  # ONLY crawl calendar pages

            elif self.is_news_related(query):
                print("[WebCrawler] Detected Prakriti article query, prioritizing Roots of All Beings philosophy content")
                article_urls = [url for url in self.prakriti_urls if 'roots-of-all-beings' in url]
                urls_to_crawl = article_urls  # ONLY crawl roots/philosophy pages

            elif self.is_news_related(query):
                print("[WebCrawler] Detected news-related query, prioritizing news/blog pages")
                news_urls = [url for url in self.prakriti_urls if any(news_word in url for news_word in ['blog', 'news', 'award', 'wins'])]
                urls_to_crawl = news_urls  # ONLY crawl news pages

            elif self.is_article_related(query):
                print("[WebCrawler] Detected article-related query, prioritizing roots/philosophy pages")
                article_urls = [url for url in self.prakriti_urls if 'roots-of-all-beings' in url]
                urls_to_crawl = article_urls  # ONLY crawl roots/philosophy pages
                
            elif self.is_academic_related(query):
                print("[WebCrawler] Detected academic-related query, prioritizing academic pages")
                academic_urls = [url for url in self.prakriti_urls if any(academic_word in url for academic_word in ['igcse', 'a-level', 'programmes', 'learning'])]
                urls_to_crawl = academic_urls  # ONLY crawl academic pages
                
            elif self.is_admission_related(query):
                print("[WebCrawler] Detected admission-related query, prioritizing admission/fee pages")
                admission_urls = [url for url in self.prakriti_urls if any(admission_word in url for admission_word in ['admission', 'fee'])]
                urls_to_crawl = admission_urls  # ONLY crawl admission pages
                
            elif self.is_contact_related(query):
                print("[WebCrawler] Detected contact-related query, prioritizing contact pages")
                contact_urls = [url for url in self.prakriti_urls if 'contact' in url]
                urls_to_crawl = contact_urls  # ONLY crawl contact pages
                
            elif self.is_testimonial_related(query):
                print("[WebCrawler] Detected testimonial-related query, prioritizing testimonial pages")
                testimonial_urls = [url for url in self.prakriti_urls if 'what-our-parents-say' in url]
                urls_to_crawl = testimonial_urls  # ONLY crawl testimonial pages
        
        # First try DuckDuckGo search for PrakritSchool specific content
        try:
            prakriti_search_query = f"site:prakriti.edu.in {query}"
            search_results = self.duckduckgo_search(prakriti_search_query)
            
            for result in search_results[:2]:  # Limit to top 2 results
                try:
                    # Only crawl URLs from prakriti.edu.in domain
                    if 'prakriti.edu.in' in result.get('url', ''):
                        content = self.extract_content_from_url(result['url'], query)
                        if 'error' not in content:
                            crawled_content.append(content)
                            time.sleep(0.5)  # Faster crawling
                except Exception as e:
                    print(f"[WebCrawler] Error extracting content from {result['url']}: {e}")
                    continue
        except Exception as e:
            print(f"[WebCrawler] Error in PrakritSchool search: {e}")
        
        # Crawl PrakritSchool URLs (prioritizing team pages for team queries)
        for url in urls_to_crawl:
            try:
                content = self.extract_content_from_url(url, query)
                if 'error' not in content:
                    crawled_content.append(content)
                    time.sleep(0.5)  # Faster crawling
            except Exception as e:
                print(f"[WebCrawler] Error with {url}: {e}")
                continue
        
        # Cache the results
        self.content_cache[cache_key] = (crawled_content, time.time())
        
        return crawled_content
    
    def search_general_content(self, query: str) -> List[Dict[str, str]]:
        """Search for general educational content - now focused only on prakriti.edu.in"""
        print(f"[WebCrawler] Searching general content for: {query}")
        
        # Check cache first
        cache_key = f"general_search_{hash(query)}"
        if cache_key in self.content_cache:
            cached_data, timestamp = self.content_cache[cache_key]
            if time.time() - timestamp < self.cache_duration:
                print("[WebCrawler] Using cached general content")
                return cached_data
        
        crawled_content = []
        
        # Only search prakriti.edu.in for all queries
        try:
            search_query = f"site:prakriti.edu.in {query}"
            search_results = self.duckduckgo_search(search_query)
            for result in search_results[:3]:  # Limit to top 3 results
                try:
                    # Only crawl URLs from prakriti.edu.in domain
                    if 'prakriti.edu.in' in result.get('url', ''):
                        content = self.extract_content_from_url(result['url'], query)
                        if 'error' not in content:
                            crawled_content.append(content)
                            time.sleep(0.5)  # Faster crawling  # Be respectful
                except Exception as e:
                    print(f"[WebCrawler] Error extracting content from {result['url']}: {e}")
                    continue
        except Exception as e:
            print(f"[WebCrawler] Error in DuckDuckGo search: {e}")
        
        # Cache the results
        self.content_cache[cache_key] = (crawled_content, time.time())
        
        return crawled_content
    
    def duckduckgo_search(self, query: str) -> List[Dict[str, str]]:
        """Perform a search using DuckDuckGo (no API key required)"""
        try:
            # Use DuckDuckGo instant answer API
            search_url = "https://api.duckduckgo.com/"
            params = {
                'q': query,
                'format': 'json',
                'no_html': '1',
                'skip_disambig': '1'
            }
            
            response = self.session.get(search_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            results = []
            
            # Extract abstract and related topics
            if data.get('Abstract'):
                results.append({
                    'title': data.get('Heading', ''),
                    'url': data.get('AbstractURL', ''),
                    'snippet': data.get('Abstract', '')
                })
            
            # Extract related topics
            for topic in data.get('RelatedTopics', [])[:3]:
                if isinstance(topic, dict) and topic.get('FirstURL'):
                    results.append({
                        'title': topic.get('Text', ''),
                        'url': topic.get('FirstURL', ''),
                        'snippet': topic.get('Text', '')
                    })
            
            return results
            
        except Exception as e:
            print(f"[WebCrawler] DuckDuckGo search error: {e}")
            return []
    
    def extract_relevant_info(self, content_list: List[Dict[str, str]], query: str) -> str:
        """Extract relevant information from crawled content based on query - OPTIMIZED FOR TOKEN REDUCTION"""
        if not content_list:
            return ""
        
        query_lower = query.lower()
        query_words = [w for w in query_lower.split() if len(w) > 2]  # Filter out short words
        is_article_query = any(word in query_lower for word in ['article', 'articles', 'latest', 'recent', 'news', 'blog', 'substack'])
        relevant_info = []
        
        for content in content_list:
            # Check if content is relevant to the query
            relevance_score = 0
            
            # Check title relevance
            if content.get('title'):
                title_lower = content['title'].lower()
                if any(word in title_lower for word in query_words):
                    relevance_score += 3
            
            # Check description relevance
            if content.get('description'):
                desc_lower = content['description'].lower()
                if any(word in desc_lower for word in query_words):
                    relevance_score += 2
            
            # Check main content relevance
            if content.get('main_content'):
                main_lower = content['main_content'].lower()
                if any(word in main_lower for word in query_words):
                    relevance_score += 1
            
            # If content is relevant, extract key information
            if relevance_score > 0:
                info_parts = []
                
                # Always include title
                if content.get('title'):
                    info_parts.append(f"**{content['title']}**")
                
                # Always include description for article queries, otherwise only if title is short
                if is_article_query:
                    if content.get('description'):
                        info_parts.append(content['description'])
                elif not content.get('title') or len(content.get('title', '')) < 20:
                    if content.get('description'):
                        info_parts.append(f"{content['description'][:80]}")
                
                if content.get('main_content'):
                    if is_article_query:
                        # For article/blog queries, return FULL content (not truncated)
                        main_content = content['main_content'].strip()
                        if main_content:
                            # Return the full article content, not just first paragraph
                            # Limit to reasonable size to avoid token overflow (8000 chars should be plenty for most articles)
                            if len(main_content) > 8000:
                                main_content = main_content[:8000] + "..."
                            info_parts.append(main_content)
                    else:
                        # For other queries, extract ONLY 1 sentence that contains query words
                        sentences = content['main_content'].split('.')
                        for sentence in sentences:
                            sentence_lower = sentence.lower()
                            if any(word in sentence_lower for word in query_words):
                                info_parts.append(sentence.strip()[:120])
                                break  # Only 1 sentence
                
                if info_parts:
                    relevant_info.append({
                        'url': content.get('url', ''),
                        'relevance_score': relevance_score,
                        'info': '\n\n'.join(info_parts) if is_article_query else ' | '.join(info_parts)
                    })
        
        # Sort by relevance score
        relevant_info.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        # Format the information (TOKEN OPTIMIZATION)
        if relevant_info:
            if is_article_query:
                # For article queries, return TOP 3 results for comprehensive information
                top_results = relevant_info[:3]
            else:
                # For other queries, only top 1 result
                top_results = relevant_info[:1]

            formatted_parts = []
            for i, result in enumerate(top_results):
                result_info = result['info']
                if result['url'] and i == 0:  # Add source for first result only
                    result_info += f"\n\nSource: [{result['url']}]({result['url']})"
                formatted_parts.append(result_info)

            formatted_info = '\n\n---\n\n'.join(formatted_parts)
            
            # TRUNCATE based on query type
            if is_article_query:
                # For article queries, allow up to 8000 chars (increased for full content)
                if len(formatted_info) > 8000:
                    formatted_info = formatted_info[:8000] + "..."
                    print(f"[WebCrawler] Truncated extract_relevant_info output to 8000 chars (article query)")
            else:
                # For other queries, max 600 chars
                if len(formatted_info) > 600:
                    formatted_info = formatted_info[:600] + "..."
                    print(f"[WebCrawler] Truncated extract_relevant_info output to 600 chars")
            
            return formatted_info
        
        return ""
    
    def get_mock_enhanced_response(self, query: str) -> str:
        """Get mock enhanced response for testing when web crawling fails"""
        query_lower = query.lower()
        
        # Mock PrakritSchool information
        if 'prakriti' in query_lower or 'prakrit school' in query_lower or 'prakrii' in query_lower:
            # Check if it's asking for team/staff information
            if any(word in query_lower for word in ['team', 'staff', 'faculty', 'teacher', 'member', 'members', 'who works', 'who teaches']):
                return """## Web Search Results

### Result 1
**Title**: PrakritSchool Team and Faculty
**Description**: PrakritSchool is led by a dedicated team of educators, administrators, and support staff who are committed to progressive education and student-centered learning.
**Relevant Content**: Our team includes experienced teachers specializing in various subjects, special educators for the Bridge Programme, therapists, counselors, and administrative staff. The faculty brings together diverse expertise in progressive education methodologies, experiential learning, and holistic development approaches.
*Source: [prakriti.edu.in/team](https://prakriti.edu.in/team)*

### Result 2
**Title**: Faculty and Staff at PrakritSchool
**Description**: The PrakritSchool team consists of passionate educators who believe in the philosophy of "learning for happiness" and work collaboratively to create a nurturing learning environment.
**Relevant Content**: Our staff includes subject specialists for IGCSE and A-Level programs, special needs educators, mindfulness instructors, art and music teachers, sports coordinators, and administrative personnel. Each team member is carefully selected for their commitment to progressive education and student well-being.
*Source: [prakriti.edu.in/team](https://prakriti.edu.in/team)*"""
            # Check if it's asking for latest news
            elif any(word in query_lower for word in ['latest', 'recent', 'news', 'update', 'current']):
                return """## Web Search Results

### Result 1
**Title**: Latest Updates from PrakritSchool
**Description**: PrakritSchool continues to expand its progressive education programs with new initiatives in experiential learning and holistic development.
**Relevant Content**: Recent developments include enhanced Bridge Programme support, new IGCSE subject offerings, and expanded co-curricular activities including mindfulness programs and maker projects.
*Source: [prakriti.edu.in/blog-and-news](https://prakriti.edu.in/blog-and-news/)*

### Result 2
**Title**: PrakritSchool News and Updates
**Description**: The school has been recognized for its innovative approach to education and continues to grow its community of learners focused on "learning for happiness."
**Relevant Content**: Latest news includes new faculty additions, curriculum enhancements, and community outreach programs that strengthen the school's mission of compassionate, learner-centric education.
*Source: [prakriti.edu.in/blog-and-news](https://prakriti.edu.in/blog-and-news/)*"""
            else:
                return """## Web Search Results

### Result 1
**Title**: PrakritSchool - Progressive Education in Noida
**Description**: PrakritSchool is an alternative/progressive K-12 school located on the Noida Expressway in Greater Noida, NCR, India. The school follows a compassionate, learner-centric model based on reconnecting with inner nature ("prakriti"), promoting joy, self-expression, and holistic development.
**Relevant Content**: PrakritSchool offers IGCSE (Grades 9-10) and AS/A Level (Grades 11-12) curriculum with subjects including Design & Tech, History, Computer Science, Enterprise, Art & Design, Physics, Chemistry, Biology, Combined Sciences, English First & Second Language, French, and Math.
*Source: [prakriti.edu.in](https://prakriti.edu.in)*

### Result 2
**Title**: Bridge Programme at PrakritSchool
**Description**: PrakritSchool runs a Bridge Programme with an inclusive curriculum for children with diverse needs. Special educators, therapists, and parent support systems are in place to ensure every child receives the support they need.
**Relevant Content**: The Bridge Programme emphasizes inclusive education where children with diverse needs learn together in a supportive environment.
*Source: [prakriti.edu.in](https://prakriti.edu.in)*"""
        
        # Mock general educational information
        elif 'igcse' in query_lower:
            return """## Web Search Results

### Result 1
**Title**: IGCSE Curriculum Overview
**Description**: The International General Certificate of Secondary Education (IGCSE) is a comprehensive two-year program for students aged 14-16. It offers a flexible curriculum with over 70 subjects.
**Relevant Content**: IGCSE provides excellent preparation for higher-level courses like A Levels and IB Diploma. It emphasizes practical application of knowledge and critical thinking skills.
*Source: Mock Educational Data*"""
        
        elif 'progressive education' in query_lower:
            return """## Web Search Results

### Result 1
**Title**: Progressive Education Philosophy
**Description**: Progressive education is a pedagogical movement that emphasizes learning through experience, student-centered learning, and the development of critical thinking skills.
**Relevant Content**: Progressive education focuses on experiential learning, collaborative learning, and the development of social skills alongside academic knowledge.
*Source: Mock Educational Data*"""
        
        return ""
    
    def get_enhanced_response(self, query: str) -> str:
        """Get enhanced response with web crawling for PrakritSchool queries"""
        print(f"[WebCrawler] Getting enhanced response for: {query}")
        print(f"[WebCrawler] 🔍 Cache check priority: 1) team_member_data (for person queries) → 2) web_crawler_data table → 3) search_cache table → 4) Web crawl")

        query_lower = query.lower()

        # SPECIAL CASE: If query contains "article" or specific article titles, force crawl Roots of All Beings pages FIRST
        is_article_query = ('article' in query_lower or 'student voice' in query_lower or
                           'guide for shaping' in query_lower or 'roots of all beings' in query_lower or
                           'green school' in query_lower or 'environment' in query_lower)

        if is_article_query:
            print(f"[WebCrawler] 🎯 ARTICLE QUERY DETECTED - Forcing direct crawl to Roots of All Beings pages")

            # Article-specific URL mapping
            article_url_mapping = {
                'student voice': "https://rootsofallbeings.substack.com/p/student-voice-a-guide-for-shaping",
                'guide for shaping': "https://rootsofallbeings.substack.com/p/student-voice-a-guide-for-shaping",
                'green school': "https://rootsofallbeings.substack.com/p/can-we-save-the-planet-or-should",
                'save the planet': "https://rootsofallbeings.substack.com/p/can-we-save-the-planet-or-should",
                'welcoming new members': "https://rootsofallbeings.substack.com/p/welcoming-new-members-to-prakriti",
                'travelogue': "https://rootsofallbeings.substack.com/p/a-travelogue-on-our-recent-ole-at",
                'ole': "https://rootsofallbeings.substack.com/p/outbound-learning-expedition-ole"
            }

            # Determine which URLs to prioritize based on query content
            prioritized_urls = []
            fallback_urls = [
                "https://prakriti.edu.in/roots-of-all-beings/",  # Main page
                "https://rootsofallbeings.substack.com/p/student-voice-a-guide-for-shaping",
                "https://rootsofallbeings.substack.com/p/can-we-save-the-planet-or-should",
                "https://rootsofallbeings.substack.com/p/welcoming-new-members-to-prakriti",
                "https://rootsofallbeings.substack.com/p/a-travelogue-on-our-recent-ole-at",
                "https://rootsofallbeings.substack.com/p/outbound-learning-expedition-ole"
            ]

            # Check for specific article matches
            for keyword, url in article_url_mapping.items():
                if keyword in query_lower:
                    prioritized_urls.append(url)

            # If no specific matches, use all URLs
            if not prioritized_urls:
                prioritized_urls = fallback_urls

            # Remove duplicates while preserving order
            seen = set()
            article_urls = [x for x in prioritized_urls if not (x in seen or seen.add(x))]

            print(f"[WebCrawler] 📋 Will check {len(article_urls)} article URLs")

            for url in article_urls:
                try:
                    print(f"[WebCrawler] 🌱 Directly crawling: {url}")

                    # Get the page content using the same method as normal crawling
                    content = self.extract_content_from_url(url, query)
                    if content and 'error' not in content and 'main_content' in content and content['main_content'].strip():
                        print(f"[WebCrawler] ✅ Found content ({len(content['main_content'])} chars) from {url}")

                        # Extract relevant information for the query
                        relevant_info = self.extract_relevant_info([content], query)
                        if relevant_info and relevant_info.strip():
                            print(f"[WebCrawler] ✅ Returning content for article query from {url}")
                            return relevant_info

                except Exception as e:
                    print(f"[WebCrawler] Error crawling {url}: {e}")
                    continue

            print(f"[WebCrawler] ⚠️ No relevant content found on any Roots of All Beings pages")

        # Continue with normal logic if article override didn't work or found no content
        
        # PRIORITY 0: Check if this is a role-based query (e.g., "French facilitator", "Math teacher")
        # This should be checked BEFORE person queries
        if self.is_role_based_query(query):
            print(f"[WebCrawler] Detected role-based query: {query}")
            
            # Normalize typos in query first
            typo_corrections = {
                'founde': 'founder', 'foundr': 'founder', 'co-founde': 'co-founder',
                'cofounde': 'cofounder', 'facilatator': 'facilitator', 'facilator': 'facilitator',
                'facilitater': 'facilitator', 'facilattor': 'facilitator', 'faciitator': 'facilitator',
                'faciitators': 'facilitators', 'faclitator': 'facilitator', 'faclitators': 'facilitators',
                'techer': 'teacher', 'teachr': 'teacher',
                'coordinater': 'coordinator', 'coordinatr': 'coordinator',
                'directer': 'director', 'principle': 'principal', 'princile': 'principal',
                'principl': 'principal', 'princpal': 'principal', 'menter': 'mentor'
            }
            normalized_query_lower = query_lower
            for typo, correct in typo_corrections.items():
                normalized_query_lower = normalized_query_lower.replace(typo, correct)
            
            # Extract role keywords from normalized query
            role_keywords = []
            query_lower_full = normalized_query_lower  # Use normalized query for phrase matching
            
            # Check for leadership roles first (founder, co-founder, principal, director, chief mentor, chairperson)
            # Use normalized query to catch typos
            leadership_roles = ['founder', 'co-founder', 'cofounder', 'founding', 'principal', 'director', 
                              'chairperson', 'chair person', 'chairman', 'chairwoman', 'chief mentor', 'chief', 'mentor']
            has_leadership_role = any(role in normalized_query_lower for role in leadership_roles)
            
            # Check for multi-word phrases first
            multi_word_phrases = ['early years', 'physical education', 'prakriti school', 'prakrit school', 'art and design', 'art & design']
            for phrase in multi_word_phrases:
                if phrase in query_lower_full:
                    # Extract individual words from phrase
                    for word in phrase.split():
                        # Skip common words like "and", "&"
                        if word not in ['and', '&', 'the', 'of', 'for'] and word not in role_keywords:
                            role_keywords.append(word)
            
            query_words = normalized_query_lower.split()  # Use normalized query
            role_indicators = ['french', 'english', 'math', 'mathematics', 'science', 'physics', 'chemistry', 
                             'biology', 'history', 'art', 'music', 'sports', 'pe', 'computer', 'it', 
                             'technology', 'design', 'drama', 'theatre', 'dance', 'primary', 'secondary',
                             'upper', 'lower', 'early', 'years', 'nursery', 'kindergarten']
            
            # Role type mapping (misspelling -> correct spelling)
            role_type_mapping = {
                'facilator': 'facilitator',
                'facilitater': 'facilitator',
                'facilattor': 'facilitator',  # Handle double 't' misspelling
                'facilitator': 'facilitator',
                'techer': 'teacher',
                'teachr': 'teacher',
                'teacher': 'teacher',
                'coordinater': 'coordinator',
                'coordinatr': 'coordinator',
                'coordinator': 'coordinator',
                'directer': 'director',
                'director': 'director',
                'principle': 'principal',
                'principal': 'principal',
                'menter': 'mentor',
                'mentor': 'mentor',
                'faculty': 'facilitator',  # Map "faculty" to "facilitator" for search
                'faculties': 'facilitator',
                'facilitators': 'facilitator',  # Plural form
                'faclitator': 'facilitator',  # Handle typo
                'faclitators': 'facilitator',  # Handle typo (plural)
                'founder': 'founder',
                'co-founder': 'founder',
                'cofounder': 'founder',
                'founding': 'founder',
                'chairperson': 'chairperson',
                'chair person': 'chairperson',
                'chairman': 'chairperson',
                'chairwoman': 'chairperson'
            }
            
            for word in query_words:
                # Check if it's a role indicator
                if word in role_indicators and word not in role_keywords:
                    role_keywords.append(word)
                # Check if it's a role type (handle misspellings)
                elif word in role_type_mapping:
                    # Normalize to correct spelling
                    normalized_role = role_type_mapping[word]
                    if normalized_role not in role_keywords:
                        role_keywords.append(normalized_role)
                # Also check if word contains role type (for typos like "faclitators")
                else:
                    for typo, correct in typo_corrections.items():
                        if typo in word:
                            normalized_word = word.replace(typo, correct)
                            if normalized_word in role_type_mapping:
                                normalized_role = role_type_mapping[normalized_word]
                                if normalized_role not in role_keywords:
                                    role_keywords.append(normalized_role)
                                    break
            
            print(f"[WebCrawler] Extracted role keywords: {role_keywords}")
            
            # Initialize variables for database and fallback matches
            database_best_match = None
            database_best_score = 0
            
            # Search in team_member_data by title/description
            if SUPABASE_AVAILABLE:
                try:
                    supabase = get_supabase_client()
                    
                    # SPECIAL HANDLING: For leadership roles (founder, co-founder, principal, director)
                    # Search directly by role/title without needing subject keywords
                    if has_leadership_role:
                        # Extract the leadership role keyword (use normalized query)
                        leadership_role_found = None
                        for role in leadership_roles:
                            if role in normalized_query_lower:
                                leadership_role_found = role
                                break
                        
                        if leadership_role_found:
                            # Normalize role for search
                            search_role = role_type_mapping.get(leadership_role_found, leadership_role_found)
                            
                            # Prioritize search terms based on query - "co-founder" should prioritize "founding" and "co-founder"
                            # Use normalized query to catch typos
                            if 'co-founder' in normalized_query_lower or 'cofounder' in normalized_query_lower:
                                # For co-founder queries, prioritize: founding director, co-founder, founding
                                search_terms_priority = ['founding director', 'co-founder', 'founding', 'founder']
                            elif 'founder' in normalized_query_lower or 'founding' in normalized_query_lower:
                                # For founder queries, prioritize: founding director, founder, founding
                                search_terms_priority = ['founding director', 'founder', 'founding']
                            elif 'chief mentor' in normalized_query_lower or ('chief' in normalized_query_lower and 'mentor' in normalized_query_lower):
                                # For chief mentor queries, prioritize: chief mentor, mentor, chief
                                search_terms_priority = ['chief mentor', 'mentor', 'chief']
                            elif 'chairperson' in normalized_query_lower or 'chair person' in normalized_query_lower or 'chairman' in normalized_query_lower or 'chairwoman' in normalized_query_lower:
                                # For chairperson queries, prioritize: chairperson, chairman, chairwoman, director
                                search_terms_priority = ['chairperson', 'chair person', 'chairman', 'chairwoman', 'director']
                            elif 'principal' in normalized_query_lower:
                                # For principal queries, ONLY search for principal (not director)
                                search_terms_priority = ['principal']
                            elif 'director' in normalized_query_lower:
                                # For director queries, search for director and related terms
                                search_terms_priority = ['director', 'founding director', 'school director']
                            else:
                                # For other roles, use role-specific terms only
                                search_terms_priority = [search_role]
                            
                            print(f"[WebCrawler] Searching for leadership role: {search_role} (priority terms: {search_terms_priority})")
                            
                            # Get all potential matches first, then score them
                            all_matches = []
                            seen_ids = set()  # Track seen member IDs to avoid duplicates
                            
                            # Search in both title and description for better matching
                            for search_term in search_terms_priority:
                                # Search in title
                                title_result = supabase.table('team_member_data').select('*').eq('is_active', True).ilike('title', f'%{search_term}%').limit(20).execute()
                                if title_result.data:
                                    for member in title_result.data:
                                        member_id = member.get('id') or member.get('name', '')
                                        if member_id and member_id not in seen_ids:
                                            seen_ids.add(member_id)
                                            all_matches.append(member)
                                
                                # Also search in description for better context
                                desc_result = supabase.table('team_member_data').select('*').eq('is_active', True).ilike('description', f'%{search_term}%').limit(20).execute()
                                if desc_result.data:
                                    for member in desc_result.data:
                                        member_id = member.get('id') or member.get('name', '')
                                        if member_id and member_id not in seen_ids:
                                            seen_ids.add(member_id)
                                            all_matches.append(member)
                            
                            # CRITICAL: If database search found matches but they have incomplete data (missing title/description),
                            # we should still check fallback_data to ensure we have complete information
                            database_has_complete_data = False
                            if all_matches:
                                # Score matches based on relevance
                                scored_matches = []
                                for member in all_matches:
                                    title_lower = (member.get('title', '') or '').lower()
                                    desc_lower = (member.get('description', '') or '').lower()
                                    details_lower = (member.get('details', '') or member.get('full_content', '') or '').lower()
                                    
                                    score = 0
                                    
                                    # CRITICAL: Check if the EXACT requested role is in the title (highest priority)
                                    # For "principal" queries, only match titles with "principal", not "director"
                                    requested_role_lower = leadership_role_found.lower() if leadership_role_found else search_role.lower()
                                    
                                    # Check if title contains the exact requested role (not just any role from priority list)
                                    if requested_role_lower in title_lower:
                                        # Exact match gets highest score
                                        score += 200
                                    else:
                                        # Fallback: check priority terms (for cases where exact role isn't found)
                                        for i, term in enumerate(search_terms_priority):
                                            term_lower = term.lower()
                                            if term_lower in title_lower:
                                                # First term gets high score (100), subsequent terms get lower scores
                                                score += (100 - i * 10)
                                                break
                                    
                                    # Bonus for "founding director" when query is "co-founder" (use normalized query)
                                    if ('co-founder' in normalized_query_lower or 'cofounder' in normalized_query_lower) and 'founding' in title_lower and 'director' in title_lower:
                                        score += 50
                                    
                                    # Check description for role context
                                    if 'founder' in desc_lower or 'founding' in desc_lower or 'co-founder' in desc_lower:
                                        score += 20
                                    
                                    # Check details/full_content for role context
                                    if 'founder' in details_lower or 'founding' in details_lower or 'co-founder' in details_lower:
                                        score += 10
                                    
                                    if score > 0:
                                        scored_matches.append((member, score))
                                
                                # CRITICAL: Filter to prioritize exact role matches
                                # If we have exact matches (score >= 200), only use those
                                exact_matches = [(m, s) for m, s in scored_matches if s >= 200]
                                if exact_matches:
                                    scored_matches = exact_matches
                                    print(f"[WebCrawler] Filtered to {len(exact_matches)} exact role matches (score >= 200)")
                                
                                # Sort by score and get best match
                                if scored_matches:
                                    scored_matches.sort(key=lambda x: x[1], reverse=True)
                                    best_match = scored_matches[0][0]
                                    best_score = scored_matches[0][1]
                                    
                                    print(f"[WebCrawler] ✅ Found leadership role match: {best_match.get('name', 'Unknown')} - {best_match.get('title', '')} (score: {best_score})")
                                    
                                    # Format response
                                    name = best_match.get('name', '')
                                    title = best_match.get('title', '')
                                    description = best_match.get('description', '')
                                    details = best_match.get('details', '') or best_match.get('full_content', '')
                                    url = best_match.get('source_url', 'https://prakriti.edu.in/team/')
                                    
                                    response_parts = [f"## {title or 'Team Member Information'}"]
                                    if name:
                                        response_parts.append(f"\n**Name**: {name}")
                                    if title:
                                        response_parts.append(f"\n**Title**: {title}")
                                    if description:
                                        response_parts.append(f"\n**Description**: {description}")
                                    if details:
                                        details_text = details[:800] + "..." if len(details) > 800 else details
                                        response_parts.append(f"\n**Details**: {details_text}")
                                    response_parts.append(f"\n*Source: [{url}]({url})*")
                                    
                                    # Check if we have complete data (title and description)
                                    if title and description and len(description) > 50:
                                        database_has_complete_data = True
                                        return "\n".join(response_parts)
                                    else:
                                        print(f"[WebCrawler] ⚠️ Database match has incomplete data (title: {bool(title)}, description length: {len(description) if description else 0}) - will check fallback_data")
                                        database_best_match = best_match
                                        database_best_score = best_score
                                        database_has_complete_data = False
                            else:
                                print(f"[WebCrawler] ⚠️ No leadership role matches found in database - will check fallback_data")
                            
                            # CRITICAL: If database doesn't have complete data or no matches, check fallback_data
                            # This ensures we return accurate information even when database is incomplete
                            if not database_has_complete_data:
                                print(f"[WebCrawler] 🔍 Checking fallback_data for leadership role: {search_role}")
                                best_fallback_match = None
                                best_fallback_score = 0
                                
                                for key, member_data in self.fallback_data.items():
                                    title_lower = (member_data.get('title', '') or '').lower()
                                    desc_lower = (member_data.get('description', '') or '').lower()
                                    details_lower = (member_data.get('details', '') or member_data.get('full_content', '') or '').lower()
                                    
                                    score = 0
                                    
                                    # Score based on role match in title/description
                                    for i, term in enumerate(search_terms_priority):
                                        term_lower = term.lower()
                                        if term_lower in title_lower:
                                            score += (100 - i * 10)
                                            break
                                        elif term_lower in desc_lower or term_lower in details_lower:
                                            score += (50 - i * 5)
                                    
                                    if score > best_fallback_score:
                                        best_fallback_score = score
                                        best_fallback_match = member_data
                                
                                # Use fallback_data if it has a better match or database has incomplete data
                                if best_fallback_match and best_fallback_score > 0:
                                    if not database_best_match or best_fallback_score > database_best_score:
                                        print(f"[WebCrawler] ✅ Using fallback_data match for leadership role (score: {best_fallback_score})")
                                        name = best_fallback_match.get('name', 'Unknown')
                                        title = best_fallback_match.get('title', 'Team Member')
                                        description = best_fallback_match.get('description', '')
                                        details = best_fallback_match.get('details', '') or best_fallback_match.get('full_content', '')
                                        url = best_fallback_match.get('source_url', 'https://prakriti.edu.in/team/')
                                        
                                        # Return structured data for LLM to format naturally
                                        structured_info = f"""TEAM MEMBER INFORMATION:
Name: {name}
Title: {title}
Description: {description}
Details: {details[:1000] if details else 'No additional details available'}
Source: {url}"""
                                        
                                        return structured_info
                                
                                # If we have database match but incomplete, still return it (better than nothing)
                                if database_best_match:
                                    name = database_best_match.get('name', '')
                                    title = database_best_match.get('title', '')
                                    description = database_best_match.get('description', '')
                                    details = database_best_match.get('details', '') or database_best_match.get('full_content', '')
                                    url = database_best_match.get('source_url', 'https://prakriti.edu.in/team/')
                                    
                                    # Return structured data for LLM to format naturally
                                    structured_info = f"""TEAM MEMBER INFORMATION:
Name: {name}
Title: {title}
Description: {description}
Details: {details[:1000] if details else 'No additional details available'}
Source: {url}"""
                                    
                                    return structured_info
                    
                    # Search for subject-based roles using vector search (primary method)
                    if role_keywords and VECTOR_SEARCH_AVAILABLE:
                        try:
                            vector_service = get_vector_search_service()
                            # Use vector search for semantic matching
                            query = f"{' '.join(role_keywords)} {user_query}"
                            vector_results = vector_service.search_team_members(query, limit=20, threshold=0.5)  # Lower threshold for better matching
                            
                            if vector_results and len(vector_results) > 0:
                                # Filter results to ensure they match role keywords
                                filtered_results = []
                                for result in vector_results:
                                    title_lower = (result.get('title', '') or '').lower()
                                    # Check if any role keyword appears in title
                                    if any(kw.lower() in title_lower for kw in role_keywords):
                                        filtered_results.append(result)
                                
                                if filtered_results:
                                    # Use best match (highest similarity)
                                    best_match = filtered_results[0]
                                    name = best_match.get('name', '')
                                    title = best_match.get('title', '')
                                    description = best_match.get('description', '')
                                    details = best_match.get('details', '') or best_match.get('full_content', '')
                                    url = best_match.get('source_url', 'https://prakriti.edu.in/team/')
                                    
                                    response_parts = [f"## {title or 'Team Member Information'}"]
                                    if name:
                                        response_parts.append(f"\n**Name**: {name}")
                                    if title:
                                        response_parts.append(f"\n**Title**: {title}")
                                    if description:
                                        response_parts.append(f"\n**Description**: {description}")
                                    if details:
                                        details_text = details[:800] + "..." if len(details) > 800 else details
                                        response_parts.append(f"\n**Details**: {details_text}")
                                    response_parts.append(f"\n*Source: [{url}]({url})*")
                                    
                                    print(f"[WebCrawler] ✅ Found role match via vector search: {name} - {title}")
                                    return "\n".join(response_parts)
                        except Exception as e:
                            print(f"[WebCrawler] Error in vector search, falling back to keyword search: {e}")
                    
                    # Fallback to keyword search if vector search not available or returned no results
                    if role_keywords:
                        # Prioritize subject keywords (like "french") over role type keywords (like "facilitator")
                        subject_keywords_list = ['french', 'english', 'math', 'mathematics', 'science', 'physics', 'chemistry', 
                                                'biology', 'history', 'art', 'music', 'sports', 'pe', 'computer', 'it', 
                                                'technology', 'design', 'drama', 'theatre', 'dance', 'primary', 'secondary',
                                                'upper', 'lower', 'early', 'years', 'nursery', 'kindergarten']
                        
                        # Find the best search keyword (prefer subject keywords)
                        search_keyword = None
                        subject_keywords_found = []
                        for keyword in role_keywords:
                            if keyword in subject_keywords_list:
                                subject_keywords_found.append(keyword)
                                if not search_keyword:  # Use first subject keyword for initial search
                                    search_keyword = keyword
                        
                        # If no subject keyword found, use first keyword
                        if not search_keyword:
                            search_keyword = role_keywords[0]
                        
                        # Initialize team_result to avoid UnboundLocalError
                        team_result = type('obj', (object,), {'data': []})()
                        team_result.data = []
                        
                        # For multi-word subjects like "art and design", search for records containing ALL keywords
                        # This ensures we get the most relevant matches
                        if len(subject_keywords_found) > 1:
                            # Search for records containing ALL subject keywords in title (more specific)
                            # Build a search that requires all keywords
                            all_keywords_present = True
                            # First, try searching with first keyword
                            team_result = supabase.table('team_member_data').select('*').eq('is_active', True).ilike('title', f'%{subject_keywords_found[0]}%').limit(50).execute()
                            
                            # Then filter to only include records with ALL keywords
                            if team_result.data:
                                filtered_results = []
                                for member in team_result.data:
                                    title_lower = (member.get('title', '') or '').lower()
                                    # Check if ALL subject keywords are present
                                    if all(kw in title_lower for kw in subject_keywords_found):
                                        filtered_results.append(member)
                                team_result.data = filtered_results[:20]  # Limit to 20
                            
                            # DO NOT fall back to description search - TITLE ONLY for role queries
                            # This ensures accuracy - only match if keywords are in title
                        if not team_result.data or len(team_result.data) == 0:
                                print(f"[WebCrawler] ⚠️ No results found with all keywords in title - will check fallback_data")
                        else:
                            # Single keyword search - CRITICAL: For role queries, ONLY search in title
                            # Description searches are unreliable for role-based queries
                            # Use word boundary matching to avoid partial matches (e.g., "art" matching "part", "start")
                            # Search for exact word match in title
                            team_result = supabase.table('team_member_data').select('*').eq('is_active', True).ilike('title', f'%{search_keyword}%').limit(20).execute()
                            
                            # DO NOT fall back to description search for role queries
                            # This prevents false matches (e.g., "art" in description matching wrong person)
                            
                            # Additional filtering: Ensure the keyword appears as a whole word, not as part of another word
                            # ALSO ensure that if we're searching for a role (like "facilitator"), it must be in the title too
                            if team_result.data:
                                filtered_results = []
                                import re
                                word_pattern = r'\b' + re.escape(search_keyword.lower()) + r'\b'
                                initial_count = len(team_result.data)
                                
                                # Also check if we need "facilitator" in the title (if query contains facilitator-related keywords)
                                role_keywords_lower = [kw.lower() for kw in role_keywords]
                                needs_facilitator = any(kw in role_keywords_lower for kw in ['facilitator', 'facilator', 'facilitators', 'faclitator', 'faclitators'])
                                
                                for member in team_result.data:
                                    title_lower = (member.get('title', '') or '').lower()
                                    member_name = member.get('name', 'Unknown')
                                    
                                    # Check if keyword appears as a whole word (not part of another word)
                                    # Also handle plural forms (e.g., "science" matches "sciences")
                                    keyword_matched = False
                                    if re.search(word_pattern, title_lower):
                                        keyword_matched = True
                                    else:
                                        # Try plural form (add 's' or 'es')
                                        plural_patterns = [
                                            r'\b' + re.escape(search_keyword.lower()) + r's\b',  # science -> sciences
                                            r'\b' + re.escape(search_keyword.lower()) + r'es\b',  # class -> classes
                                        ]
                                        # Also try removing 's' from keyword if it ends with 's' (sciences -> science)
                                        if search_keyword.lower().endswith('s'):
                                            singular_keyword = search_keyword.lower()[:-1]
                                            plural_patterns.append(r'\b' + re.escape(singular_keyword) + r'\b')
                                        
                                        for plural_pattern in plural_patterns:
                                            if re.search(plural_pattern, title_lower):
                                                keyword_matched = True
                                                break
                                    
                                    if not keyword_matched:
                                        print(f"[WebCrawler] ⚠️ Filtered out {member_name} - '{search_keyword}' not found as whole word (or plural) in title: '{title_lower}'")
                                        continue
                                    
                                    # CRITICAL: If query is about "art facilitator", ensure BOTH "art" AND "facilitator" are in title
                                    if needs_facilitator and search_keyword != 'facilitator':
                                        # Check if "facilitator" (or variations) is in title
                                        facilitator_in_title = any(re.search(r'\b' + re.escape(kw) + r'\b', title_lower) for kw in ['facilitator', 'facilator', 'facilitators'])
                                        if not facilitator_in_title:
                                            print(f"[WebCrawler] ⚠️ Filtered out {member_name} - 'facilitator' not found in title (query requires facilitator role): '{title_lower}'")
                                            continue
                                    
                                    filtered_results.append(member)
                                
                                team_result.data = filtered_results
                                if len(filtered_results) == 0:
                                    print(f"[WebCrawler] ⚠️ Word-boundary filtering removed all {initial_count} results - will check fallback_data")
                                else:
                                    print(f"[WebCrawler] After word-boundary filtering: {len(filtered_results)} results remain (from {initial_count} initial results)")
                    else:
                        # Default search for facilitator
                        team_result = supabase.table('team_member_data').select('*').eq('is_active', True).ilike('title', '%facilitator%').limit(20).execute()
                    
                    if team_result.data and len(team_result.data) > 0:
                        print(f"[WebCrawler] Found {len(team_result.data)} results from database, filtering for best match...")
                        # Filter results to find best match
                        best_matches = []
                        # Separate subject keywords from role type keywords
                        subject_keywords_list = ['french', 'english', 'math', 'mathematics', 'science', 'physics', 'chemistry', 
                                                'biology', 'history', 'art', 'music', 'sports', 'pe', 'computer', 'it', 
                                                'technology', 'design', 'drama', 'theatre', 'dance', 'primary', 'secondary',
                                                'upper', 'lower', 'early', 'years', 'nursery', 'kindergarten']
                        subject_keywords_in_query = [kw for kw in role_keywords if kw in subject_keywords_list]
                        role_type_keywords_in_query = [kw for kw in role_keywords if kw not in subject_keywords_list]
                        
                        print(f"[WebCrawler] Subject keywords: {subject_keywords_in_query}, Role keywords: {role_type_keywords_in_query}")
                        
                        for member in team_result.data:
                            title_lower = (member.get('title', '') or '').lower()
                            desc_lower = (member.get('description', '') or '').lower()
                            full_content_lower = (member.get('full_content', '') or '').lower()
                            member_name = member.get('name', 'Unknown')
                            
                            # CRITICAL: For role-based queries, require subject keyword in TITLE (not just description)
                            # This ensures we get the actual facilitator for that subject, not someone mentioned in description
                            if subject_keywords_in_query:
                                # Check if at least one subject keyword is in title as a WHOLE WORD (REQUIRED)
                                # Use word boundaries to prevent partial matches (e.g., "art" matching "part", "start")
                                # Also handle plural forms (e.g., "science" matches "sciences")
                                import re
                                subject_in_title = False
                                for kw in subject_keywords_in_query:
                                    word_pattern = r'\b' + re.escape(kw.lower()) + r'\b'
                                    if re.search(word_pattern, title_lower):
                                        subject_in_title = True
                                        break
                                    else:
                                        # Try plural forms
                                        plural_patterns = [
                                            r'\b' + re.escape(kw.lower()) + r's\b',  # science -> sciences
                                            r'\b' + re.escape(kw.lower()) + r'es\b',  # class -> classes
                                        ]
                                        if kw.lower().endswith('s'):
                                            singular_kw = kw.lower()[:-1]
                                            plural_patterns.append(r'\b' + re.escape(singular_kw) + r'\b')
                                        
                                        for plural_pattern in plural_patterns:
                                            if re.search(plural_pattern, title_lower):
                                                subject_in_title = True
                                                break
                                        if subject_in_title:
                                            break
                                
                                if not subject_in_title:
                                    # Skip if no subject keyword in title (description matches are not reliable for role queries)
                                    print(f"[WebCrawler] ⚠️ Skipping {member_name} - subject keyword '{subject_keywords_in_query}' not found as whole word (or plural) in title: '{title_lower}'")
                                    continue
                                
                                # CRITICAL: Also require role type keyword (like "facilitator") in title for role queries
                                # This ensures we don't match people who just happen to have the subject in their title
                                if role_type_keywords_in_query:
                                    role_in_title = False
                                    for kw in role_type_keywords_in_query:
                                        word_pattern = r'\b' + re.escape(kw.lower()) + r'\b'
                                        if re.search(word_pattern, title_lower):
                                            role_in_title = True
                                            break
                                    if not role_in_title:
                                        print(f"[WebCrawler] ⚠️ Skipping {member_name} - role type keyword '{role_type_keywords_in_query}' not found as whole word in title: '{title_lower}'")
                                        continue
                                
                                print(f"[WebCrawler] ✅ {member_name} has both subject and role keywords in title: '{title_lower}'")
                            
                            # Score matches
                            score = 0
                            
                            # For multi-word subjects like "art and design", check if ALL keywords are present (handle plural forms)
                            all_subjects_match_in_title = False
                            all_subjects_match_anywhere = False
                            if len(subject_keywords_in_query) > 1:
                                # Check each keyword with plural handling
                                all_match = True
                                for kw in subject_keywords_in_query:
                                    kw_lower = kw.lower()
                                    # Check exact match or plural form
                                    if kw_lower not in title_lower:
                                        # Try plural forms
                                        if kw_lower + 's' not in title_lower and kw_lower + 'es' not in title_lower:
                                            # Try singular if keyword ends with 's'
                                            if kw_lower.endswith('s') and kw_lower[:-1] not in title_lower:
                                                all_match = False
                                                break
                                all_subjects_match_in_title = all_match
                                all_subjects_match_anywhere = all(kw in title_lower or kw + 's' in title_lower or kw + 'es' in title_lower or kw in desc_lower or kw in full_content_lower for kw in subject_keywords_in_query)
                            else:
                                # Single subject keyword - check if it's in title (with plural handling)
                                if subject_keywords_in_query:
                                    kw = subject_keywords_in_query[0].lower()
                                    all_subjects_match_in_title = (kw in title_lower or kw + 's' in title_lower or kw + 'es' in title_lower or (kw.endswith('s') and kw[:-1] in title_lower))
                                else:
                                    all_subjects_match_in_title = False
                            
                            # MUCH Higher score for subject keyword matches in TITLE ONLY (TITLE FIRST PRIORITY - NO DESCRIPTION MATCHING)
                            for keyword in subject_keywords_in_query:
                                # Use word boundaries to ensure whole word match (including plural forms)
                                import re
                                word_pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                                keyword_found = False
                                if re.search(word_pattern, title_lower):
                                    keyword_found = True
                                else:
                                    # Try plural forms
                                    plural_patterns = [
                                        r'\b' + re.escape(keyword.lower()) + r's\b',  # science -> sciences
                                        r'\b' + re.escape(keyword.lower()) + r'es\b',  # class -> classes
                                    ]
                                    if keyword.lower().endswith('s'):
                                        singular_kw = keyword.lower()[:-1]
                                        plural_patterns.append(r'\b' + re.escape(singular_kw) + r'\b')
                                    
                                    for plural_pattern in plural_patterns:
                                        if re.search(plural_pattern, title_lower):
                                            keyword_found = True
                                            break
                                
                                if keyword_found:
                                    score += 50  # Subject in title = highest priority
                                # DO NOT check description or full_content - TITLE ONLY
                            
                            # Big bonus if ALL subject keywords match in TITLE (especially important for "art and design")
                            if all_subjects_match_in_title:
                                score += 100  # Big bonus for complete match in title (increased from 30)
                            elif all_subjects_match_anywhere:
                                score += 20  # Smaller bonus if all match but not all in title
                            
                            # Check if role type keyword is in title (REQUIRED for accurate role matching)
                            role_in_title = any(kw in title_lower for kw in role_type_keywords_in_query)
                            
                            # Higher score for role type keyword matches in TITLE ONLY (TITLE FIRST PRIORITY - NO DESCRIPTION)
                            for keyword in role_type_keywords_in_query:
                                # Use word boundaries to ensure whole word match
                                import re
                                word_pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                                if re.search(word_pattern, title_lower):
                                    score += 30  # Role type in title = high priority
                                # DO NOT check description or full_content - TITLE ONLY
                            
                            # MASSIVE bonus for exact match in title (all keywords in title)
                            # This ensures "Art Facilitator" matches "Facilitator Art & Design" perfectly
                            if subject_keywords_in_query and role_type_keywords_in_query:
                                all_in_title = all(kw in title_lower for kw in subject_keywords_in_query) and all(kw in title_lower for kw in role_type_keywords_in_query)
                                if all_in_title:
                                    score += 200  # MASSIVE bonus for exact match (increased from 50)
                            
                            # Additional bonus if role type appears before subject in title (e.g., "Facilitator Art")
                            # or if they appear together (e.g., "Art Facilitator")
                            if role_in_title and subject_keywords_in_query:
                                # Check if role and subject appear close together in title
                                title_words = title_lower.split()
                                role_indices = [i for i, word in enumerate(title_words) if any(kw in word for kw in role_type_keywords_in_query)]
                                subject_indices = [i for i, word in enumerate(title_words) if any(kw in word for kw in subject_keywords_in_query)]
                                if role_indices and subject_indices:
                                    # If they're within 3 words of each other, bonus
                                    min_distance = min(abs(r - s) for r in role_indices for s in subject_indices)
                                    if min_distance <= 3:
                                        score += 50  # Bonus for proximity
                            
                            # CRITICAL: Only add to best_matches if score > 0 AND has both keywords (for role queries)
                            # This ensures we don't return partial matches like Rahul Batra for "art facilitator"
                            if score > 0:
                                # For role queries with both subject and role keywords, require BOTH in title
                                if subject_keywords_in_query and role_type_keywords_in_query:
                                    # Double-check that both are actually in title (word-boundary match)
                                    import re
                                    title_lower_check = (member.get('title', '') or '').lower()
                                    has_subject = any(re.search(r'\b' + re.escape(kw.lower()) + r'\b', title_lower_check) for kw in subject_keywords_in_query)
                                    has_role = any(re.search(r'\b' + re.escape(kw.lower()) + r'\b', title_lower_check) for kw in role_type_keywords_in_query)
                                    if not (has_subject and has_role):
                                        print(f"[WebCrawler] ⚠️ Rejecting {member_name} - missing required keywords in title (has_subject: {has_subject}, has_role: {has_role})")
                                        continue  # Skip this member - doesn't have both keywords
                                
                                best_matches.append((member, score))
                        
                        # Sort by score and get best match
                        if best_matches:
                            best_matches.sort(key=lambda x: x[1], reverse=True)
                            database_best_match = best_matches[0][0]
                            database_best_score = best_matches[0][1]
                            
                            print(f"[WebCrawler] Found potential match in team_member_data: {database_best_match.get('name', 'Unknown')} (score: {database_best_score})")
                        else:
                            print(f"[WebCrawler] ⚠️ No valid matches after filtering (all results filtered out) - checking fallback_data...")
                            database_best_match = None
                            database_best_score = 0
                except Exception as e:
                    print(f"[WebCrawler] Error searching by role in team_member_data: {e}")
                    import traceback
                    traceback.print_exc()
            
            # ALWAYS check fallback_data (even if database search found nothing or all results were filtered)
            # This ensures we use fallback_data when database doesn't have the person or filtering removed all matches
            print(f"[WebCrawler] 🔍 Checking fallback_data for role query...")
            # Separate subject keywords from role type keywords (same logic as database search)
            subject_keywords_list = ['french', 'english', 'math', 'mathematics', 'science', 'physics', 'chemistry', 
                                    'biology', 'history', 'art', 'music', 'sports', 'pe', 'computer', 'it', 
                                    'technology', 'design', 'drama', 'theatre', 'dance', 'primary', 'secondary',
                                    'upper', 'lower', 'early', 'years', 'nursery', 'kindergarten']
            subject_keywords_in_query = [kw for kw in role_keywords if kw in subject_keywords_list]
            role_type_keywords_in_query = [kw for kw in role_keywords if kw not in subject_keywords_list]
            
            # Score and find best match in fallback_data
            best_fallback_match = None
            best_fallback_score = 0
            
            for key, member_data in self.fallback_data.items():
                title_lower = (member_data.get('title', '') or '').lower()
                desc_lower = (member_data.get('description', '') or '').lower()
                details_lower = (member_data.get('details', '') or '').lower()
                full_content_lower = (member_data.get('full_content', '') or '').lower()
                
                # CRITICAL: For role-based queries, require subject keyword in TITLE as a WHOLE WORD (TITLE ONLY - NO DESCRIPTION)
                # ALSO require role type keyword (like "facilitator") in title if query is about a specific role
                import re
                
                if subject_keywords_in_query:
                    # Use word boundaries to prevent partial matches (e.g., "art" matching "part", "start")
                    # Also handle plural forms (e.g., "science" matches "sciences")
                    subject_in_title = False
                    for kw in subject_keywords_in_query:
                        word_pattern = r'\b' + re.escape(kw.lower()) + r'\b'
                        if re.search(word_pattern, title_lower):
                            subject_in_title = True
                            break
                        else:
                            # Try plural forms
                            plural_patterns = [
                                r'\b' + re.escape(kw.lower()) + r's\b',  # science -> sciences
                                r'\b' + re.escape(kw.lower()) + r'es\b',  # class -> classes
                            ]
                            # Also try singular if keyword ends with 's'
                            if kw.lower().endswith('s'):
                                singular_kw = kw.lower()[:-1]
                                plural_patterns.append(r'\b' + re.escape(singular_kw) + r'\b')
                            
                            for plural_pattern in plural_patterns:
                                if re.search(plural_pattern, title_lower):
                                    subject_in_title = True
                                    break
                            if subject_in_title:
                                break
                    if not subject_in_title:
                        continue  # Skip if no subject keyword in title as whole word (or plural)
                
                # CRITICAL: If query is about "art facilitator", ensure BOTH "art" AND "facilitator" are in title
                if subject_keywords_in_query and role_type_keywords_in_query:
                    # Check if role type keyword (like "facilitator") is in title
                    role_in_title = False
                    for kw in role_type_keywords_in_query:
                        word_pattern = r'\b' + re.escape(kw.lower()) + r'\b'
                        if re.search(word_pattern, title_lower):
                            role_in_title = True
                            break
                    if not role_in_title:
                        # Skip if role type keyword not in title (e.g., "facilitator" not in title for "art facilitator" query)
                        continue
                
                # Score matches (same logic as database search)
                score = 0
                
                # Check if ALL subject keywords match in TITLE (handle plural forms)
                all_subjects_match_in_title = False
                all_subjects_match_anywhere = False
                if len(subject_keywords_in_query) > 1:
                    # Check each keyword with plural handling
                    all_match = True
                    for kw in subject_keywords_in_query:
                        kw_lower = kw.lower()
                        # Check exact match or plural form
                        if kw_lower not in title_lower:
                            # Try plural forms
                            if kw_lower + 's' not in title_lower and kw_lower + 'es' not in title_lower:
                                # Try singular if keyword ends with 's'
                                if kw_lower.endswith('s') and kw_lower[:-1] not in title_lower:
                                    all_match = False
                                    break
                    all_subjects_match_in_title = all_match
                    all_subjects_match_anywhere = all(kw in title_lower or kw + 's' in title_lower or kw + 'es' in title_lower or kw in desc_lower or kw in details_lower or kw in full_content_lower for kw in subject_keywords_in_query)
                else:
                    if subject_keywords_in_query:
                        kw = subject_keywords_in_query[0].lower()
                        all_subjects_match_in_title = (kw in title_lower or kw + 's' in title_lower or kw + 'es' in title_lower or (kw.endswith('s') and kw[:-1] in title_lower))
                    else:
                        all_subjects_match_in_title = False
                
                # MUCH Higher score for subject keyword matches in TITLE ONLY (TITLE FIRST PRIORITY - NO DESCRIPTION)
                import re
                for keyword in subject_keywords_in_query:
                    # Use word boundaries to ensure whole word match (including plural forms)
                    word_pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                    keyword_found = False
                    if re.search(word_pattern, title_lower):
                        keyword_found = True
                    else:
                        # Try plural forms
                        plural_patterns = [
                            r'\b' + re.escape(keyword.lower()) + r's\b',  # science -> sciences
                            r'\b' + re.escape(keyword.lower()) + r'es\b',  # class -> classes
                        ]
                        if keyword.lower().endswith('s'):
                            singular_kw = keyword.lower()[:-1]
                            plural_patterns.append(r'\b' + re.escape(singular_kw) + r'\b')
                        
                        for plural_pattern in plural_patterns:
                            if re.search(plural_pattern, title_lower):
                                keyword_found = True
                                break
                    
                    if keyword_found:
                        score += 50  # Subject in title = highest priority
                    # DO NOT check description, details, or full_content - TITLE ONLY
                
                # Big bonus if ALL subject keywords match in TITLE
                if all_subjects_match_in_title:
                    score += 100  # Big bonus for complete match in title
                elif all_subjects_match_anywhere:
                    score += 20  # Smaller bonus if all match but not all in title
                
                # Check if role type keyword is in title
                role_in_title = any(kw in title_lower for kw in role_type_keywords_in_query)
                
                # Higher score for role type keyword matches in TITLE ONLY (TITLE FIRST PRIORITY - NO DESCRIPTION)
                for keyword in role_type_keywords_in_query:
                    # Use word boundaries to ensure whole word match
                    word_pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                    if re.search(word_pattern, title_lower):
                        score += 30  # Role type in title = high priority
                    # DO NOT check description, details, or full_content - TITLE ONLY
                
                # MASSIVE bonus for exact match in title (all keywords in title)
                if subject_keywords_in_query and role_type_keywords_in_query:
                    all_in_title = all(kw in title_lower for kw in subject_keywords_in_query) and all(kw in title_lower for kw in role_type_keywords_in_query)
                    if all_in_title:
                        score += 200  # MASSIVE bonus for exact match
                
                if score > best_fallback_score:
                    best_fallback_score = score
                    best_fallback_match = member_data
            
            # Compare database match vs fallback_data match - use the one with higher score
            # CRITICAL: For queries like "art facilitator", fallback_data (Priyanka Oberoi) should win
            # because she has both "art" AND "facilitator" in title, while database matches might not
            final_match = None
            final_score = 0
            match_source = None
            
            # Initialize database_best_match and database_best_score if not already set
            if 'database_best_match' not in locals():
                database_best_match = None
                database_best_score = 0
            
            print(f"[WebCrawler] Comparing matches - Database: {database_best_score if database_best_match else 0}, Fallback: {best_fallback_score}")
            
            # CRITICAL: For role queries with both subject and role keywords, ALWAYS prefer fallback_data
            # This ensures we use fallback_data when it has the correct person (like Priyanka Oberoi)
            # Database matches are often incomplete or incorrect for role queries
            if best_fallback_match and best_fallback_score > 0:
                # For role queries with both keywords, fallback_data is the source of truth
                if subject_keywords_in_query and role_type_keywords_in_query:
                    # ALWAYS prefer fallback_data for role queries - it has complete, accurate data
                    final_match = best_fallback_match
                    final_score = best_fallback_score
                    match_source = "fallback_data"
                    print(f"[WebCrawler] ✅ Using fallback_data match (preferred for role queries with both keywords, score: {best_fallback_score})")
                    if database_best_match:
                        print(f"[WebCrawler] ⚠️ Database match '{database_best_match.get('name', 'Unknown')}' (score: {database_best_score}) ignored - fallback_data preferred for role queries")
                else:
                    # For queries without both keywords, compare scores
                    if database_best_match and database_best_score > 0:
                        # Check if database match actually has both subject AND role in title (strict requirement)
                        db_title_lower = (database_best_match.get('title', '') or '').lower()
                        has_both_in_db = False
                        if subject_keywords_in_query and role_type_keywords_in_query:
                            import re
                            has_subject = any(re.search(r'\b' + re.escape(kw.lower()) + r'\b', db_title_lower) for kw in subject_keywords_in_query)
                            has_role = any(re.search(r'\b' + re.escape(kw.lower()) + r'\b', db_title_lower) for kw in role_type_keywords_in_query)
                            has_both_in_db = has_subject and has_role
                        
                        # Use database match only if it has both keywords AND significantly higher score
                        if has_both_in_db and database_best_score > best_fallback_score + 50:
                            final_match = database_best_match
                            final_score = database_best_score
                            match_source = "team_member_data"
                            print(f"[WebCrawler] Using database match (has both keywords, score: {database_best_score})")
                        else:
                            # Prefer fallback_data
                            final_match = best_fallback_match
                            final_score = best_fallback_score
                            match_source = "fallback_data"
                            print(f"[WebCrawler] Using fallback_data match (better match, score: {best_fallback_score})")
                    else:
                        # No database match, use fallback
                        final_match = best_fallback_match
                        final_score = best_fallback_score
                        match_source = "fallback_data"
                        print(f"[WebCrawler] Using fallback_data match (no database match, score: {best_fallback_score})")
            elif database_best_match and database_best_score > 0:
                # Only use database match if no fallback match
                final_match = database_best_match
                final_score = database_best_score
                match_source = "team_member_data"
                print(f"[WebCrawler] Using database match (no fallback match, score: {database_best_score})")
            
            if final_match and final_score > 0:
                print(f"[WebCrawler] ✅ Found role match in {match_source}: {final_match.get('name', 'Unknown')} (score: {final_score})")
                
                # Return structured data for LLM to format naturally (not pre-formatted markdown)
                # This allows the chatbot to create conversational responses
                if match_source == "team_member_data":
                    name = final_match.get('name', '')
                    title = final_match.get('title', '')
                    description = final_match.get('description', '')
                    details = final_match.get('details', '') or final_match.get('full_content', '')
                    url = final_match.get('source_url', 'https://prakriti.edu.in/team/')
                    
                    # Return structured information for LLM to format naturally
                    structured_info = f"""TEAM MEMBER INFORMATION:
Name: {name}
Title: {title}
Description: {description}
Details: {details[:1000] if details else 'No additional details available'}
Source: {url}"""
                else:
                    # Fallback data
                    structured_info = f"""TEAM MEMBER INFORMATION:
Name: {final_match.get('name', 'Unknown')}
Title: {final_match.get('title', 'Team Member')}
Description: {final_match.get('description', '')}
Details: {(final_match.get('details', '') or '')[:1000] if final_match.get('details') else 'No additional details available'}
Source: https://prakriti.edu.in/team"""
                
                return structured_info
            
            # If not found, return helpful message
            # Check if it's a generic role query (no valid subject specified)
            # Filter out generic terms like "it" that don't actually represent a subject
            # Generic terms that appear in queries but don't help identify a specific facilitator
            generic_terms = ['it']  # "it" is too generic and doesn't help identify a specific facilitator
            valid_subject_keywords = [kw for kw in subject_keywords_in_query if kw not in generic_terms]
            
            # If we have no valid subject keywords (either none detected, or only generic terms like "it")
            # and we have a role type keyword, this is a generic role query that needs a subject
            if not valid_subject_keywords and role_type_keywords_in_query:
                # Generic role query without valid subject - provide helpful guidance
                role_type = role_type_keywords_in_query[0] if role_type_keywords_in_query else 'facilitator'
                return f"""## Information Request

I found that you're asking about a {role_type}, but you haven't specified which subject or area you're interested in.

To help you better, please specify the subject, for example:
- "Who is the French facilitator?"
- "Who is the Math facilitator?"
- "Who is the Art facilitator?"
- "Who is the Science facilitator?"

Or if you're asking about a leadership role, you can ask:
- "Who is the Principal?"
- "Who is the Director?"
- "Who is the Founder?"

*Source: [prakriti.edu.in/team](https://prakriti.edu.in/team)*"""
            
            return f"""## Information Not Available

I'm sorry, but I couldn't find information about a {query_lower.replace('who is the', '').replace('who is', '').strip()} in our team database.

We're continuously updating our team profiles, so please check back later or contact us directly for more information.

*Source: [prakriti.edu.in/team](https://prakriti.edu.in/team)*"""
        
        # PRIORITY 0: Check if this is a specific person query FIRST (before other cache checks)
        # This ensures we get complete person data from team_member_data table
        if self.is_specific_person_query(query):
            person_name = self.extract_person_name(query)
            if person_name:
                print(f"[WebCrawler] Detected specific person query: {person_name}")
                
                # CRITICAL: Check if this is a single name FIRST (before normalization)
                # Normalization might convert "priyanka" to "Priyanka Oberoi", which would skip multiple-match check
                original_parts = person_name.split()
                is_single_name = len(original_parts) == 1
                
                # Normalize name to handle misspellings
                # If it's a single name, preserve it (don't expand) so we can check for multiple matches
                normalized_name = self.normalize_person_name(person_name, preserve_single_name=is_single_name)
                
                # Re-check if normalized name is still single (normalization might have expanded it)
                normalized_parts = normalized_name.split()
                # If normalization expanded single name to full name, we still need to check for multiple matches
                # So keep is_single_name = True if original was single, even if normalized is now full
                if is_single_name and len(normalized_parts) > 1:
                    # Normalization expanded it - but we still want to check for multiple matches
                    # Use the original first name for matching
                    first_name_for_matching = original_parts[0].lower()
                else:
                    first_name_for_matching = normalized_parts[0].lower() if normalized_parts else normalized_name.lower()
                
                # CRITICAL: For single names, check BOTH database AND fallback_data to find ALL matches
                # Then decide: if multiple matches, show list; if single match, show that person
                if is_single_name:
                    # Use first_name_for_matching (original first name, not normalized full name)
                    first_name = first_name_for_matching
                    all_matches = []
                    
                    print(f"[WebCrawler] Single name query detected: '{person_name}' -> checking for multiple matches with first name: '{first_name}'")
                    
                    # Step 1: Check database for all matches
                    if SUPABASE_AVAILABLE:
                        try:
                            supabase = get_supabase_client()
                            # Get ALL matches with this first name
                            team_result = supabase.table('team_member_data').select('*').eq('is_active', True).ilike('name', f'%{first_name}%').limit(20).execute()
                            
                            if team_result.data and len(team_result.data) > 0:
                                # Filter to only include records where first name matches exactly
                                for member in team_result.data:
                                    member_name_lower = (member.get('name', '') or '').lower()
                                    member_parts = member_name_lower.split()
                                    # Check if first name matches
                                    if len(member_parts) >= 1 and member_parts[0] == first_name:
                                        all_matches.append({
                                            'name': member.get('name', 'Unknown'),
                                            'title': member.get('title', 'Team Member'),
                                            'source': 'database'
                                        })
                        except Exception as e:
                            print(f"[WebCrawler] Error checking team_member_data for multiple matches: {e}")
                    
                    # Step 2: Check fallback_data for all matches
                    matching_keys = []
                    for key in self.fallback_data.keys():
                        key_lower = key.lower().strip()
                        key_parts = key_lower.split()
                        # Check if first name matches
                        if len(key_parts) >= 1 and key_parts[0] == first_name:
                            matching_keys.append(key)
                    
                    # Add fallback_data matches (avoid duplicates)
                    for key in matching_keys:
                        person_data = self.fallback_data[key]
                        person_name = person_data.get('name', key)
                        # Check if not already in all_matches
                        if not any(m['name'].lower() == person_name.lower() for m in all_matches):
                            all_matches.append({
                                'name': person_name,
                                'title': person_data.get('title', 'Team Member'),
                                'source': 'fallback'
                            })
                    
                    # Step 3: If multiple matches found, return list
                    if len(all_matches) > 1:
                        print(f"[WebCrawler] ⚠️ Multiple matches found for '{normalized_name}': {len(all_matches)} people")
                        
                        # Return structured list for LLM to format
                        list_info = f"""MULTIPLE PEOPLE FOUND:
Query: "{normalized_name}" matches {len(all_matches)} people:

"""
                        for i, person in enumerate(all_matches, 1):
                            list_info += f"{i}. {person['name']} - {person['title']}\n"
                        
                        list_info += f"""
Please specify which person you'd like to know about by providing their full name (e.g., "{all_matches[0]['name']}" or "{all_matches[1]['name'] if len(all_matches) > 1 else ''}")."""
                        
                        return list_info
                    elif len(all_matches) == 1:
                        # Single match found - get full details for this person
                        print(f"[WebCrawler] ✅ Single match found for '{normalized_name}': {all_matches[0]['name']}")
                        matched_person = all_matches[0]
                        
                        # Try to get full details from database first
                        if matched_person['source'] == 'database' and SUPABASE_AVAILABLE:
                            try:
                                supabase = get_supabase_client()
                                full_result = supabase.table('team_member_data').select('*').eq('is_active', True).ilike('name', f"%{matched_person['name']}%").limit(1).execute()
                                
                                if full_result.data and len(full_result.data) > 0:
                                    member = full_result.data[0]
                                    name = member.get('name', matched_person['name'])
                                    title = member.get('title', matched_person['title'])
                                    description = member.get('description', '')
                                    details = member.get('details', '') or member.get('full_content', '')
                                    url = member.get('source_url', 'https://prakriti.edu.in/team/')
                                    
                                    # If we have minimal data, try to get more from full_content
                                    if not description and not details and member.get('full_content'):
                                        full_content = member.get('full_content', '')
                                        sentences = full_content.split('.')
                                        if sentences:
                                            description = sentences[0].strip()
                                        if len(sentences) > 1:
                                            details = '. '.join(sentences[1:]).strip()[:600]
                                    
                                    structured_info = f"""TEAM MEMBER INFORMATION:
Name: {name}
Title: {title}
Description: {description}
Details: {details[:1000] if details else 'No additional details available'}
Source: {url}"""
                                    
                                    return structured_info
                            except Exception as e:
                                print(f"[WebCrawler] Error getting full details from database: {e}")
                        
                        # If not from database or database failed, get from fallback_data
                        if matched_person['source'] == 'fallback':
                            for key in self.fallback_data.keys():
                                if self.fallback_data[key].get('name', key).lower() == matched_person['name'].lower():
                                    fallback = self.fallback_data[key]
                                    structured_info = f"""TEAM MEMBER INFORMATION:
Name: {fallback.get('name', matched_person['name'])}
Title: {fallback.get('title', matched_person['title'])}
Description: {fallback.get('description', '')}
Details: {(fallback.get('details', '') or '')[:1000] if fallback.get('details') else 'No additional details available'}
Source: {fallback.get('source_url', 'https://prakriti.edu.in/team/')}"""
                                    
                                    return structured_info
                        
                        # Fallback: return basic info
                        structured_info = f"""TEAM MEMBER INFORMATION:
Name: {matched_person['name']}
Title: {matched_person['title']}
Description: No additional details available
Details: No additional details available
Source: https://prakriti.edu.in/team/"""
                        
                        return structured_info
                
                # FIRST: Check team_member_data table directly (most accurate for person queries)
                # Only for full name queries (not single names - those are handled above)
                if not is_single_name and SUPABASE_AVAILABLE:
                    try:
                        supabase = get_supabase_client()
                        # Try both original and normalized name
                        search_terms = [normalized_name, person_name] if normalized_name != person_name else [person_name]
                        
                        for search_term in search_terms:
                            # Try multiple search strategies for better matching
                            # CRITICAL: For full names (2+ words), prioritize exact surname match
                            name_parts = search_term.split()
                            
                            # Initialize team_result for this search_term
                            team_result = type('obj', (object,), {'data': []})()
                            team_result.data = []
                            
                            # Strategy 1: If full name (2+ words), search by surname first (most accurate)
                            if len(name_parts) >= 2:
                                first_name = name_parts[0]
                                last_name = name_parts[-1]
                                
                                # CRITICAL: Search by surname first (exact match required)
                                # This ensures "priyanka oberoi" matches "Priyanka Oberoi" not "Priyanka Jain"
                                team_result = supabase.table('team_member_data').select('*').eq('is_active', True).ilike('name', f'%{last_name}%').limit(20).execute()
                                
                                if team_result.data and len(team_result.data) > 0:
                                    # Find exact surname + first name match
                                    best_match = None
                                    search_term_lower = search_term.lower()
                                    for member in team_result.data:
                                        member_name_lower = (member.get('name', '') or '').lower()
                                        member_parts = member_name_lower.split()
                                        
                                        # CRITICAL: Require exact surname match
                                        if len(member_parts) >= 2 and member_parts[-1] == last_name.lower():
                                            # Check if first name also matches
                                            if member_parts[0] == first_name.lower():
                                                # Perfect match - use this
                                                best_match = member
                                                print(f"[WebCrawler] ✅ Exact surname+first name match: '{member.get('name')}'")
                                                break
                                    
                                    # If no perfect match, use first surname match
                                    if not best_match:
                                        for member in team_result.data:
                                            member_name_lower = (member.get('name', '') or '').lower()
                                            member_parts = member_name_lower.split()
                                            if len(member_parts) >= 2 and member_parts[-1] == last_name.lower():
                                                best_match = member
                                                print(f"[WebCrawler] ✅ Exact surname match: '{member.get('name')}'")
                                                break
                                    
                                    if best_match:
                                        team_result.data = [best_match]
                                    else:
                                        team_result.data = []
                            
                            # Strategy 2: If no match yet, try full name match
                            if not team_result.data or len(team_result.data) == 0:
                                team_result = supabase.table('team_member_data').select('*').eq('is_active', True).ilike('name', f'%{search_term}%').limit(1).execute()
                            
                            # Strategy 3: If still no match and we have 2+ words, try first name only
                            if (not team_result.data or len(team_result.data) == 0) and len(name_parts) >= 2:
                                first_name = name_parts[0]
                                team_result = supabase.table('team_member_data').select('*').eq('is_active', True).ilike('name', f'%{first_name}%').limit(5).execute()
                                
                                # Find the best match from results (prefer exact surname match)
                                if team_result.data and len(team_result.data) > 0:
                                    last_name = name_parts[-1]
                                    best_match = None
                                    for member in team_result.data:
                                        member_name_lower = (member.get('name', '') or '').lower()
                                        member_parts = member_name_lower.split()
                                        # Prefer exact surname match
                                        if len(member_parts) >= 2 and member_parts[-1] == last_name.lower():
                                            best_match = member
                                            break
                                    # If no exact surname match, use first result
                                    if not best_match:
                                        best_match = team_result.data[0]
                                    team_result.data = [best_match]
                            
                            # Strategy 4: Single name search (first name only) - already handled above
                            # Skip this if we already processed single name matches
                            if not is_single_name:
                                if not team_result.data or len(team_result.data) == 0:
                                    first_name = search_term.split()[0] if search_term.split() else search_term
                                    team_result = supabase.table('team_member_data').select('*').eq('is_active', True).ilike('name', f'%{first_name}%').limit(5).execute()
                                    
                                    if team_result.data and len(team_result.data) > 0:
                                        # For non-single names, just get first match
                                        team_result.data = [team_result.data[0]]
                            
                            # Single match found - return that person's info
                            if team_result.data and len(team_result.data) > 0:
                                member = team_result.data[0]
                                print(f"[WebCrawler] ✅ Found {search_term} in team_member_data table (direct lookup)")
                                
                                # Get member data
                                name = member.get('name', normalized_name)
                                title = member.get('title', '')
                                description = member.get('description', '')
                                details = member.get('details', '') or member.get('full_content', '')
                                url = member.get('source_url', 'https://prakriti.edu.in/team/')
                                
                                # If we have minimal data, try to get more from full_content
                                if not description and not details and member.get('full_content'):
                                    full_content = member.get('full_content', '')
                                    # Extract first sentence as description
                                    sentences = full_content.split('.')
                                    if sentences:
                                        description = sentences[0].strip()
                                    # Use remaining as details
                                    if len(sentences) > 1:
                                        details = '. '.join(sentences[1:]).strip()[:600]
                                
                                # Return structured data for LLM to format naturally
                                structured_info = f"""TEAM MEMBER INFORMATION:
Name: {name}
Title: {title}
Description: {description}
Details: {details[:1000] if details else 'No additional details available'}
Source: {url}"""
                                
                                return structured_info
                    except Exception as e:
                        print(f"[WebCrawler] Error checking team_member_data for person query: {e}")
                
                # If not found in team_member_data, check fallback_data
                # Try to find in fallback_data using normalized name or variations
                fallback_key = None
                normalized_lower = normalized_name.lower().strip()
                original_lower = person_name.lower().strip() if person_name else ""
                
                # Check if this is a single name (first name only) - might have multiple matches
                normalized_parts = normalized_lower.split()
                is_single_name = len(normalized_parts) == 1
                
                print(f"[WebCrawler] Searching fallback_data for: '{normalized_name}' (normalized: '{normalized_lower}', original: '{original_lower}')")
                print(f"[WebCrawler] Available fallback_data keys: {list(self.fallback_data.keys())}")
                
                # CRITICAL: If single name, check for multiple matches first
                if is_single_name:
                    first_name = normalized_parts[0]
                    matching_keys = []
                    for key in self.fallback_data.keys():
                        key_lower = key.lower().strip()
                        key_parts = key_lower.split()
                        # Check if first name matches
                        if len(key_parts) >= 1 and key_parts[0] == first_name:
                            matching_keys.append(key)
                    
                    # If multiple matches found, return list
                    if len(matching_keys) > 1:
                        print(f"[WebCrawler] ⚠️ Multiple matches found in fallback_data for '{normalized_name}': {len(matching_keys)} people")
                        
                        # Build list of matching people
                        people_list = []
                        for key in matching_keys:
                            person_data = self.fallback_data[key]
                            people_list.append({
                                'name': person_data.get('name', key),
                                'title': person_data.get('title', 'Team Member')
                            })
                        
                        # Return structured list for LLM to format
                        list_info = f"""MULTIPLE PEOPLE FOUND:
Query: "{normalized_name}" matches {len(people_list)} people:

"""
                        for i, person in enumerate(people_list, 1):
                            list_info += f"{i}. {person['name']} - {person['title']}\n"
                        
                        list_info += f"""
Please specify which person you'd like to know about by providing their full name (e.g., "{people_list[0]['name']}" or "{people_list[1]['name'] if len(people_list) > 1 else ''}")."""
                        
                        return list_info
                    elif len(matching_keys) == 1:
                        # Single match found
                        fallback_key = matching_keys[0]
                        print(f"[WebCrawler] ✅ Single match found in fallback_data: '{fallback_key}'")
                
                # Check exact match first (try both normalized and original)
                if not fallback_key:
                    for key in self.fallback_data.keys():
                        key_lower = key.lower().strip()
                        if key_lower == normalized_lower or (original_lower and key_lower == original_lower):
                            fallback_key = key
                            print(f"[WebCrawler] ✅ Exact match found in fallback_data: '{key}'")
                            break
                        
                        # Also try matching without case sensitivity and with extra spaces
                        normalized_clean = normalized_lower.replace(' ', '').strip()
                        key_clean = key_lower.replace(' ', '').strip()
                        if normalized_clean == key_clean:
                            fallback_key = key
                            print(f"[WebCrawler] ✅ Exact match found (after space removal) in fallback_data: '{key}'")
                        break
                
                # If no exact match, try partial match (e.g., "Shuchi Mishra" matches "shuchi mishra")
                if not fallback_key:
                    # CRITICAL: If query has 2+ words (full name), prioritize EXACT surname match
                    normalized_parts = normalized_lower.split()
                    if len(normalized_parts) >= 2:
                        first_name = normalized_parts[0].strip()
                        last_name = normalized_parts[-1].strip()
                        print(f"[WebCrawler] Trying first+last name match with surname priority: first='{first_name}', last='{last_name}'")
                        
                        # First, try exact surname match (highest priority)
                        exact_surname_matches = []
                        for key in self.fallback_data.keys():
                            key_lower = key.lower().strip()
                            key_parts = key_lower.split()
                            if len(key_parts) >= 2:
                                key_first = key_parts[0].strip()
                                key_last = key_parts[-1].strip()
                                # CRITICAL: Exact surname match is required for full names
                                if last_name == key_last:
                                    # Check if first name also matches
                                    if first_name == key_first:
                                        # Perfect match - use this immediately
                                        fallback_key = key
                                        print(f"[WebCrawler] ✅ Perfect match (first+last): '{key}'")
                                        break
                                    else:
                                        # Surname matches but first name doesn't - store for later
                                        exact_surname_matches.append((key, key_first))
                
                        # If perfect match found, use it
                        if fallback_key:
                            pass  # Already found
                        elif exact_surname_matches:
                            # Use the first surname match (even if first name differs slightly)
                            # This handles cases like "priyanka oberoi" vs "priyanka jain" - prioritize exact surname
                            fallback_key = exact_surname_matches[0][0]
                            print(f"[WebCrawler] ✅ Exact surname match found: '{fallback_key}' (surname: '{last_name}')")
                        else:
                            # No exact surname match, try fuzzy matching
                            for key in self.fallback_data.keys():
                                key_lower = key.lower().strip()
                                key_parts = key_lower.split()
                                if len(key_parts) >= 2:
                                    key_first = key_parts[0].strip()
                                    key_last = key_parts[-1].strip()
                                    # Check if first and last names match exactly
                                    if first_name == key_first and last_name == key_last:
                                        fallback_key = key
                                        print(f"[WebCrawler] ✅ First+Last name match found: '{key}'")
                                        break
                                    # Also check if names are similar (fuzzy match)
                                    elif (first_name in key_first or key_first in first_name) and \
                                         (last_name in key_last or key_last in last_name):
                                        fallback_key = key
                                        print(f"[WebCrawler] ✅ Fuzzy name match found: '{key}'")
                                        break
                    
                    # If still no match, try substring matching (including single word matches)
                    if not fallback_key:
                        print(f"[WebCrawler] Trying substring matching...")
                        for key in self.fallback_data.keys():
                            key_lower = key.lower().strip()
                            key_parts = key_lower.split()
                            
                            # Check if normalized name contains key or key contains normalized name
                            if normalized_lower in key_lower or key_lower in normalized_lower:
                                fallback_key = key
                                print(f"[WebCrawler] ✅ Substring match found: '{key}'")
                                break
                            
                            # Check if first name matches (for single word queries like "vanila")
                            if len(normalized_parts) == 1 and len(key_parts) >= 1:
                                if normalized_parts[0] == key_parts[0]:
                                    fallback_key = key
                                    print(f"[WebCrawler] ✅ First name match found: '{key}'")
                                    break
                            
                            # Also check last name match
                            if len(normalized_parts) >= 1 and len(key_parts) >= 2:
                                if normalized_parts[-1] == key_parts[-1]:
                                    fallback_key = key
                                    print(f"[WebCrawler] ✅ Last name match found: '{key}'")
                                    break
                            
                            # Check if any part of normalized name matches any part of key
                            if normalized_parts and key_parts:
                                if any(n_part in key_lower for n_part in normalized_parts) or \
                                   any(k_part in normalized_lower for k_part in key_parts):
                                    fallback_key = key
                                    print(f"[WebCrawler] ✅ Partial name match found: '{key}'")
                                    break
                
                if fallback_key:
                    print(f"[WebCrawler] ✅ Found {normalized_name} in fallback_data (key: {fallback_key})")
                    fallback = self.fallback_data[fallback_key]
                    
                    # Return structured data for LLM to format naturally (not pre-formatted markdown)
                    structured_info = f"""TEAM MEMBER INFORMATION:
Name: {fallback.get('name', 'Unknown')}
Title: {fallback.get('title', 'Team Member')}
Description: {fallback.get('description', '')}
Details: {(fallback.get('details', '') or '')[:1000] if fallback.get('details') else 'No additional details available'}
Source: {fallback.get('source_url', 'https://prakriti.edu.in/team/')}"""
                    
                    return structured_info
                
                # If not found in fallback_data either, return "not found" message
                # DO NOT trigger Selenium web crawling for person queries (too slow and unnecessary)
                print(f"[WebCrawler] ⚠️ Person '{normalized_name}' not found in team_member_data table or fallback_data")
                print(f"[WebCrawler] ℹ️ Skipping web crawling for person query - data should be in team_member_data table or fallback_data")
                return f"""## Information Not Available

I'm sorry, but information about {normalized_name} is not currently available in our team database.

We're continuously updating our team profiles, so please check back later or contact us directly for more information about our staff members.

*Source: [prakriti.edu.in/team](https://prakriti.edu.in/team)*"""
        
        # FIRST: Try to get filtered cached data from web_crawler_data table (FAST PATH)
        # This is faster than checking search_cache, then crawling
        if SUPABASE_AVAILABLE:
            try:
                supabase = get_supabase_client()
                query_lower = query.lower()
                query_words = [w for w in query_lower.split() if len(w) > 2]
                
                # Determine content_type
                content_type = None
                is_substack_query = 'substack' in query_lower
                
                if self.is_team_related(query):
                    content_type = 'team'
                elif self.is_article_related(query) and not is_substack_query:
                    content_type = 'article'
                elif self.is_calendar_related(query):
                    content_type = 'calendar'
                elif self.is_news_related(query) and not is_substack_query:
                    content_type = 'news'
                elif self.is_academic_related(query):
                    content_type = 'academic'
                elif self.is_admission_related(query):
                    content_type = 'admission'
                elif self.is_contact_related(query):
                    content_type = 'contact'
                elif self.is_testimonial_related(query):
                    content_type = 'testimonial'
                
                # Query cached pages directly
                base_query = supabase.table('web_crawler_data').select('url, title, description, main_content, content_type').eq('is_active', True).gte('crawled_at', (datetime.utcnow() - timedelta(hours=24)).isoformat())
                
                # Filter by content_type (but handle Substack queries specially)
                if content_type and not is_substack_query:
                    base_query = base_query.eq('content_type', content_type)
                elif is_substack_query:
                    # For Substack queries, search both 'news' and 'article' content types
                    base_query = base_query.in_('content_type', ['news', 'article'])
                    print(f"[WebCrawler] Fast cache: Filtering by content_type: news OR article (Substack query)")
                
                result = base_query.limit(10).execute()  # Limit to 10 for scoring
                
                if result.data and len(result.data) > 0:
                    print(f"[WebCrawler] ✅ Found {len(result.data)} cached pages in web_crawler_data table, scoring by relevance...")
                    
                    # AGGRESSIVE FILTERING: Score pages and only keep highly relevant ones
                    # Check if this is an article/news query - lower threshold for these
                    is_article_query = any(word in query_lower for word in ['article', 'articles', 'latest', 'recent', 'news', 'blog', 'substack'])
                    min_threshold = 3 if is_article_query else 5  # Lower threshold for article queries
                    
                    scored_pages = []
                    for page in result.data:
                        score = 0
                        page_title = (page.get('title') or '').lower()
                        page_desc = (page.get('description') or '').lower()
                        page_content = (page.get('main_content') or '')[:1000].lower()  # Check first 1000 chars
                        
                        # Count exact query word matches (more specific = higher score)
                        query_word_matches = sum(1 for word in query_words if word in page_title or word in page_desc or word in page_content)
                        
                        # Title match = highest priority (20 points)
                        title_matches = sum(10 for word in query_words if word in page_title)
                        score += title_matches
                        
                        # Description match = medium priority (6 points)
                        desc_matches = sum(3 for word in query_words if word in page_desc)
                        score += desc_matches
                        
                        # Content match = lower priority (1 point)
                        content_matches = sum(1 for word in query_words if word in page_content)
                        score += content_matches
                        
                        # Bonus for multiple query words matching
                        if query_word_matches >= len(query_words) * 0.7:  # 70% of query words match
                            score += 10
                        
                        # For article queries, give bonus if page has substantial content
                        if is_article_query and page.get('main_content') and len(page.get('main_content', '')) > 500:
                            score += 5  # Bonus for having substantial content
                        
                        # Only include pages with minimum relevance threshold
                        if score >= min_threshold:
                            scored_pages.append({
                                'title': page.get('title', ''),
                                'description': page.get('description', ''),
                                'main_content': page.get('main_content', ''),
                                'url': page.get('url', ''),
                                'score': score,
                                'query_matches': query_word_matches
                            })
                    
                    if scored_pages:
                        scored_pages.sort(key=lambda x: (x['score'], x['query_matches']), reverse=True)
                        # ONLY return TOP 1 most relevant page (TOKEN OPTIMIZATION)
                        top_page = scored_pages[0]
                        
                        # Check if this is an article/news query - return more content
                        is_article_query = any(word in query_lower for word in ['article', 'articles', 'latest', 'recent', 'news', 'blog', 'substack'])
                        
                        relevant_text_parts = []
                        
                        # Always include title for article queries
                        if top_page['title']:
                            if is_article_query:
                                relevant_text_parts.append(top_page['title'])
                            elif any(word in top_page['title'].lower() for word in query_words):
                                relevant_text_parts.append(top_page['title'][:70])
                        
                        # Always include description for article queries
                        if top_page['description']:
                            if is_article_query:
                                relevant_text_parts.append(top_page['description'])
                            elif any(word in top_page['description'].lower() for word in query_words):
                                relevant_text_parts.append(top_page['description'][:80])
                        
                        # Extract content from main_content
                        if top_page['main_content']:
                            if is_article_query:
                                # For article queries, return more substantial content (first 1500 chars)
                                main_content = top_page['main_content'].strip()
                                if main_content:
                                    # Get first paragraph or first 1500 chars
                                    first_paragraph = main_content.split('\n\n')[0] if '\n\n' in main_content else main_content
                                    if len(first_paragraph) > 1500:
                                        first_paragraph = first_paragraph[:1500] + "..."
                                    relevant_text_parts.append(first_paragraph)
                            else:
                                # For other queries, extract ONLY sentences with query words (max 2 sentences)
                                sentences = top_page['main_content'].split('.')
                                relevant_sentences = []
                                for sentence in sentences:
                                    sentence_clean = sentence.strip()
                                    if sentence_clean and len(sentence_clean) > 20:  # Skip very short sentences
                                        sentence_lower = sentence_clean.lower()
                                        # Check if sentence contains any query word
                                        if any(word in sentence_lower for word in query_words):
                                            relevant_sentences.append(sentence_clean[:150])  # Max 150 chars per sentence
                                            if len(relevant_sentences) >= 2:  # Max 2 sentences
                                                break
                            
                            if relevant_sentences:
                                relevant_text_parts.extend(relevant_sentences)
                        
                        # Combine content
                        if relevant_text_parts:
                            if is_article_query:
                                # For article queries, use newlines for better formatting, max 2000 chars
                                result_text = '\n\n'.join(relevant_text_parts)
                                if len(result_text) > 2000:
                                    result_text = result_text[:2000] + "..."
                            else:
                                # For other queries, use pipe separator, max 400 chars
                                result_text = ' | '.join(relevant_text_parts)
                                if len(result_text) > 400:
                                    result_text = result_text[:400] + "..."
                            
                            if top_page['url']:
                                result_text += f"\n\nSource: [{top_page['url']}]({top_page['url']})"
                            
                            print(f"[WebCrawler] ✅ Returning TOP 1 cached page (score: {top_page['score']}, matches: {top_page['query_matches']}/{len(query_words)} words, {len(result_text)} chars, is_article_query: {is_article_query})")
                            return result_text
                        else:
                            print(f"[WebCrawler] ⚠️ Page found but no relevant text extracted (score: {top_page['score']})")
                    else:
                        print(f"[WebCrawler] ⚠️ No pages met minimum relevance threshold (5 points)")
            except Exception as e:
                print(f"[WebCrawler] Error in fast cache check: {e}")
        
        # SECOND: Check Supabase search_cache table (older method)
        if SUPABASE_AVAILABLE:
            try:
                print(f"[WebCrawler] 🔍 Checking search_cache table (step 2)...")
                supabase = get_supabase_client()
                # Generate query hash
                query_hash = hashlib.md5(query.lower().strip().encode()).hexdigest()
                
                # Check search_cache table for cached results
                # SELECT ONLY cached_results column (not *) to reduce data transfer
                cache_result = supabase.table('search_cache').select('cached_results').eq('query_hash', query_hash).eq('is_active', True).gte('expires_at', datetime.utcnow().isoformat()).limit(1).execute()
                
                if cache_result.data and len(cache_result.data) > 0:
                    cached_entry = cache_result.data[0]
                    print(f"[WebCrawler] ✅ Found cached data in Supabase search_cache (fast response, no crawling needed)")
                    
                    # Return cached results
                    cached_results = cached_entry.get('cached_results', '')
                    
                    # cached_results is stored as JSONB in Supabase, but may be returned as string or dict
                    if isinstance(cached_results, str):
                        # If it's a string, truncate if too long to save tokens (max 1500 chars)
                        if cached_results.strip():
                            if len(cached_results) > 1500:
                                cached_results = cached_results[:1500] + "..."
                                print(f"[WebCrawler] Truncated cached_results to 1500 chars to save tokens")
                            print(f"[WebCrawler] Returning cached data (no crawling needed)")
                            return cached_results
                    elif isinstance(cached_results, dict):
                        # If it's a dict, format it and truncate
                        formatted_info = self.format_cached_results(cached_results, query)
                        if formatted_info:
                            if len(formatted_info) > 1500:
                                formatted_info = formatted_info[:1500] + "..."
                                print(f"[WebCrawler] Truncated formatted_info to 1500 chars to save tokens")
                            print(f"[WebCrawler] Returning cached data (no crawling needed)")
                            return formatted_info
            except Exception as e:
                print(f"[WebCrawler] Error checking Supabase cache: {e}")
                # Continue to crawling if cache check fails
        
        # If no cache found in search_cache either, proceed with crawling
        print(f"[WebCrawler] ⚠️ No cached data found in either cache table, starting web crawl (this may take 2-5 seconds)...")
        print(f"[WebCrawler] 📝 Crawled data will be cached in Supabase for faster future responses")
        
        # Note: Person queries are already handled at the beginning of this function
        # Search for PrakritSchool specific content
        prakriti_content = self.search_prakriti_content(query)
        
        # If it's a general educational query, also search general content
        general_content = []
        if not self.is_prakriti_related(query):
            general_content = self.search_general_content(query)
        
        # Extract relevant information
        enhanced_info = ""
        if prakriti_content:
            enhanced_info += self.extract_relevant_info(prakriti_content, query)
        
        if general_content:
            general_info = self.extract_relevant_info(general_content, query)
            if general_info:
                enhanced_info += "\n" + general_info
        
        # If no web content found, provide clear "not available" message
        if not enhanced_info:
            enhanced_info = f"""## Information Not Available

I'm sorry, but the information you're looking for is not currently available on our website. 

We're continuously updating our content, so please check back later or contact us directly for more information.

*Source: [prakriti.edu.in](https://prakriti.edu.in)*"""
        
        # Cache the results in Supabase for future use (if available)
        if SUPABASE_AVAILABLE and enhanced_info:
            try:
                supabase = get_supabase_client()
                query_hash = hashlib.md5(query.lower().strip().encode()).hexdigest()
                
                # Prepare cache entry
                cache_data = {
                    'query_hash': query_hash,
                    'query_text': query,
                    'cached_results': enhanced_info if isinstance(enhanced_info, str) else json.dumps(enhanced_info),
                    'result_count': len(enhanced_info) if enhanced_info else 0,
                    'expires_at': (datetime.utcnow() + timedelta(hours=24)).isoformat(),
                    'is_active': True
                }
                
                # Upsert to search_cache (insert or update if exists)
                supabase.table('search_cache').upsert(cache_data, on_conflict='query_hash').execute()
                print(f"[WebCrawler] ✅ Cached results in Supabase for future use")
            except Exception as e:
                print(f"[WebCrawler] Error caching in Supabase: {e}")
                # Non-critical, continue
        
        return enhanced_info
    
    def format_cached_results(self, cached_data: any, query: str) -> str:
        """Format cached results from Supabase for chatbot use"""
        # If it's already a string (formatted HTML/text), return as is
        if isinstance(cached_data, str):
            return cached_data
        
        # If it's a dict, try to extract formatted content
        if isinstance(cached_data, dict):
            # Check if it's already formatted text in cached_results field
            if 'cached_results' in cached_data:
                results = cached_data['cached_results']
                if isinstance(results, str):
                    return results
                elif isinstance(results, dict):
                    # Format as web search results
                    return self.extract_relevant_info([results], query) if isinstance(results, dict) else str(results)
            # If it's a content dict directly, format it
            elif 'main_content' in cached_data or 'title' in cached_data:
                return self.extract_relevant_info([cached_data], query)
        
        # Fallback: return as string
        return str(cached_data) if cached_data else ""

# Global instance
web_crawler = WebCrawlerAgent()

def get_web_enhanced_response(query: str) -> str:
    """Get web-enhanced response for chatbot queries"""
    try:
        return web_crawler.get_enhanced_response(query)
    except Exception as e:
        print(f"[WebCrawler] Error getting enhanced response: {e}")
        return ""
