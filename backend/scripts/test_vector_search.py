"""
Test script to validate vector search accuracy and performance
Compares vector search results with keyword search and measures performance
"""
import os
import sys
import time
from typing import List, Dict
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.vector_search_service import get_vector_search_service
from supabase_config import get_supabase_client

load_dotenv()


def test_semantic_similarity():
    """Test semantic similarity (e.g., 'science teacher' finds science facilitators)"""
    print("\n" + "=" * 60)
    print("Test 1: Semantic Similarity")
    print("=" * 60)
    
    test_cases = [
        ("science teacher", "Should find science facilitators"),
        ("french facilitator", "Should find French facilitators"),
        ("math instructor", "Should find mathematics facilitators"),
        ("art and design teacher", "Should find Art & Design facilitators"),
    ]
    
    vector_service = get_vector_search_service()
    
    for query, expected in test_cases:
        print(f"\nQuery: '{query}'")
        print(f"Expected: {expected}")
        
        start_time = time.time()
        results = vector_service.search_team_members(query, limit=5, threshold=0.6)
        elapsed = (time.time() - start_time) * 1000  # Convert to ms
        
        if results:
            print(f"✅ Found {len(results)} results in {elapsed:.2f}ms")
            for i, result in enumerate(results[:3], 1):
                name = result.get('name', 'Unknown')
                title = result.get('title', '')
                similarity = result.get('similarity', 0)
                print(f"  {i}. {name} - {title} (similarity: {similarity:.2f})")
        else:
            print(f"❌ No results found")


def test_person_name_queries():
    """Test person name queries with typos"""
    print("\n" + "=" * 60)
    print("Test 2: Person Name Queries (with typos)")
    print("=" * 60)
    
    test_cases = [
        ("priyanka oberoi", "Correct spelling"),
        ("priyanka oberoy", "Typo in surname"),
        ("priyanka", "First name only"),
        ("oberoi", "Surname only"),
        ("ritoo martin", "Typo in first name"),
    ]
    
    vector_service = get_vector_search_service()
    
    for query, description in test_cases:
        print(f"\nQuery: '{query}' ({description})")
        
        start_time = time.time()
        results = vector_service.search_team_members(query, limit=3, threshold=0.5)
        elapsed = (time.time() - start_time) * 1000
        
        if results:
            print(f"✅ Found {len(results)} results in {elapsed:.2f}ms")
            for i, result in enumerate(results, 1):
                name = result.get('name', 'Unknown')
                similarity = result.get('similarity', 0)
                print(f"  {i}. {name} (similarity: {similarity:.2f})")
        else:
            print(f"❌ No results found")


def test_role_based_queries():
    """Test role-based queries"""
    print("\n" + "=" * 60)
    print("Test 3: Role-Based Queries")
    print("=" * 60)
    
    test_cases = [
        ("who is the principal", "Should find principal"),
        ("founding director", "Should find founding director"),
        ("co-founder", "Should find co-founder/founding director"),
        ("chief mentor", "Should find chief mentor"),
    ]
    
    vector_service = get_vector_search_service()
    
    for query, expected in test_cases:
        print(f"\nQuery: '{query}'")
        print(f"Expected: {expected}")
        
        start_time = time.time()
        results = vector_service.search_team_members(query, limit=3, threshold=0.6)
        elapsed = (time.time() - start_time) * 1000
        
        if results:
            print(f"✅ Found {len(results)} results in {elapsed:.2f}ms")
            for i, result in enumerate(results, 1):
                name = result.get('name', 'Unknown')
                title = result.get('title', '')
                similarity = result.get('similarity', 0)
                print(f"  {i}. {name} - {title} (similarity: {similarity:.2f})")
        else:
            print(f"❌ No results found")


def test_web_content_search():
    """Test web content search"""
    print("\n" + "=" * 60)
    print("Test 4: Web Content Search")
    print("=" * 60)
    
    test_cases = [
        ("admission process", "Should find admission pages"),
        ("school calendar", "Should find calendar pages"),
        ("team members", "Should find team pages"),
        ("academic programs", "Should find academic pages"),
    ]
    
    vector_service = get_vector_search_service()
    
    for query, expected in test_cases:
        print(f"\nQuery: '{query}'")
        print(f"Expected: {expected}")
        
        start_time = time.time()
        results = vector_service.search_web_content(query, limit=3, threshold=0.6)
        elapsed = (time.time() - start_time) * 1000
        
        if results:
            print(f"✅ Found {len(results)} results in {elapsed:.2f}ms")
            for i, result in enumerate(results, 1):
                title = result.get('title', 'Unknown')
                url = result.get('url', '')
                similarity = result.get('similarity', 0)
                print(f"  {i}. {title[:60]}... (similarity: {similarity:.2f})")
                print(f"     URL: {url[:60]}...")
        else:
            print(f"❌ No results found")


def compare_with_keyword_search():
    """Compare vector search with keyword search performance"""
    print("\n" + "=" * 60)
    print("Test 5: Performance Comparison (Vector vs Keyword)")
    print("=" * 60)
    
    test_query = "science facilitator"
    
    vector_service = get_vector_search_service()
    supabase = get_supabase_client()
    
    # Test vector search
    print(f"\nQuery: '{test_query}'")
    print("\n--- Vector Search ---")
    start_time = time.time()
    vector_results = vector_service.search_team_members(test_query, limit=5, threshold=0.6)
    vector_time = (time.time() - start_time) * 1000
    
    print(f"Time: {vector_time:.2f}ms")
    print(f"Results: {len(vector_results)}")
    if vector_results:
        for i, result in enumerate(vector_results[:3], 1):
            print(f"  {i}. {result.get('name', 'Unknown')} - {result.get('title', '')} (similarity: {result.get('similarity', 0):.2f})")
    
    # Test keyword search
    print("\n--- Keyword Search (ilike) ---")
    start_time = time.time()
    keyword_results = supabase.table('team_member_data').select('*').eq('is_active', True).ilike('title', f'%science%').limit(5).execute()
    keyword_time = (time.time() - start_time) * 1000
    
    print(f"Time: {keyword_time:.2f}ms")
    print(f"Results: {len(keyword_results.data) if keyword_results.data else 0}")
    if keyword_results.data:
        for i, result in enumerate(keyword_results.data[:3], 1):
            print(f"  {i}. {result.get('name', 'Unknown')} - {result.get('title', '')}")
    
    # Comparison
    print("\n--- Comparison ---")
    speedup = keyword_time / vector_time if vector_time > 0 else 0
    print(f"Vector search is {speedup:.2f}x {'faster' if speedup > 1 else 'slower'}")
    print(f"Vector search found {len(vector_results)} results vs {len(keyword_results.data) if keyword_results.data else 0} for keyword search")


def test_coursework_search():
    """Test coursework search if data exists"""
    print("\n" + "=" * 60)
    print("Test 6: Coursework Search")
    print("=" * 60)
    
    vector_service = get_vector_search_service()
    
    test_query = "assignment homework"
    
    print(f"\nQuery: '{test_query}'")
    
    start_time = time.time()
    results = vector_service.search_coursework(test_query, limit=3, threshold=0.6)
    elapsed = (time.time() - start_time) * 1000
    
    if results:
        print(f"✅ Found {len(results)} results in {elapsed:.2f}ms")
        for i, result in enumerate(results, 1):
            title = result.get('title', 'Unknown')
            similarity = result.get('similarity', 0)
            print(f"  {i}. {title[:60]}... (similarity: {similarity:.2f})")
    else:
        print(f"ℹ️ No coursework data found (this is normal if no Google Classroom data is synced)")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Vector Search Test Suite")
    print("=" * 60)
    
    try:
        # Test 1: Semantic similarity
        test_semantic_similarity()
        
        # Test 2: Person name queries
        test_person_name_queries()
        
        # Test 3: Role-based queries
        test_role_based_queries()
        
        # Test 4: Web content search
        test_web_content_search()
        
        # Test 5: Performance comparison
        compare_with_keyword_search()
        
        # Test 6: Coursework search
        test_coursework_search()
        
        print("\n" + "=" * 60)
        print("✅ All tests completed")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()





