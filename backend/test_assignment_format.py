"""
Test script to verify assignment data format and expected response format
This simulates what the chatbot should receive and generate
"""

import json
from datetime import datetime

# Simulate the data structure from the database (what comes from get_student_coursework_data)
sample_coursework_data = {
    "classroom_data": [
        {
            "name": "A2-1st Year",
            "course_link": "https://classroom.google.com/c/MjM1NjczMDU0NTI4",
            "coursework": [
                {
                    "title": "CE-1 : Mathematics-1 : 28/11/2020 : 02.00 pm",
                    "alternate_link": "https://classroom.google.com/c/MjM1NjczMDU0NTI4/a/MjkzNDg1MDg4NjE5/details",
                    "due": "2020-11-28T14:00:00Z",
                    "description": "Complete the mathematics assignment covering algebra and geometry",
                    "work_type": "ASSIGNMENT",
                    "status": "NEW"
                },
                {
                    "title": "CE-2 : Maths-1 : 19/12/2020  Saturday : 02.00 pm",
                    "alternate_link": "https://classroom.google.com/c/MjM1NjczMDU0NTI4/a/MjkzNDg1MDg4NjE2/details",
                    "due": "2020-12-19T14:00:00Z",
                    "description": "Second mathematics assignment on calculus",
                    "work_type": "ASSIGNMENT",
                    "status": "NEW"
                },
                {
                    "title": "CE-3 : Maths-1 : 09/01/2021 Saturday : 02.00 pm",
                    "alternate_link": "https://classroom.google.com/c/MjM1NjczMDU0NTI4/a/MjkzNDg1MDg4NjE3/details",
                    "due": "2021-01-09T14:00:00Z",
                    "description": "Third mathematics assignment on trigonometry",
                    "work_type": "ASSIGNMENT",
                    "status": "TURNED_IN"
                },
                {
                    "title": "CE-4 : Maths-1 : 05/02/2021 Friday : 03.30 pm",
                    "alternate_link": "https://classroom.google.com/c/MjM1NjczMDU0NTI4/a/MjkzNDg1MDg4NjE4/details",
                    "due": "2021-02-05T15:30:00Z",
                    "description": "Fourth mathematics assignment on statistics",
                    "work_type": "ASSIGNMENT",
                    "status": "NEW"
                },
                {
                    "title": "Final Assignment: Maths 1: Deadline: 18-03-2021",
                    "alternate_link": "https://classroom.google.com/c/MjM1NjczMDU0NTI4/a/MjkzNDg1MDg4NjE5/details",
                    "due": "2021-03-18T23:59:00Z",
                    "description": "Final comprehensive mathematics assignment covering all topics",
                    "work_type": "ASSIGNMENT",
                    "status": "NEW"
                },
                {
                    "title": "CE-1 : ENGLISH : 16/12/2020 Wednesday till 03.00 pm",
                    "alternate_link": "https://classroom.google.com/c/MjM1NjczMDU0NTI4/a/MjkzNDg1MDg4NjIw/details",
                    "due": "2020-12-16T15:00:00Z",
                    "description": "English literature analysis assignment",
                    "work_type": "ASSIGNMENT",
                    "status": "NEW"
                },
                {
                    "title": "CE-2 : ENGLISH : 13-01-2021",
                    "alternate_link": "https://classroom.google.com/c/MjM1NjczMDU0NTI4/a/MjkzNDg1MDg4NjIx/details",
                    "due": "2021-01-13T23:59:00Z",
                    "description": "English grammar and composition assignment",
                    "work_type": "ASSIGNMENT",
                    "status": "TURNED_IN"
                },
                {
                    "title": "Final Assignment: ENGLISH: Deadline: 18-03-2021",
                    "alternate_link": "https://classroom.google.com/c/MjM1NjczMDU0NTI4/a/MjkzNDg1MDg4NjIy/details",
                    "due": "2021-03-18T23:59:00Z",
                    "description": "Final English assignment - creative writing and analysis",
                    "work_type": "ASSIGNMENT",
                    "status": "NEW"
                }
            ]
        }
    ]
}

def print_data_structure():
    """Print the data structure that comes from the database"""
    print("=" * 80)
    print("DATA STRUCTURE FROM DATABASE")
    print("=" * 80)
    print(json.dumps(sample_coursework_data, indent=2))
    print("\n")

def print_actual_assignment_titles():
    """Print the actual assignment titles that should be extracted"""
    print("=" * 80)
    print("ACTUAL ASSIGNMENT TITLES FROM DATA")
    print("=" * 80)
    titles = []
    for course in sample_coursework_data["classroom_data"]:
        for cw in course.get("coursework", []):
            titles.append(cw.get("title", ""))
    
    for idx, title in enumerate(titles, 1):
        print(f"{idx}. {title}")
    print("\n")

def print_maths_assignments():
    """Print what Maths assignments should look like"""
    print("=" * 80)
    print("EXPECTED RESPONSE FOR: 'show my maths assignments'")
    print("=" * 80)
    
    maths_assignments = []
    for course in sample_coursework_data["classroom_data"]:
        for cw in course.get("coursework", []):
            title = cw.get("title", "")
            if any(kw in title.upper() for kw in ["MATH", "MATHS", "MATHEMATICS"]):
                maths_assignments.append({
                    "title": title,
                    "alternate_link": cw.get("alternate_link", ""),
                    "due": cw.get("due", ""),
                    "description": cw.get("description", ""),
                    "status": cw.get("status", "")
                })
    
    print("### Maths Assignments:\n")
    for idx, assignment in enumerate(maths_assignments, 1):
        print(f"{idx}. **{assignment['title']}**")
        if assignment.get('description'):
            print(f"   **Description:** {assignment['description']}")
        if assignment.get('due'):
            print(f"   **Due Date:** {assignment['due']}")
        if assignment.get('status'):
            print(f"   **Status:** {assignment['status']}")
        if assignment.get('alternate_link'):
            print(f"   **[View Assignment]({assignment['alternate_link']})**")
        print()
    print("\n")

def print_english_assignments():
    """Print what English assignments should look like"""
    print("=" * 80)
    print("EXPECTED RESPONSE FOR: 'show my english assignments'")
    print("=" * 80)
    
    english_assignments = []
    for course in sample_coursework_data["classroom_data"]:
        for cw in course.get("coursework", []):
            title = cw.get("title", "")
            if "ENGLISH" in title.upper():
                english_assignments.append({
                    "title": title,
                    "alternate_link": cw.get("alternate_link", ""),
                    "due": cw.get("due", ""),
                    "description": cw.get("description", ""),
                    "status": cw.get("status", "")
                })
    
    print("### English Assignments:\n")
    for idx, assignment in enumerate(english_assignments, 1):
        print(f"{idx}. **{assignment['title']}**")
        if assignment.get('description'):
            print(f"   **Description:** {assignment['description']}")
        if assignment.get('due'):
            print(f"   **Due Date:** {assignment['due']}")
        if assignment.get('status'):
            print(f"   **Status:** {assignment['status']}")
        if assignment.get('alternate_link'):
            print(f"   **[View Assignment]({assignment['alternate_link']})**")
        print()
    print("\n")

def print_forbidden_format():
    """Print examples of FORBIDDEN response formats"""
    print("=" * 80)
    print("FORBIDDEN RESPONSE FORMATS (DO NOT GENERATE THESE)")
    print("=" * 80)
    print("""
[X] FORBIDDEN EXAMPLE 1:
### Maths Assignments:
1. **Topic**: Geometry Shapes
   **Description**: Identify different geometric shapes and their properties.
   **Due Date**: 15th October 2021
   **Link**: [Geometry Shapes Assignment](assignment_link)

2. **Topic**: Fractions and Decimals
   **Description**: Practice converting fractions to decimals and vice versa.
   **Due Date**: 22nd October 2021
   **Link**: [Fractions and Decimals Assignment](assignment_link)

[X] FORBIDDEN EXAMPLE 2:
### English Assignments:
1. **Topic**: Literature Analysis
   - **Assignment**: Write a short analysis of the main themes in the novel "To Kill a Mockingbird" by Harper Lee.

2. **Topic**: Grammar
   - **Assignment**: Identify and correct the errors in the following sentences:
     - She don't like to eat vegetables.
     - The dog wagged it's tail happily.

[X] FORBIDDEN: Creating fake topics, generic examples, or made-up assignments
[X] FORBIDDEN: Using placeholder links like "assignment_link"
[X] FORBIDDEN: Generating example problems or generic descriptions
""")

def print_compact_json_format():
    """Print the compact JSON format that would be sent to LLM"""
    print("=" * 80)
    print("COMPACT JSON FORMAT (as sent to LLM)")
    print("=" * 80)
    
    # Create filtered format (what gets sent to LLM)
    filtered_courses = []
    for course in sample_coursework_data["classroom_data"]:
        filtered_course = {
            "name": course.get("name", ""),
            "course_link": course.get("course_link", ""),
            "coursework": []
        }
        for cw in course.get("coursework", []):
            cw_item = {
                "title": cw.get("title", ""),
            }
            if cw.get("alternate_link"):
                cw_item["alternate_link"] = cw.get("alternate_link")
            if cw.get("due"):
                cw_item["due"] = cw.get("due")
            if cw.get("description"):
                cw_item["description"] = cw.get("description")
            if cw.get("work_type"):
                cw_item["work_type"] = cw.get("work_type")
            if cw.get("status"):
                cw_item["status"] = cw.get("status")
            filtered_course["coursework"].append(cw_item)
        filtered_courses.append(filtered_course)
    
    # Compact format (no indentation, minimal whitespace)
    compact_json = json.dumps(filtered_courses, separators=(',', ':'))
    print(compact_json)
    print("\n")

def main():
    """Run all test outputs"""
    print("\n" + "=" * 80)
    print("ASSIGNMENT DATA FORMAT TEST SCRIPT")
    print("=" * 80 + "\n")
    
    print_data_structure()
    print_actual_assignment_titles()
    print_maths_assignments()
    print_english_assignments()
    print_forbidden_format()
    print_compact_json_format()
    
    print("=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    main()

