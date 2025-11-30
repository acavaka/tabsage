# Audio Podcast Generation (NotebookLM-style)

## Overview

Implemented capability to convert one or multiple articles into audio podcast, similar to Google NotebookLM Audio Overview. The system creates a podcast where two AI hosts discuss article content.

## Technologies

### Google Cloud Text-to-Speech API

Uses **Google Cloud Text-to-Speech API** for speech synthesis:

- Russian language support (ru-RU)
- Male and female voices
- Speech rate adjustment (0.25 - 4.0)
- MP3 format saving
- SSML support for intonation control

**Installation:**
```bash
pip install google-cloud-texttospeech
```

**Configuration:**
```bash
export TTS_PROVIDER=google_cloud  # Default
# or
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
```

## Architecture

### Components

1. **Podcast Generator** (`src/tabsage/tools/podcast_generator.py`)
   - `generate_podcast_from_articles()` - main function
   - Support for one or multiple articles
   - Article search by topic

2. **TTS Integration** (`src/tabsage/tools/tts.py`)
   - `synthesize_speech()` - speech synthesis via Google Cloud TTS
   - `batch_synthesize()` - batch synthesis

3. **Telegram Bot** (`src/tabsage/bot/telegram_bot.py`)
   - `/audio` command for podcast generation
   - Support for article URLs or topic

## Podcast Generation Process

1. **Get Articles**
   - By URL (if specified)
   - By topic (if topic specified)

2. **Generate Script**
   - Uses `Scriptwriter Agent`
   - Creates structured script with segments

3. **Generate TTS Prompts**
   - Uses `Audio Producer Agent`
   - Creates prompts for each segment

4. **Audio Synthesis**
   - Each segment synthesized via Google Cloud TTS
   - Combine segments into one file

5. **Post-processing**
   - Volume normalization (optional)
   - Save to persistent storage

## Usage

### Via Telegram Bot

**By topic:**
```
/audio microservices
```

**By article URLs:**
```
/audio https://habr.com/ru/articles/519982/ https://habr.com/ru/articles/658157/
```

**Text commands:**
```
voice articles about microservices
create podcast from these articles
```

### Programmatically

```python
from tabsage.tools.podcast_generator import generate_podcast_from_articles

# By topic
result = await generate_podcast_from_articles(
    topic="microservices",
    session_id="my_session",
    episode_id="podcast_001"
)

# By URL
result = await generate_podcast_from_articles(
    article_urls=[
        "https://habr.com/ru/articles/519982/",
        "https://habr.com/ru/articles/658157/"
    ],
    session_id="my_session",
    episode_id="podcast_002"
)

if result["status"] == "success":
    audio_path = result["audio_path"]
    duration = result["duration_seconds"]
    print(f"Podcast ready: {audio_path} ({duration}s)")
```

## Result

Function returns:

```python
{
    "status": "success",
    "audio_path": "/tmp/podcasts/podcast_123.mp3",
    "duration_seconds": 300.5,
    "script": {...},  # Full script from Scriptwriter Agent
    "articles_used": ["url1", "url2"],
    "segments_count": 5,
    "tts_prompts_count": 5
}
```

## Voice Configuration

The following voices are available in Google Cloud TTS for Russian:

- **Male:**
  - `ru-RU-Standard-A` (default)
  - `ru-RU-Standard-B`
  - `ru-RU-Wavenet-A`
  - `ru-RU-Wavenet-B`

- **Female:**
  - `ru-RU-Standard-C`
  - `ru-RU-Standard-D`
  - `ru-RU-Wavenet-C`
  - `ru-RU-Wavenet-D`

Usage in code:
```python
from tabsage.tools.tts import synthesize_speech

result = synthesize_speech(
    text="Hello, this is test text",
    voice="ru-RU-Standard-C",  # Female voice
    speed=1.0,
    output_path="/tmp/test.mp3"
)
```

## Limitations

- **Text length:** Google Cloud TTS has limit of ~5000 characters per request
- **Cost:** ~$4 per 1 million characters (first 4 million free)
- **Speed:** Synthesis of one segment takes ~1-2 seconds

## Future Improvements

- [ ] Upload audio to Cloud Storage
- [ ] Background music support
- [ ] Sound effects
- [ ] Multiple voices (dialogue)
- [ ] Long text optimization (splitting into parts)

## Usage Examples

### Example 1: Podcast by Topic

```python
# User sends in Telegram:
"/audio microservices"

# System:
# 1. Searches articles by topic "microservices" in Firestore
# 2. Generates podcast script
# 3. Synthesizes audio
# 4. Sends MP3 file to user
```

### Example 2: Podcast from Specific Articles

```python
# User sends in Telegram:
"/audio https://habr.com/ru/articles/519982/ https://habr.com/ru/articles/658157/"

# System:
# 1. Gets articles by URL from Firestore
# 2. Generates script based on these articles
# 3. Synthesizes audio
# 4. Sends MP3 file to user
```

## Troubleshooting

### Error: "google-cloud-texttospeech not installed"

**Solution:**
```bash
pip install google-cloud-texttospeech
```

### Error: "Authentication failed"

**Solution:**
```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
# or
gcloud auth application-default login
```

### Error: "Article not found"

**Solution:**
- Make sure articles were processed via `/process_url` or URL sending
- Check that Firestore is configured (`KG_PROVIDER=firestore`)

### Error: "No TTS prompts generated"

**Solution:**
- Check that `Audio Producer Agent` works correctly
- Make sure `Scriptwriter Agent` generates segments

## Related Components

- **Scriptwriter Agent** - script generation
- **Audio Producer Agent** - TTS prompt creation
- **Google Cloud TTS** - speech synthesis
- **Firestore** - article storage
- **Telegram Bot** - user interface

