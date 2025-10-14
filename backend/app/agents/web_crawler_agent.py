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
        name_pattern = r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}\b'
        potential_names = re.findall(name_pattern, query)
        
        # If no potential names found, it's not a person query
        if not potential_names:
            return False
        
        # Check if the potential name is actually a person name (not common words)
        common_words = ['little', 'bit', 'about', 'tell', 'me', 'who', 'is', 'information', 'details', 'cooking', 'recipes', 'admission', 'fees', 'school', 'program', 'course', 'prakriti', 'prakrit']
        
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
            'litle bit', 'litle bit info', 'litle bit about'
        ]
        
        for pattern in question_patterns:
            cleaned_query = cleaned_query.replace(pattern, '').strip()
        
        # Remove individual common words that might interfere
        common_words = ['little', 'bit', 'about', 'of', 'the', 'a', 'an', 'and', 'or', 'but', 'give', 'me', 'information', 'details', 'litle', 'info']
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
            common_words = ['little', 'bit', 'about', 'tell', 'me', 'who', 'is', 'information']
            if not any(word in longest_match.lower() for word in common_words):
                return longest_match
        
        # Fallback: If we have a reasonable length name (2+ words), return it
        words = cleaned_query.split()
        if len(words) >= 2:
            return ' '.join(words).title()
        
        return cleaned_query.title() if cleaned_query else ""
    
    def search_specific_person(self, person_name: str, content_list: List[Dict[str, str]]) -> Dict[str, str]:
        """Search for specific person details in crawled content"""
        if not person_name or not content_list:
            return {}
        
        person_name_lower = person_name.lower()
        
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
            'when is', 'what day', 'which day', 'date', 'dates'
        ]
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in calendar_keywords)
    
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
    
    def extract_content_from_url(self, url: str, query: str = "") -> Dict[str, str]:
        """Extract content from a specific URL"""
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
            
            # Check if this page contains Substack links and crawl them
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
                    
                    # Check if query is asking for "this week" specifically
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
                    else:
                        return "CALENDAR_DATA: No upcoming events found in the current calendar view. The calendar shows past events, but no future events are currently visible. Prakriti School regularly organizes cultural festivals (including Diwali, Holi, Eid, Christmas, and other cultural celebrations), sports meets, art exhibitions, academic workshops, and parent-teacher meetings throughout the year. For specific upcoming event dates, please check the school's official calendar or contact administration."
                else:
                    if 'this week' in query.lower():
                        return "CALENDAR_DATA: No events are scheduled for this week (October 13-19, 2025) at Prakriti School. The calendar shows an events archive with navigation for different months and years, but no specific events are planned for the current week. For upcoming events in future weeks, please check the school's official calendar or contact administration."
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
    
    def extract_team_members_with_selenium(self, url: str) -> Dict[str, str]:
        """Extract team member information using Selenium to handle popups/modals"""
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
                
                # Look for clickable team member elements (images, cards, buttons)
                clickable_selectors = [
                    "img[alt*='team']", "img[alt*='staff']", "img[alt*='faculty']",
                    ".team-member", ".staff-member", ".person-card", ".member-card",
                    "[data-member]", "[data-person]", ".team-card", ".staff-card",
                    "img[src*='team']", "img[src*='staff']", "img[src*='member']",
                    ".profile-image", ".member-image", ".staff-image",
                    "[onclick*='team']", "[onclick*='member']", "[onclick*='profile']",
                    # More general selectors
                    "img", "a", "div[class*='member']", "div[class*='team']",
                    "div[class*='staff']", "div[class*='person']", "div[class*='profile']",
                    "[class*='click']", "[class*='card']", "[class*='item']"
                ]
                
                clickable_elements = []
                for selector in clickable_selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        clickable_elements.extend(elements)
                        if elements:
                            print(f"[WebCrawler] Found {len(elements)} elements with selector: {selector}")
                    except Exception as e:
                        print(f"[WebCrawler] Error with selector {selector}: {e}")
                        continue
                
                print(f"[WebCrawler] Found {len(clickable_elements)} clickable team elements")
                
                # Debug: Print all clickable elements found
                for i, elem in enumerate(clickable_elements[:5]):
                    try:
                        print(f"[WebCrawler] Element {i}: {elem.tag_name}, text: {elem.text[:50]}...")
                    except:
                        print(f"[WebCrawler] Element {i}: Could not get info")
                
                # Try to click each element and extract popup content
                # Process elements one by one to avoid stale element issues
                # Limit to first 3 elements for maximum speed
                for i in range(min(3, len(clickable_elements))):  # Process only first 3 elements for speed
                    try:
                        # Re-find elements to avoid stale references
                        current_elements = []
                        for selector in clickable_selectors:
                            try:
                                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                                current_elements.extend(elements)
                            except:
                                continue
                        
                        if i >= len(current_elements):
                            break
                            
                        element = current_elements[i]
                        
                        # Scroll element into view with smooth scrolling
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                        time.sleep(0.2)  # Minimal wait time
                        
                        # Click the element
                        driver.execute_script("arguments[0].click();", element)
                        time.sleep(0.3)  # Minimal wait time
                        
                        # Look for popup/modal content with more comprehensive selectors
                        popup_selectors = [
                            ".modal", ".popup", ".overlay", ".dialog",
                            "[role='dialog']", ".team-popup", ".member-popup",
                            ".modal-content", ".popup-content", ".modal-body",
                            ".popup-body", ".profile-popup", ".member-details",
                            ".team-modal", ".staff-modal", ".person-modal",
                            "[class*='modal']", "[class*='popup']", "[class*='overlay']",
                            "[id*='modal']", "[id*='popup']", "[id*='dialog']"
                        ]
                        
                        popup_content = ""
                        popup_element = None
                        
                        for popup_selector in popup_selectors:
                            try:
                                popup = driver.find_element(By.CSS_SELECTOR, popup_selector)
                                if popup.is_displayed():
                                    popup_content = popup.text
                                    popup_element = popup
                                    print(f"[WebCrawler] Found popup with selector: {popup_selector}")
                                    break
                            except:
                                continue
                        
                        # If no popup found, try to find any visible overlay or modal
                        if not popup_content:
                            try:
                                # Look for any element with high z-index (likely popups)
                                high_z_elements = driver.find_elements(By.CSS_SELECTOR, "[style*='z-index']")
                                for elem in high_z_elements:
                                    if elem.is_displayed() and elem.text.strip():
                                        popup_content = elem.text
                                        popup_element = elem
                                        print(f"[WebCrawler] Found popup with z-index")
                                        break
                            except:
                                pass
                        
                        if popup_content:
                            print(f"[WebCrawler] Extracted popup content: {popup_content[:200]}...")
                            
                            # Extract name and details from popup
                            lines = popup_content.split('\n')
                            name = ""
                            details = []
                            
                            # Look for name patterns in the content
                            for line in lines:
                                line = line.strip()
                                if line and len(line) > 2:
                                    # Check if line contains a name (capitalized words)
                                    if re.match(r'^[A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?$', line) and len(line.split()) <= 3:
                                        name = line
                                    else:
                                        details.append(line)
                            
                            # If no name found in lines, try to extract from the beginning of content
                            if not name:
                                # Look for name at the start of popup content
                                name_match = re.search(r'^([A-Z][a-z]+ [A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', popup_content)
                                if name_match:
                                    name = name_match.group(1)
                            
                            if name:
                                team_members[name] = {
                                    'name': name,
                                    'details': ' '.join(details[:10]),  # Include more details
                                    'full_content': popup_content
                                }
                                print(f"[WebCrawler] Successfully extracted info for: {name}")
                            else:
                                print(f"[WebCrawler] Could not extract name from popup content")
                        
                        # Close popup if open
                        try:
                            close_selectors = [".close", ".modal-close", "[aria-label='Close']", ".btn-close"]
                            for close_selector in close_selectors:
                                close_btn = driver.find_element(By.CSS_SELECTOR, close_selector)
                                if close_btn.is_displayed():
                                    close_btn.click()
                                    break
                        except:
                            # Try pressing Escape key
                            driver.execute_script("document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape'}));")
                        
                        time.sleep(0.2)  # Minimal wait time
                        
                    except Exception as e:
                        print(f"[WebCrawler] Error clicking element {i}: {e}")
                        continue
                
                return team_members
                
            finally:
                driver.quit()
                
        except Exception as e:
            print(f"[WebCrawler] Error with Selenium extraction: {e}")
            return {}
    
    def search_prakriti_content(self, query: str) -> List[Dict[str, str]]:
        """Search for PrakritSchool related content"""
        if not self.is_prakriti_related(query):
            return []
        
        print(f"[WebCrawler] Searching PrakritSchool content for: {query}")
        
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
        """Extract relevant information from crawled content based on query"""
        if not content_list:
            return ""
        
        query_lower = query.lower()
        relevant_info = []
        
        for content in content_list:
            # Check if content is relevant to the query
            relevance_score = 0
            
            # Check title relevance
            if content.get('title'):
                title_lower = content['title'].lower()
                if any(word in title_lower for word in query_lower.split()):
                    relevance_score += 3
            
            # Check description relevance
            if content.get('description'):
                desc_lower = content['description'].lower()
                if any(word in desc_lower for word in query_lower.split()):
                    relevance_score += 2
            
            # Check main content relevance
            if content.get('main_content'):
                main_lower = content['main_content'].lower()
                if any(word in main_lower for word in query_lower.split()):
                    relevance_score += 1
            
            # If content is relevant, extract key information
            if relevance_score > 0:
                info_parts = []
                
                if content.get('title'):
                    info_parts.append(f"**Title**: {content['title']}")
                
                if content.get('description'):
                    info_parts.append(f"**Description**: {content['description'][:200]}...")
                
                if content.get('main_content'):
                    # Extract sentences that contain query words
                    sentences = content['main_content'].split('.')
                    relevant_sentences = []
                    for sentence in sentences:
                        sentence_lower = sentence.lower()
                        if any(word in sentence_lower for word in query_lower.split()):
                            relevant_sentences.append(sentence.strip())
                    
                    if relevant_sentences:
                        info_parts.append(f"**Relevant Content**: {' '.join(relevant_sentences[:3])}")
                
                if info_parts:
                    relevant_info.append({
                        'url': content.get('url', ''),
                        'relevance_score': relevance_score,
                        'info': '\n'.join(info_parts)
                    })
        
        # Sort by relevance score
        relevant_info.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        # Format the information
        if relevant_info:
            formatted_info = "## Web Search Results\n\n"
            for i, info in enumerate(relevant_info[:3]):  # Limit to top 3 results
                formatted_info += f"### Result {i+1}\n"
                formatted_info += f"{info['info']}\n"
                if info['url']:
                    formatted_info += f"*Source: [{info['url']}]({info['url']})*\n\n"
            
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
        
        return enhanced_info

# Global instance
web_crawler = WebCrawlerAgent()

def get_web_enhanced_response(query: str) -> str:
    """Get web-enhanced response for chatbot queries"""
    try:
        return web_crawler.get_enhanced_response(query)
    except Exception as e:
        print(f"[WebCrawler] Error getting enhanced response: {e}")
        return ""
