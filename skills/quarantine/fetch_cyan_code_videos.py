import requests

def fetch_cyan_code_videos(api_key, max_results=5):
    """
    Fetches the latest videos from the @cyan_code YouTube channel.
    
    Args:
        api_key (str): Your Google API Key for YouTube Data API v3.
        max_results (int): Number of recent videos to retrieve.
        
    Returns:
        list: A list of dictionaries containing video titles and URLs.
    """
    # Step 1: Find the Channel ID for @cyan_code
    search_url = "https://www.googleapis.com/youtube/v3/search"
    search_params = {
        "part": "snippet",
        "q": "@cyan_code",
        "type": "channel",
        "key": api_key
    }
    
    try:
        search_response = requests.get(search_url, params=search_params).json()
        if not search_response.get("items"):
            return "Could not find the channel @cyan_code."
        
        channel_id = search_response["items"][0]["snippet"]["channelId"]
        
        # Step 2: Fetch the latest videos from that channel
        video_url = "https://www.googleapis.com/youtube/v3/search"
        video_params = {
            "part": "snippet",
            "channelId": channel_id,
            "maxResults": max_results,
            "order": "date",
            "type": "video",
            "key": api_key
        }
        
        video_response = requests.get(video_url, params=video_params).json()
        videos = []
        
        for item in video_response.get("items", []):
            title = item["snippet"]["title"]
            video_id = item["id"]["videoId"]
            url = f"https://www.youtube.com/watch?v={video_id}"
            videos.append({"title": title, "url": url})
            
        return videos

    except Exception as e:
        return f"An error occurred: {str(e)}"

# Example usage:
# results = fetch_cyan_code_videos("YOUR_API_KEY_HERE")
# print(results)