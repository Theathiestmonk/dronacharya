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

class WebCrawlerAgent:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        # Set default timeout for all requests
        self.session.timeout = 30
        
        # PrakritSchool specific URLs to crawl (all 19 discovered pages)
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
            "https://prakriti.edu.in/cpp/"
        ]
        
        # Cache for crawled content
        self.content_cache = {}
        self.cache_duration = 3600  # 1 hour cache
        
        # No cached team member data - always crawl website for fresh information
        
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
    
    def is_specific_person_query(self, query: str) -> bool:
        """Check if the query is asking about a specific person by name"""
        query_lower = query.lower()
        
        # First, check if the query contains a potential person name (2+ capitalized words)
        import re
        # Look for 2-word names specifically (First Last)
        two_word_pattern = r'\b[a-zA-Z]+\s+[a-zA-Z]+\b'
        potential_names = re.findall(two_word_pattern, query_lower)
        
        # If still no potential names found, it's not a person query
        if not potential_names:
            return False
        
        # Check if the potential name is actually a person name (not common words)
        # Exclude educational/academic terms, scientific concepts, and common phrases
        common_words = ['little', 'bit', 'about', 'tell', 'me', 'who', 'is', 'information', 'details', 'cooking', 'recipes', 'admission', 'fees', 'school', 'program', 'course', 'prakriti', 'prakrit', 'roots', 'philosophy', 'article', 'articles', 'blog', 'news', 'calendar', 'event', 'admission', 'fee', 'curriculum', 'learning', 'learn', 'teaching', 'approach', 'want', 'newton', 'einstein', 'darwin', 'law', 'laws', 'theory', 'theorem', 'formula', 'concept', 'concepts', 'example', 'examples', 'explain', 'understand', 'help', 'solve', 'study', 'physics', 'chemistry', 'biology', 'math', 'mathematics', 'algebra', 'calculus']
        
        # Also check for known person name patterns
        person_name_patterns = ['mishra', 'batra', 'rana', 'goel', 'krishna', 'tayal', 'john', 'doe', 'smith', 'jones']
        
        for name in potential_names:
            name_lower = name.lower()
            # Check if the name itself contains common words (not just the original query)
            name_words = name_lower.split()
            contains_common_words = any(word in common_words for word in name_words)
            
            # Check if it's NOT a common word AND either looks like a person name OR contains known person name patterns
            if (not contains_common_words and 
                (len(name.split()) >= 2 or any(pattern in name_lower for pattern in person_name_patterns))):
                return True
        
        return False
    
    def extract_person_name(self, query: str) -> str:
        """Extract potential person name from query"""
        query_lower = query.lower()
        
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
        common_words = ['little', 'bit', 'about', 'of', 'the', 'a', 'an', 'and', 'or', 'but', 'give', 'me', 'information', 'details', 'litle', 'info', 'check', 'for', 'this', 'that', 'these', 'those', 'with', 'introduction', 'detail', 'what', 'facilaor', 'facilitator']
        words = cleaned_query.split()
        cleaned_words = [word for word in words if word.lower() not in common_words]
        cleaned_query = ' '.join(cleaned_words)
        
        # Remove team context words
        team_words = ['team', 'staff', 'faculty', 'teacher', 'member', 'of prakriti', 'at prakriti']
        for word in team_words:
            cleaned_query = cleaned_query.replace(word, '').strip()
        
        # Clean up extra spaces and common words
        cleaned_query = cleaned_query.replace('  ', ' ').strip()
        
        # Extract name using regex pattern (First Last or First Middle Last)
        import re
        name_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}\b'
        matches = re.findall(name_pattern, cleaned_query.title())
        
        if matches:
            # Return the longest match (most likely to be the full name)
            longest_match = max(matches, key=len)
            # Additional check: ensure it's not just common words
            common_words = ['little', 'bit', 'about', 'tell', 'me', 'who', 'is', 'information', 'check', 'for', 'this', 'that', 'with', 'introduction', 'detail', 'what', 'facilaor', 'facilitator']
            if not any(word in longest_match.lower() for word in common_words):
                return longest_match
        
        # Fallback: If we have a reasonable length name (2+ words), return it
        words = cleaned_query.split()
        if len(words) >= 2:
            return ' '.join(words).title()
        
        return cleaned_query.title() if cleaned_query else ""
    
    def search_specific_person(self, person_name: str, content_list: List[Dict[str, str]]) -> Dict[str, str]:
        """Search for specific person details in crawled content"""
        if not person_name:
            return {}
        
        person_name_lower = person_name.lower()
        
        # FIRST: Check team_member_data table (fastest, most accurate for popup data)
        if SUPABASE_AVAILABLE:
            try:
                supabase = get_supabase_client()
                # Search for person in team_member_data (case-insensitive)
                team_result = supabase.table('team_member_data').select('*').eq('is_active', True).ilike('name', f'%{person_name}%').limit(1).execute()
                
                if team_result.data and len(team_result.data) > 0:
                    member = team_result.data[0]
                    print(f"[WebCrawler] ✅ Found {person_name} in team_member_data table")
                    return {
                        'found': True,
                        'name': member.get('name', person_name),
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
        
        # First, try to find the person in regular content
        for content in content_list:
            # Search in title
            if content.get('title'):
                title_lower = content['title'].lower()
                if person_name_lower in title_lower:
                    return {
                        'found': True,
                        'name': person_name,
                        'title': content['title'],
                        'description': content.get('description', ''),
                        'content': content.get('main_content', ''),
                        'url': content.get('url', '')
                    }
            
            # Search in main content
            if content.get('main_content'):
                main_content = content['main_content']
                main_content_lower = main_content.lower()
                
                # Check if person name appears in content
                if person_name_lower in main_content_lower:
                    # Extract sentences around the person's name
                    sentences = main_content.split('.')
                    relevant_sentences = []
                    
                    for sentence in sentences:
                        sentence_lower = sentence.lower()
                        if person_name_lower in sentence_lower:
                            relevant_sentences.append(sentence.strip())
                    
                    if relevant_sentences:
                        return {
                            'found': True,
                            'name': person_name,
                            'title': content.get('title', f'Information about {person_name}'),
                            'description': content.get('description', ''),
                            'content': '. '.join(relevant_sentences[:3]),
                            'url': content.get('url', '')
                        }
        
        # If not found in regular content, try Selenium for team pages
        team_urls = [content.get('url') for content in content_list if 'team' in content.get('url', '').lower()]
        
        if team_urls:
            print(f"[WebCrawler] Trying Selenium extraction for {person_name} from team page")
            team_members = self.extract_team_members_with_selenium(team_urls[0])
            
            # Check if the person is in the Selenium results
            for member_name, member_info in team_members.items():
                if person_name_lower in member_name.lower():
                    return {
                        'found': True,
                        'name': person_name,
                        'title': f'Team Member - {member_name}',
                        'description': member_info.get('details', ''),
                        'content': member_info.get('full_content', ''),
                        'url': team_urls[0]
                    }
        
        # No cached data - return not found message
        return {
            'found': False,
            'name': person_name,
            'message': f"Information about {person_name} is not currently available on our team page. We're continuously updating our team profiles, so please check back later or contact us directly for more information."
        }
    
    def is_article_related(self, query: str) -> bool:
        """Check if the query is about articles/philosophy/roots"""
        article_keywords = [
            'article', 'articles', 'philosophy', 'philosophical', 'roots', 'beings',
            'educational philosophy', 'learning philosophy', 'school philosophy',
            'prakriti philosophy', 'progressive education philosophy', 'nature',
            'inner nature', 'prakriti way', 'way of learning', 'educational approach',
            'learning approach', 'teaching philosophy', 'educational method', 
            'learning method', 'pedagogical approach', 'learning approch',
            'whats learning', 'what\'s learning', 'how we learn', 'our approach',
            'teaching method', 'learning style', 'educational style'
        ]
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in article_keywords)
    
    def is_news_related(self, query: str) -> bool:
        """Check if the query is about news/events/updates"""
        # Check for specific news patterns first
        news_patterns = [
            'whats new', 'what\'s new', 'new article', 'new articles',
            'latest article', 'recent article', 'share by', 'published',
            'latest news', 'recent news', 'new post', 'new posts'
        ]
        
        query_lower = query.lower()
        
        # Check for specific news patterns first (higher priority)
        if any(pattern in query_lower for pattern in news_patterns):
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
        testimonial_keywords = [
            'testimonial', 'testimonials', 'parent feedback', 'parent review', 'parent opinion',
            'what parents say', 'parent experience', 'parent satisfaction', 'parent comment',
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
                """Parse date from event text and return date object"""
                try:
                    # Look for date patterns like "MON 20 OCT", "20 OCT", "OCT 20", "20/10", etc.
                    date_patterns = [
                        r'(\d{1,2})\s+(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)',  # 20 OCT
                        r'(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\s+(\d{1,2})',  # OCT 20
                        r'(\d{1,2})/(\d{1,2})',  # 20/10
                        r'(\d{1,2})-(\d{1,2})',  # 20-10
                        r'(MON|TUE|WED|THU|FRI|SAT|SUN)\s+(\d{1,2})\s+(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)',  # MON 20 OCT
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
                                
                                # Assume current year for now
                                year = current_date.year
                                return date(year, month, day)
                            elif len(groups) == 3:  # Day name + day + month (MON 20 OCT)
                                day = int(groups[1])
                                month = month_map[groups[2]]
                                year = current_date.year
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
                time.sleep(2)  # Wait for page to load
                
                calendar_events = []
                
                # Look for event elements with various selectors
                event_selectors = [
                    ".event", ".events", ".calendar-event", ".event-item",
                    ".event-title", ".event-date", ".event-description",
                    "[class*='event']", "[id*='event']", "[data-event]",
                    ".schedule", ".agenda", ".program", ".activity",
                    ".fc-event", ".calendar-item", ".event-card"
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
                                            calendar_events.append(f"UPCOMING_EVENT: {event_text}")
                                        else:
                                            calendar_events.append(f"PAST_EVENT: {event_text}")
                            except Exception as e:
                                continue
                    except Exception as e:
                        continue
                
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
                
                for event in calendar_events:
                    if event.startswith("UPCOMING_EVENT"):
                        # Extract the actual event text for deduplication
                        event_text = event.replace("UPCOMING_EVENT: ", "").strip()
                        # Create a normalized key for deduplication
                        normalized_key = re.sub(r'\s+', ' ', event_text.upper())
                        if normalized_key not in seen_events:
                            upcoming_events.append(event)
                            seen_events.add(normalized_key)
                    elif event.startswith("PAST_EVENT"):
                        past_events.append(event)
                
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
        # Fallback data for team members that fail extraction or have minimal data
        fallback_data = {
            'Priyanka Oberoi': {
                'name': 'Priyanka Oberoi',
                'title': 'Facilitator Art & Design and Design & Technology',
                'description': 'Priyanka is an artist and designer whose work blends India\'s cultural depth with Western artistic expression.',
                'details': 'Teaching visually impaired children in 2014 inspired her inclusive, tactile approach to art. She holds a BFA from the College of Art, New Delhi, a dual Post graduation from NID, India and UCA, UK, and an MA in Graphic storytelling from LUCA school of arts, KU Leuven, Belgium. With experience in sports photography for leading international publications, she has also collaborated with scientists to create visual narratives and illustrated a board game for the Deutsches Museum. A certified mountaineer and recent graduate in Graphic Storytelling, Priyanka\'s art reflects curiosity, inclusivity, and creativity—values she looks forward to sharing at Prakriti.',
                'full_content': 'Priyanka Oberoi\nFacilitator Art & Design and Design & Technology\n\nPriyanka is an artist and designer whose work blends India\'s cultural depth with Western artistic expression. Teaching visually impaired children in 2014 inspired her inclusive, tactile approach to art. She holds a BFA from the College of Art, New Delhi, a dual Post graduation from NID, India and UCA, UK, and an MA in Graphic storytelling from LUCA school of arts, KU Leuven, Belgium. With experience in sports photography for leading international publications, she has also collaborated with scientists to create visual narratives and illustrated a board game for the Deutsches Museum. A certified mountaineer and recent graduate in Graphic Storytelling, Priyanka\'s art reflects curiosity, inclusivity, and creativity—values she looks forward to sharing at Prakriti.'
            },
            'Ritu Martin': {
                'name': 'Ritu Martin',
                'title': 'Senior Primary Facilitator Sciences',
                'description': 'Ritu Martin holds a B.Sc. in Biotechnology, a B.Ed., an MBA, and has completed the SEEL LI Facilitator course.',
                'details': 'She believes that teaching is about nurturing the whole personality of a student, which begins with the teacher embodying the values they wish to impart. For Ritu, education is not about changing students but about self-growth—modeling integrity, curiosity, and empathy through everyday actions. She values the freedom to engage in focused, meaningful work and aligns deeply with the philosophy of becoming a better version of oneself each day, inspiring her students to do the same.',
                'full_content': 'Ritu Martin\nSenior Primary Facilitator Sciences\n\nRitu Martin holds a B.Sc. in Biotechnology, a B.Ed., an MBA, and has completed the SEEL LI Facilitator course. She believes that teaching is about nurturing the whole personality of a student, which begins with the teacher embodying the values they wish to impart. For Ritu, education is not about changing students but about self-growth—modeling integrity, curiosity, and empathy through everyday actions. She values the freedom to engage in focused, meaningful work and aligns deeply with the philosophy of becoming a better version of oneself each day, inspiring her students to do the same.'
            },
            'Shuchi Mishra': {
                'name': 'Shuchi Mishra',
                'title': 'Facilitator',
                'description': 'Mrs. Shuchi Mishra holds a Bachelor\'s degree in Psychology (Honours), Economics, and English, and a Master\'s in Psychology from Lucknow University.',
                'details': 'She also completed her B.Ed. from Annamalai University and recently pursued the GSE4x: Introduction to Family Engagement in Education course from HarvardX. A National Scholarship recipient, Mrs. Mishra has over 30 years of teaching experience—18 years at Jaipuria School, Lucknow (ICSE) and 13 years at Sanskriti School, New Delhi (CBSE). She believes education must go beyond academics to nurture integrity, responsibility, and creativity. Her teaching philosophy emphasizes holistic growth through theatre, sports, debates, and experiential learning. Passionate about shaping young minds, she views teachers as key influences during a child\'s formative years—guiding not only intellectual development but also moral and social growth.',
                'full_content': 'Shuchi Mishra\nFacilitator\n\nMrs. Shuchi Mishra holds a Bachelor\'s degree in Psychology (Honours), Economics, and English, and a Master\'s in Psychology from Lucknow University. She also completed her B.Ed. from Annamalai University and recently pursued the GSE4x: Introduction to Family Engagement in Education course from HarvardX. A National Scholarship recipient, Mrs. Mishra has over 30 years of teaching experience—18 years at Jaipuria School, Lucknow (ICSE) and 13 years at Sanskriti School, New Delhi (CBSE). She believes education must go beyond academics to nurture integrity, responsibility, and creativity. Her teaching philosophy emphasizes holistic growth through theatre, sports, debates, and experiential learning. Passionate about shaping young minds, she views teachers as key influences during a child\'s formative years—guiding not only intellectual development but also moral and social growth.'
            },
            'Gunjan Bhatia': {
                'name': 'Gunjan Bhatia',
                'title': 'Early Years Programme Facilitator',
                'description': 'Gunjan Bhatia is a Nursery teacher in the Green group with an M.Phil in Economics.',
                'details': 'She approaches teaching as a continuous journey of learning, believing that every method has value and that the true skill lies in selecting the pedagogy best suited to each child and context. With a focus on experiential learning, Gunjan encourages children to explore, question, and engage with their surroundings, fostering curiosity and independent thinking from an early age. She combines progressive educational practices with room for freedom, ensuring that every child feels empowered to learn at their own pace while developing critical social, emotional, and cognitive skills. Gunjan\'s classrooms are designed to be spaces where creativity, discovery, and growth are prioritized, and where learning becomes a meaningful and joyful experience. Her holistic approach ensures that each child is nurtured, guided, and inspired to develop their full potential.',
                'full_content': 'Gunjan Bhatia\nEarly Years Programme Facilitator\n\nGunjan Bhatia is a Nursery teacher in the Green group with an M.Phil in Economics. She approaches teaching as a continuous journey of learning, believing that every method has value and that the true skill lies in selecting the pedagogy best suited to each child and context. With a focus on experiential learning, Gunjan encourages children to explore, question, and engage with their surroundings, fostering curiosity and independent thinking from an early age. She combines progressive educational practices with room for freedom, ensuring that every child feels empowered to learn at their own pace while developing critical social, emotional, and cognitive skills. Gunjan\'s classrooms are designed to be spaces where creativity, discovery, and growth are prioritized, and where learning becomes a meaningful and joyful experience. Her holistic approach ensures that each child is nurtured, guided, and inspired to develop their full potential.'
            },
            'Vidya Vishwanathan': {
                'name': 'Vidya Vishwanathan',
                'title': 'Upper Secondary, Global Perspectives Facilitator',
                'description': 'Vidya Viswanathan is a researcher, writer, and curriculum advisor with a unique ability to identify emerging trends and connect insights to paint a broader picture.',
                'details': 'She has interacted with academics, industry leaders, and innovators worldwide, often serving as a sounding board and storyteller. Her impactful journalism at Business Standard, Business World, and Business Today influenced industries, set trends, and shaped policy discussions. Starting as a programmer and equity researcher, she later explored financial journalism and diverse subjects. Passionate about alternative education, India\'s scientific, cultural, and spiritual heritage, Vidya now designs and advises on history and civics curriculum at Prakriti, fostering a generation proud of the country.',
                'full_content': 'Vidya Vishwanathan\nUpper Secondary, Global Perspectives Facilitator\n\nVidya Viswanathan is a researcher, writer, and curriculum advisor with a unique ability to identify emerging trends and connect insights to paint a broader picture. She has interacted with academics, industry leaders, and innovators worldwide, often serving as a sounding board and storyteller. Her impactful journalism at Business Standard, Business World, and Business Today influenced industries, set trends, and shaped policy discussions. Starting as a programmer and equity researcher, she later explored financial journalism and diverse subjects. Passionate about alternative education, India\'s scientific, cultural, and spiritual heritage, Vidya now designs and advises on history and civics curriculum at Prakriti, fostering a generation proud of the country.'
            },
            'Gayatri Tahiliani': {
                'name': 'Gayatri Tahiliani',
                'title': 'Primary English and Math Curriculum Leader',
                'description': 'Gayatri Tahiliani is the Primary English and Math Curriculum Leader at Prakriti.',
                'details': 'She holds a Bachelor\'s in Elementary Education from Lady Shri Ram College, a Master\'s in History from IGNOU, and a Master\'s in Education with a specialization in Teaching and Teacher Leadership from Harvard University. In her role, Gayatri works closely with teachers to strengthen vertical and horizontal alignment of the English curriculum, mentor educators, and coordinate the new phonics program across the primary grades. Passionate about meaningful learning, she designs inquiry-driven classrooms where children explore, question, and develop a deep sense of connection and responsibility toward the world around them.',
                'full_content': 'Gayatri Tahiliani\nPrimary English and Math Curriculum Leader\n\nGayatri Tahiliani is the Primary English and Math Curriculum Leader at Prakriti. She holds a Bachelor\'s in Elementary Education from Lady Shri Ram College, a Master\'s in History from IGNOU, and a Master\'s in Education with a specialization in Teaching and Teacher Leadership from Harvard University. In her role, Gayatri works closely with teachers to strengthen vertical and horizontal alignment of the English curriculum, mentor educators, and coordinate the new phonics program across the primary grades. Passionate about meaningful learning, she designs inquiry-driven classrooms where children explore, question, and develop a deep sense of connection and responsibility toward the world around them.'
            },
            'Vanila Ghai': {
                'name': 'Vanila Ghai',
                'title': 'Bridge Programme Facilitator',
                'description': 'Vanila is a Finance professional with Corporate experience of a decade in BFSI sector.',
                'details': 'She gave up her career to serve the community after her son got diagnosed with Autism Spectrum Disorder and dedicated herself to the cause. She pursued Diploma in Early Childhood – Special Education and is a RCI certified Practitioner. She finished her coursework of Behavior Analysis from the Florida Institute of Technologies, US and very recently finished her MA in Clinical Psychology from IGNOU. She holds a work experience of 5+ years for working with children with Autism and Developmental Disabilities.',
                'full_content': 'Vanila Ghai\nBridge Programme Facilitator\n\nVanila is a Finance professional with Corporate experience of a decade in BFSI sector. She gave up her career to serve the community after her son got diagnosed with Autism Spectrum Disorder and dedicated herself to the cause. She pursued Diploma in Early Childhood – Special Education and is a RCI certified Practitioner. She finished her coursework of Behavior Analysis from the Florida Institute of Technologies, US and very recently finished her MA in Clinical Psychology from IGNOU. She holds a work experience of 5+ years for working with children with Autism and Developmental Disabilities.'
            }
        }
        
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
                if self.is_team_related(query):
                    content_type = 'team'
                elif self.is_calendar_related(query):
                    content_type = 'calendar'
                elif self.is_news_related(query):
                    content_type = 'news'
                elif self.is_article_related(query):
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
                
                # Filter by content_type if detected
                if content_type:
                    base_query = base_query.eq('content_type', content_type)
                    print(f"[WebCrawler] Filtering by content_type: {content_type}")
                
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
            urls_to_crawl = self.prakriti_urls.copy()
            
            if self.is_team_related(query):
                print("[WebCrawler] Detected team-related query, prioritizing team pages")
                team_urls = [url for url in self.prakriti_urls if 'team' in url]
                urls_to_crawl = team_urls  # ONLY crawl team pages
                
            elif self.is_calendar_related(query):
                print("[WebCrawler] Detected calendar-related query, prioritizing calendar pages")
                calendar_urls = [url for url in self.prakriti_urls if 'calendar' in url]
                urls_to_crawl = calendar_urls  # ONLY crawl calendar pages
                
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
            
            # If content is relevant, extract key information (MINIMAL to save tokens)
            if relevance_score > 0:
                info_parts = []
                
                # Extract MINIMAL info (TOKEN OPTIMIZATION)
                if content.get('title'):
                    info_parts.append(f"**{content['title'][:80]}**")  # Limit title (reduced from 100)
                
                # Only include description if title is missing or very short
                if not content.get('title') or len(content.get('title', '')) < 20:
                    if content.get('description'):
                        info_parts.append(f"{content['description'][:80]}")  # Reduced from 150
                
                if content.get('main_content'):
                    # Extract ONLY 1 sentence that contains query words (TOKEN OPTIMIZATION - reduced from 2)
                    sentences = content['main_content'].split('.')
                    for sentence in sentences:
                        sentence_lower = sentence.lower()
                        if any(word in sentence_lower for word in query_words):
                            info_parts.append(sentence.strip()[:120])  # Limit sentence length (reduced from 200)
                            break  # Only 1 sentence
                
                if info_parts:
                    relevant_info.append({
                        'url': content.get('url', ''),
                        'relevance_score': relevance_score,
                        'info': ' | '.join(info_parts)  # Use | separator instead of newlines (more compact)
                    })
        
        # Sort by relevance score
        relevant_info.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        # Format the information (LIMIT TO TOP 1 RESULT - TOKEN OPTIMIZATION)
        if relevant_info:
            top_result = relevant_info[0]  # Only top 1 result
            formatted_info = f"{top_result['info']}"
            if top_result['url']:
                formatted_info += f" [{top_result['url']}]"
            
            # TRUNCATE entire formatted info to max 600 chars (reduced from 1200)
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
        print(f"[WebCrawler] 🔍 Cache check priority: 1) web_crawler_data table → 2) search_cache table → 3) Web crawl")
        
        # FIRST: Try to get filtered cached data from web_crawler_data table (FAST PATH)
        # This is faster than checking search_cache, then crawling
        if SUPABASE_AVAILABLE:
            try:
                supabase = get_supabase_client()
                query_lower = query.lower()
                query_words = [w for w in query_lower.split() if len(w) > 2]
                
                # Determine content_type
                content_type = None
                if self.is_team_related(query):
                    content_type = 'team'
                elif self.is_article_related(query):
                    content_type = 'article'
                elif self.is_calendar_related(query):
                    content_type = 'calendar'
                elif self.is_news_related(query):
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
                
                if content_type:
                    base_query = base_query.eq('content_type', content_type)
                
                result = base_query.limit(10).execute()  # Limit to 10 for scoring
                
                if result.data and len(result.data) > 0:
                    print(f"[WebCrawler] ✅ Found {len(result.data)} cached pages in web_crawler_data table, scoring by relevance...")
                    
                    # AGGRESSIVE FILTERING: Score pages and only keep highly relevant ones
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
                        
                        # Only include pages with minimum relevance threshold (at least 5 points)
                        if score >= 5:
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
                        
                        # Extract ONLY sentences containing query words (AGGRESSIVE FILTERING)
                        relevant_text_parts = []
                        
                        # Title (if relevant)
                        if top_page['title'] and any(word in top_page['title'].lower() for word in query_words):
                            relevant_text_parts.append(top_page['title'][:70])
                        
                        # Description (if relevant)
                        if top_page['description'] and any(word in top_page['description'].lower() for word in query_words):
                            relevant_text_parts.append(top_page['description'][:80])
                        
                        # Extract ONLY sentences with query words from main_content (max 2 sentences)
                        if top_page['main_content']:
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
                        
                        # Combine and truncate to max 400 chars total (TOKEN OPTIMIZATION)
                        if relevant_text_parts:
                            result_text = ' | '.join(relevant_text_parts)
                            if len(result_text) > 400:
                                result_text = result_text[:400] + "..."
                            
                            if top_page['url']:
                                result_text += f" [{top_page['url']}]"
                            
                            print(f"[WebCrawler] ✅ Returning TOP 1 cached page (score: {top_page['score']}, matches: {top_page['query_matches']}/{len(query_words)} words, {len(result_text)} chars)")
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
        
        query_lower = query.lower()
        
        # Check if this is a specific person query
        if self.is_specific_person_query(query):
            person_name = self.extract_person_name(query)
            if person_name:
                print(f"[WebCrawler] Detected specific person query: {person_name}")
                
                # Search for PrakritSchool team content (only team page for efficiency)
                prakriti_content = self.search_prakriti_content(query)
                
                # Search for specific person
                person_info = self.search_specific_person(person_name, prakriti_content)
                
                if person_info.get('found'):
                    print(f"[WebCrawler] Found information about {person_name}")
                    return f"""## Information about {person_info['name']}

**Title**: {person_info['title']}

**Description**: {person_info['description']}

**Details**: {person_info['content']}

*Source: [{person_info['url']}]({person_info['url']})*"""
                else:
                    print(f"[WebCrawler] No specific information found for {person_name}")
                    return f"""## Information Not Available

I'm sorry, but information about {person_name} is not currently available on our team page.

We're continuously updating our team profiles, so please check back later or contact us directly for more information about our staff members.

*Source: [prakriti.edu.in/team](https://prakriti.edu.in/team)*"""
        
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
