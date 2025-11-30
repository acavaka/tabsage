"""
Podcast Generator - converting articles to audio podcast (like NotebookLM)

This module implements functionality to convert one or more articles
into audio podcast, similar to Google NotebookLM Audio Overview.

Process:
1. Gets articles from Firestore (by URL or topic)
2. Generates podcast script via Scriptwriter Agent
3. Creates audio via Audio Producer Agent + Google Cloud TTS
4. Saves audio file to Cloud Storage
5. Returns audio link
"""

import logging
import asyncio
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
import tempfile

from tools.kg_client import get_kg_instance
from agents.scriptwriter_agent import run_once as scriptwriter_run_once
from agents.audio_producer_agent import run_once as audio_producer_run_once
from tools.tts import batch_synthesize
from tools.audio_utils import normalize_audio, mix_audio
from schemas.models import ScriptwriterPayload, AudioProducerPayload, Topic
from observability.logging import get_logger

logger = get_logger(__name__)


async def generate_podcast_from_articles(
    article_urls: Optional[List[str]] = None,
    topic: Optional[str] = None,
    session_id: str = "podcast_session",
    episode_id: Optional[str] = None
) -> Dict[str, Any]:
    """Generates audio podcast from one or more articles.
    
    Similar to NotebookLM Audio Overview - creates podcast where two AI hosts
    discuss article content.
    
    Args:
        article_urls: List of article URLs (if None, topic is used)
        topic: Topic to search articles (if article_urls not specified)
        session_id: Session ID
        episode_id: Podcast episode ID
        
    Returns:
        Dictionary with results:
        {
            "status": "success",
            "audio_path": "/path/to/podcast.mp3",
            "duration_seconds": 300.5,
            "script": {...},
            "articles_used": [...]
        }
    """
    try:
        kg = get_kg_instance()
        
        articles = []
        if article_urls:
            for url in article_urls:
                if hasattr(kg, 'get_article'):
                    article = kg.get_article(url)
                    if article:
                        articles.append(article)
                    else:
                        logger.warning(f"Article not found: {url}")
                else:
                    logger.warning("Firestore not available, cannot get articles by URL")
        elif topic:
            if hasattr(kg, 'search_articles_by_topic'):
                articles = kg.search_articles_by_topic(topic, limit=10)
            else:
                logger.warning("Firestore not available, cannot search by topic")
        else:
            return {
                "status": "error",
                "error_message": "Either article_urls or topic must be provided"
            }
        
        if not articles:
            return {
                "status": "error",
                "error_message": "No articles found"
            }
        
        logger.info(f"Generating podcast from {len(articles)} articles")
        
        articles_context = []
        for article in articles:
            articles_context.append({
                "url": article.get("url", ""),
                "title": article.get("title", ""),
                "summary": article.get("summary", ""),
                "key_points": article.get("key_points", [])
            })
        
        topic_name = topic or f"Discussion of {len(articles)} articles"
        articles_summary = "\n".join([
            f"- {a.get('title', 'No title')}: {a.get('summary', '')[:200]}..."
            for a in articles_context[:5]
        ])
        
        topic_obj = Topic(
            title=topic_name,
            why_it_matters=f"Podcast based on {len(articles)} articles:\n{articles_summary}",
            seed_nodes=[],
            difficulty="medium",
            estimated_length_minutes=15
        )
        
        scriptwriter_payload = ScriptwriterPayload(
            topic=topic_obj,
            target_audience="general",
            format="podcast",
            session_id=session_id,
            episode_id=episode_id or f"podcast_{hash(str(article_urls)) % 10000}"
        )
        
        script_result = await scriptwriter_run_once(scriptwriter_payload.dict())
        
        if "error_message" in script_result or script_result.get("status") == "error":
            return {
                "status": "error",
                "error_message": script_result.get("error_message", "Script generation failed")
            }
        
        segments = script_result.get("segments", [])
        full_script = script_result.get("full_script", "")
        
        if not segments:
            return {
                "status": "error",
                "error_message": "No segments in script"
            }
        
        audio_payload = AudioProducerPayload(
            segments=segments,
            full_script=full_script,
            session_id=session_id,
            episode_id=episode_id
        )
        
        audio_result = await audio_producer_run_once(audio_payload.dict())
        
        if "error_message" in audio_result or audio_result.get("status") == "error":
            return {
                "status": "error",
                "error_message": audio_result.get("error_message", "Audio production failed")
            }
        
        tts_prompts = audio_result.get("tts_prompts", [])
        
        if not tts_prompts:
            return {
                "status": "error",
                "error_message": "No TTS prompts generated"
            }
        
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_files = []
            
            for i, prompt in enumerate(tts_prompts):
                text = prompt.get("text", prompt.get("ssml", ""))
                voice = prompt.get("voice", "default")
                speed = prompt.get("speed", 1.0)
                
                output_path = f"{temp_dir}/segment_{i}.mp3"
                
                from tools.tts import synthesize_speech
                tts_result = synthesize_speech(
                    text=text,
                    voice=voice,
                    speed=speed,
                    output_path=output_path
                )
                
                if tts_result.get("status") == "success":
                    audio_files.append(tts_result["audio_path"])
                else:
                    logger.warning(f"TTS failed for segment {i}: {tts_result.get('error_message')}")
            
            if not audio_files:
                return {
                    "status": "error",
                    "error_message": "No audio files generated"
                }
            
            final_audio_path = f"{temp_dir}/podcast_final.mp3"
            
            try:
                import shutil
                from pathlib import Path
                
                if len(audio_files) == 1:
                    final_audio_path = audio_files[0]
                else:
                    try:
                        with open(final_audio_path, 'wb') as outfile:
                            for audio_file in audio_files:
                                if os.path.exists(audio_file):
                                    with open(audio_file, 'rb') as infile:
                                        shutil.copyfileobj(infile, outfile)
                        logger.info(f"Combined {len(audio_files)} audio files into {final_audio_path}")
                    except Exception as e:
                        logger.warning(f"Error combining audio files: {e}, using first file")
                        final_audio_path = audio_files[0] if audio_files else None
            except Exception as e:
                logger.warning(f"Error processing audio: {e}, using first file")
                final_audio_path = audio_files[0] if audio_files else None
            
            try:
                if os.path.exists(final_audio_path):
                    normalized_path = f"{temp_dir}/podcast_normalized.mp3"
                    normalize_result = normalize_audio(final_audio_path, normalized_path)
                    
                    if normalize_result.get("status") == "success" and os.path.exists(normalized_path):
                        final_audio_path = normalized_path
            except Exception as e:
                logger.debug(f"Audio normalization skipped: {e}")
            
            if not os.path.exists(final_audio_path):
                return {
                    "status": "error",
                    "error_message": "TTS not configured. Please install google-cloud-texttospeech: pip install google-cloud-texttospeech"
                }
            
            # TODO: Upload to Cloud Storage
            persistent_path = f"/tmp/podcasts/podcast_{episode_id or session_id}.mp3"
            Path(persistent_path).parent.mkdir(parents=True, exist_ok=True)
            
            import shutil
            shutil.copy2(final_audio_path, persistent_path)
            
            total_duration = 0
            for prompt in tts_prompts:
                text = prompt.get("text", prompt.get("ssml", ""))
                words = len(text.split())
                duration = (words / 150) * 60 / prompt.get("speed", 1.0)
                total_duration += duration
            
            logger.info(f"Podcast generated: {persistent_path} ({total_duration:.1f}s)")
            
            return {
                "status": "success",
                "audio_path": persistent_path,
                "duration_seconds": total_duration,
                "script": script_result,
                "articles_used": [a.get("url") for a in articles],
                "segments_count": len(segments),
                "tts_prompts_count": len(tts_prompts)
            }
        
    except Exception as e:
        import traceback
        logger.error(f"Error generating podcast: {e}")
        logger.debug(traceback.format_exc())
        return {
            "status": "error",
            "error_message": str(e)
        }

