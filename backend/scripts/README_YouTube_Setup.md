# YouTube Video Integration Setup Guide

## 🔑 Getting Your YouTube API Key

### Step 1: Create Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Sign in with the Google account that manages the Prakriti School YouTube channel
3. Create a new project or select existing one
4. Name it "Prakriti School Chatbot"

### Step 2: Enable YouTube Data API
1. Go to "APIs & Services" → "Library"
2. Search for "YouTube Data API v3"
3. Click "Enable"

### Step 3: Create API Key
1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "API Key"
3. Copy the generated API key
4. (Optional) Restrict the key to YouTube Data API v3 for security

### Step 4: Get Channel Information
- **Channel Username**: `@Prakritischool` (from the URL)
- **Channel ID**: Will be found automatically by the script

## 🚀 Running the Video Database Update

### Option 1: Using Channel Username (Easiest)
```bash
cd backend/scripts
python update_video_database.py --channel @Prakritischool --api-key YOUR_API_KEY
```

### Option 2: Using Channel ID
```bash
cd backend/scripts
python update_video_database.py --channel UCxxxxxxxxxxxxxxxxxxxxxx --api-key YOUR_API_KEY
```

### Parameters
- `--channel`: YouTube channel username (e.g., @Prakritischool) or channel ID
- `--api-key`: Your YouTube Data API key
- `--max-results`: Maximum videos to fetch (default: 50)
- `--output`: Output file name (default: video_database.py)

## 📝 After Running the Script

1. The script will generate a `video_database.py` file
2. Copy the content from this file
3. Replace the `VIDEO_DATABASE` in `backend/app/agents/youtube_intent_classifier.py`
4. Restart your backend server

## 🔧 Troubleshooting

### "Channel not found" Error
- Make sure the channel username is correct: `@Prakritischool`
- Verify the channel is public
- Check that your API key has YouTube Data API v3 enabled

### "API key invalid" Error
- Verify your API key is correct
- Make sure YouTube Data API v3 is enabled
- Check if there are any API restrictions

### "Quota exceeded" Error
- YouTube API has daily quotas
- Wait 24 hours or request quota increase
- Reduce `--max-results` parameter

## 📊 Expected Output

The script will:
1. Find the channel ID automatically
2. Fetch video information (title, description, thumbnail)
3. Categorize videos by content (gardening, arts, sports, etc.)
4. Generate Python code for the video database
5. Save to `video_database.py`

## 🎯 Next Steps

1. Run the script with your API key
2. Copy the generated code to `youtube_intent_classifier.py`
3. Test the chatbot with video queries like:
   - "Show me gardening videos"
   - "I want to see art exhibitions"
   - "What sports programs do you have?"
