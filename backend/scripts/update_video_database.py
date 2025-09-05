#!/usr/bin/env python3
"""
Script to update the video database with real YouTube video IDs from Prakriti School channel.
This script helps populate the VIDEO_DATABASE with actual video information.

To use this script:
1. Get the YouTube channel ID for @Prakritischool
2. Use YouTube Data API to fetch video information
3. Update the VIDEO_DATABASE in youtube_intent_classifier.py

Example usage:
python update_video_database.py --channel-id YOUR_CHANNEL_ID --api-key YOUR_YOUTUBE_API_KEY
"""

import argparse
import requests
import json
from typing import List, Dict, Any

def fetch_channel_videos(channel_identifier: str, api_key: str, max_results: int = 50) -> List[Dict[str, Any]]:
    """
    Fetch videos from a YouTube channel using YouTube Data API v3
    channel_identifier can be either channel ID or channel username (e.g., @Prakritischool)
    """
    base_url = "https://www.googleapis.com/youtube/v3"
    
    # Determine if it's a channel ID or username
    if channel_identifier.startswith('@'):
        # It's a username, search for the channel
        search_url = f"{base_url}/search"
        search_params = {
            'part': 'snippet',
            'q': channel_identifier,
            'type': 'channel',
            'maxResults': 1,
            'key': api_key
        }
        
        response = requests.get(search_url, params=search_params)
        search_data = response.json()
        
        if 'items' not in search_data or not search_data['items']:
            print(f"Error: Channel {channel_identifier} not found")
            return []
        
        channel_id = search_data['items'][0]['id']['channelId']
        print(f"Found channel ID: {channel_id}")
    else:
        channel_id = channel_identifier
    
    # Get the uploads playlist ID
    channel_url = f"{base_url}/channels"
    channel_params = {
        'part': 'contentDetails',
        'id': channel_id,
        'key': api_key
    }
    
    response = requests.get(channel_url, params=channel_params)
    channel_data = response.json()
    
    if 'items' not in channel_data or not channel_data['items']:
        print(f"Error: Channel {channel_id} not found")
        return []
    
    uploads_playlist_id = channel_data['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    
    # Get videos from the uploads playlist
    playlist_url = f"{base_url}/playlistItems"
    playlist_params = {
        'part': 'snippet',
        'playlistId': uploads_playlist_id,
        'maxResults': max_results,
        'key': api_key
    }
    
    response = requests.get(playlist_url, params=playlist_params)
    playlist_data = response.json()
    
    videos = []
    for item in playlist_data.get('items', []):
        video_info = {
            'video_id': item['snippet']['resourceId']['videoId'],
            'title': item['snippet']['title'],
            'description': item['snippet']['description'][:200] + '...' if len(item['snippet']['description']) > 200 else item['snippet']['description'],
            'thumbnail_url': item['snippet']['thumbnails']['high']['url'],
            'published_at': item['snippet']['publishedAt']
        }
        videos.append(video_info)
    
    return videos

def categorize_video(video: Dict[str, Any]) -> str:
    """
    Categorize a video based on its title and description
    """
    title_lower = video['title'].lower()
    desc_lower = video['description'].lower()
    text = f"{title_lower} {desc_lower}"
    
    # Define category keywords
    categories = {
        'gardening': ['garden', 'plant', 'vegetable', 'compost', 'sustainable', 'organic', 'farming', 'agriculture'],
        'arts': ['art', 'music', 'dance', 'painting', 'drawing', 'creative', 'exhibition', 'performance', 'theater'],
        'sports': ['sport', 'athletic', 'fitness', 'competition', 'game', 'physical', 'exercise', 'tournament'],
        'science': ['science', 'experiment', 'lab', 'stem', 'research', 'innovation', 'technology', 'project'],
        'mindfulness': ['mindfulness', 'meditation', 'wellness', 'mental', 'relaxation', 'yoga', 'peace', 'calm'],
        'campus_tour': ['campus', 'tour', 'facility', 'building', 'infrastructure', 'environment', 'school', 'visit']
    }
    
    # Count keyword matches for each category
    category_scores = {}
    for category, keywords in categories.items():
        score = sum(1 for keyword in keywords if keyword in text)
        category_scores[category] = score
    
    # Return the category with the highest score, or 'general' if no matches
    if category_scores:
        best_category = max(category_scores, key=category_scores.get)
        if category_scores[best_category] > 0:
            return best_category
    
    return 'general'

def generate_video_database_code(videos: List[Dict[str, Any]]) -> str:
    """
    Generate Python code for the VIDEO_DATABASE
    """
    # Group videos by category
    categorized_videos = {}
    for video in videos:
        category = categorize_video(video)
        if category not in categorized_videos:
            categorized_videos[category] = []
        categorized_videos[category].append(video)
    
    # Generate the code
    code = "VIDEO_DATABASE = {\n"
    
    for category, video_list in categorized_videos.items():
        code += f'    "{category}": [\n'
        for video in video_list[:3]:  # Limit to 3 videos per category
            code += f"""        YouTubeVideo(
            video_id="{video['video_id']}",
            title="{video['title'].replace('"', '\\"')}",
            description="{video['description'].replace('"', '\\"')}",
            category="{category}",
            tags=["{category}", "prakriti", "school"],
            duration="0:00",  # You may want to fetch this separately
            thumbnail_url="{video['thumbnail_url']}"
        ),\n"""
        code += "    ],\n"
    
    code += "}\n"
    return code

def main():
    parser = argparse.ArgumentParser(description='Update video database with real YouTube videos')
    parser.add_argument('--channel', required=True, help='YouTube channel ID or username (e.g., @Prakritischool)')
    parser.add_argument('--api-key', required=True, help='YouTube Data API key')
    parser.add_argument('--max-results', type=int, default=50, help='Maximum number of videos to fetch')
    parser.add_argument('--output', default='video_database.py', help='Output file for the generated code')
    
    args = parser.parse_args()
    
    print(f"Fetching videos from channel {args.channel}...")
    videos = fetch_channel_videos(args.channel, args.api_key, args.max_results)
    
    if not videos:
        print("No videos found. Please check your channel ID and API key.")
        return
    
    print(f"Found {len(videos)} videos. Categorizing...")
    
    # Generate the database code
    code = generate_video_database_code(videos)
    
    # Write to file
    with open(args.output, 'w') as f:
        f.write(code)
    
    print(f"Video database code written to {args.output}")
    print("You can now copy this code to replace the VIDEO_DATABASE in youtube_intent_classifier.py")

if __name__ == "__main__":
    main()
