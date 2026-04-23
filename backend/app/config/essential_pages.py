"""
Essential Prakriti School pages for chatbot queries
Only these 10 pages are needed for accurate, fast responses
"""

# The team page is maintained via admin "Sync" / manual flows only—excluded from scheduled daily auto-crawl.
TEAM_PAGE_URL = "https://prakriti.edu.in/team/"

ESSENTIAL_PRAKRITI_PAGES = [
    # 1. Homepage - General school info
    "https://prakriti.edu.in/",
    
    # 2. Team/Staff - For "who is X" queries
    "https://prakriti.edu.in/team/",
    
    # 3. Philosophy/Approach - For "what is Prakriti" queries
    "https://prakriti.edu.in/prakriti-way-of-learning/",
    "https://prakriti.edu.in/roots-of-all-beings/",
    
    # 4. Programs - For academic queries
    "https://prakriti.edu.in/our-programmes/",
    
    # 5. Admissions - For admission queries
    "https://prakriti.edu.in/admissions/",
    "https://prakriti.edu.in/school-fees/",
    
    # 6. Contact - For contact info
    "https://prakriti.edu.in/contact/",
    
    # 7. Academic Year Flow calendar (replaces legacy prakriti.edu.in/calendar archive)
    "https://events.prakriti.edu.in/",
    
    # 8. News/Blog - For "latest news" queries (main page only)
    "https://prakriti.edu.in/blog-and-news/",
    
    # 9. Parents Testimonials - For "what say about parents" queries
    "https://prakriti.edu.in/what-our-parents-say-about-us/",
]

ESSENTIAL_PRAKRITI_PAGES_FOR_AUTO_CRAWL = [u for u in ESSENTIAL_PRAKRITI_PAGES if u != TEAM_PAGE_URL]

# Content type mapping for each page
PAGE_CONTENT_TYPES = {
    "https://prakriti.edu.in/": "general",
    "https://prakriti.edu.in/team/": "team",
    "https://prakriti.edu.in/prakriti-way-of-learning/": "article",
    "https://prakriti.edu.in/roots-of-all-beings/": "article",
    "https://prakriti.edu.in/our-programmes/": "academic",
    "https://prakriti.edu.in/admissions/": "admission",
    "https://prakriti.edu.in/school-fees/": "admission",
    "https://prakriti.edu.in/contact/": "contact",
    "https://events.prakriti.edu.in/": "calendar",
    "https://prakriti.edu.in/blog-and-news/": "news",
    "https://prakriti.edu.in/what-our-parents-say-about-us/": "testimonial",
}








