# Social Media Harvest Workflow

## Purpose
Harvest content from social media platforms (YouTube, Instagram, LinkedIn, Twitter/X).

## Supported Platforms

### YouTube
- **Transcript Extraction** (3-path waterfall):
  1. youtube-transcript-api (instant, no download)
  2. yt-dlp + ffmpeg audio → Whisper ASR (fallback)
  3. yt-dlp + OpenCV frame extraction → Vision model (last resort)
- **Metadata**: title, description, duration, view count, tags
- **VAD Gate**: Check voice activity before Whisper; music-only reels get `Audio: Music/Non-vocal` label

### Instagram
- **Method**: instagrapi with session cookies
- **Content**: post metadata, caption, media URLs
- **Rate Limit**: 30 requests/minute

### LinkedIn
- **Method**: linkedin-api with cookies
- **Content**: post text, reactions, company info
- **Rate Limit**: 20 requests/minute

### Twitter/X
- **Method**: Twitter API v2 (bearer token for read)
- **Content**: tweet text, media, engagement metrics
- **Rate Limit**: 180 requests/15 min (free tier)

## Workflow Steps

### 1. URL Validation
- Validate URL format for target platform
- Extract content ID from URL

### 2. Authentication
- Check for valid authentication tokens
- Refresh tokens if needed
- Fall back to demo mode if unauthenticated

### 3. Content Extraction
- Route to appropriate extractor based on platform
- Execute extraction with retry logic

### 4. Sanitization
- Scan extracted content for prompt injection
- Clean and escape content

### 5. Output Formatting
- Format as Markdown or JSON
- Include metadata

### 6. Storage
- Save to session history
- Optionally save media files

## Error Handling
- Auth expired: trigger re-authentication
- Rate limited: implement backoff
- Content unavailable: return partial or error
- CAPTCHA: notify user

## Compliance
- Respect platform Terms of Service
- Use authenticated sessions, not public scraping
- Implement rate limiting
- Personal research use only
