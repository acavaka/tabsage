"""
Audio Summary - audio narration of article summaries (like NotebookLM Audio Overview)

This module creates audio version of article summaries without podcast format.
Simply narrates key points, intents, values and trends from articles.
"""

import asyncio
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
import tempfile

from tools.kg_client import get_kg_instance
from tools.tts import synthesize_speech
from observability.logging import get_logger

logger = get_logger(__name__)


async def generate_audio_summary(
    article_urls: Optional[List[str]] = None,
    topic: Optional[str] = None,
    session_id: str = "audio_summary_session",
    episode_id: Optional[str] = None
) -> Dict[str, Any]:
    """Generates audio version of article summaries.
    
    Similar to NotebookLM Audio Overview - simply narrates summaries without podcast format.
    
    Args:
        article_urls: List of article URLs (if None, topic is used)
        topic: Topic to search articles (if article_urls not specified)
        session_id: Session ID
        episode_id: Episode ID
        
    Returns:
        Dictionary with results:
        {
            "status": "success",
            "audio_path": "/path/to/audio.mp3",
            "duration_seconds": 300.5,
            "articles_used": [...],
            "summary_text": "..."
        }
    """
    try:
        kg = get_kg_instance()
        
        articles = []
        if article_urls:
            logger.info(f"Processing {len(article_urls)} article URLs: {article_urls}")
            for url in article_urls:
                logger.info(f"Checking article: {url}")
                if hasattr(kg, 'get_article'):
                    article = kg.get_article(url)
                    if article:
                        logger.info(f"Article found in Firestore: {url}")
                        articles.append(article)
                    else:
                        logger.info(f"Article not found in Firestore: {url}, will process it first")
                        try:
                            from tools.web_scraper import scrape_url
                            from agents.ingest_agent import run_once as ingest_run_once
                            from agents.kg_builder_agent import run_once as kg_builder_run_once
                            from agents.summary_agent import run_once as summary_run_once
                            from schemas.models import IngestPayload, KGBuilderPayload
                            
                            logger.info(f"Step 1: Scraping article: {url}")
                            scraped = await asyncio.to_thread(scrape_url, url)
                            if scraped.get("status") != "success":
                                error_msg = scraped.get("error_message", "Unknown error")
                                logger.error(f"Failed to scrape article {url}: {error_msg}")
                                continue
                            
                            article_text = scraped.get("text", "")
                            title = scraped.get("title", "No title")
                            
                            logger.info(f"Scraped article: {title}, text length: {len(article_text)}")
                            
                            if not article_text:
                                logger.error(f"Empty text after scraping: {url}")
                                continue
                            
                            logger.info(f"Step 2: Running Ingest Agent for: {url}")
                            ingest_payload = IngestPayload(
                                raw_text=article_text,
                                metadata={"url": url, "title": title, "source": "audio_summary"},
                                session_id=session_id,
                                episode_id=episode_id or "audio_episode"
                            ).model_dump()
                            
                            import inspect
                            if inspect.iscoroutinefunction(ingest_run_once):
                                ingest_result = await ingest_run_once(ingest_payload)
                            else:
                                ingest_result = await asyncio.to_thread(ingest_run_once, ingest_payload)
                            
                            if "error_message" in ingest_result:
                                logger.error(f"Ingest failed for {url}: {ingest_result['error_message']}")
                                continue
                            
                            logger.info(f"Ingest completed: {len(ingest_result.get('chunks', []))} chunks")
                            
                            logger.info(f"Step 3: Running KG Builder Agent for: {url}")
                            kg_payload = KGBuilderPayload(
                                cleaned_text=ingest_result.get("cleaned_text", article_text),
                                chunks=ingest_result.get("chunks", []),
                                title=ingest_result.get("title", title),
                                language=ingest_result.get("language", "ru"),
                                metadata={"url": url, "title": title},
                                session_id=session_id,
                                episode_id=episode_id or "audio_episode"
                            ).model_dump()
                            
                            if inspect.iscoroutinefunction(kg_builder_run_once):
                                await kg_builder_run_once(kg_payload)
                            else:
                                await asyncio.to_thread(kg_builder_run_once, kg_payload)
                            logger.info(f"KG Builder completed for: {url}")
                            
                            logger.info(f"Step 4: Running Summary Agent for: {url}")
                            summary_result = await summary_run_once(
                                article_text=ingest_result.get("cleaned_text", article_text),
                                title=title,
                                url=url
                            )
                            logger.info(f"Summary completed for: {url}, summary length: {len(summary_result.get('summary', ''))}")
                            
                            article_data = {
                                "url": url,
                                "title": title,
                                "summary": summary_result.get("summary", ""),
                                "key_points": summary_result.get("key_points", []),
                                "intents": summary_result.get("intents", []),
                                "values": summary_result.get("values", []),
                                "trends": summary_result.get("trends", []),
                                "unusual_points": summary_result.get("unusual_points", []),
                                "processed_at": summary_result.get("processed_at")
                            }
                            
                            logger.info(f"Step 5: Saving article to Firestore: {url}")
                            if hasattr(kg, 'add_article'):
                                try:
                                    kg.add_article(article_data)
                                    logger.info(f"Article saved to Firestore: {url}")
                                except Exception as e:
                                    logger.warning(f"Failed to save to Firestore (non-critical): {e}")
                            
                            logger.info(f"Adding article to list: {url}, summary: {len(article_data.get('summary', ''))} chars")
                            articles.append(article_data)
                            logger.info(f"Article added successfully. Total articles: {len(articles)}")
                        except Exception as e:
                            import traceback
                            logger.error(f"Error processing article {url}: {e}")
                            logger.error(traceback.format_exc())
                            logger.warning(f"Trying to use basic article data for {url}")
                            try:
                                basic_article = {
                                    "url": url,
                                    "title": title if 'title' in locals() else "Article",
                                    "summary": f"Error processing: {str(e)}",
                                    "key_points": [],
                                    "intents": [],
                                    "values": [],
                                    "trends": [],
                                    "unusual_points": []
                                }
                                articles.append(basic_article)
                                logger.info(f"Added basic article data. Total articles: {len(articles)}")
                            except Exception as e2:
                                logger.error(f"Failed to add even basic article data: {e2}")
                                continue
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
            logger.error(f"No articles found or processed. URLs: {article_urls}, Topic: {topic}")
            return {
                "status": "error",
                "error_message": "No articles found or processed"
            }
        
        logger.info(f"Successfully processed {len(articles)} articles for audio summary")
        
        logger.info(f"Generating audio summary from {len(articles)} articles")
        
        summary_parts = []
        
        if len(articles) == 1:
            # Single article - simple summary
            article = articles[0]
            title = article.get("title", "Article")
            summary = article.get("summary", "")
            key_points = article.get("key_points", [])
            
            if summary and "Error processing" in summary:
                logger.error(f"Article has error summary: {summary}")
                return {
                    "status": "error",
                    "error_message": f"Error processing article: {summary}"
                }
            
            if not summary or len(summary.strip()) < 10:
                logger.warning(f"Article has empty or very short summary: {len(summary)} chars")
                return {
                    "status": "error",
                    "error_message": "Failed to generate summary for article"
                }
            
            summary_parts.append(f"Article: {title}")
            summary_parts.append("")
            summary_parts.append("Summary:")
            summary_parts.append(summary)
            
            if key_points:
                summary_parts.append("")
                summary_parts.append("Key points:")
                for i, point in enumerate(key_points[:5], 1):
                    summary_parts.append(f"{i}. {point}")
        else:
            # Multiple articles - overview of all
            summary_parts.append(f"Overview of {len(articles)} articles")
            summary_parts.append("")
            
            for idx, article in enumerate(articles, 1):
                title = article.get("title", f"Article {idx}")
                summary = article.get("summary", "")
                key_points = article.get("key_points", [])
                
                summary_parts.append(f"Article {idx}: {title}")
                summary_parts.append(summary)
                
                if key_points:
                    summary_parts.append("Key points:")
                    for point in key_points[:3]:  # Only first 3 for brevity
                        summary_parts.append(f"• {point}")
                
                summary_parts.append("")
        
        # Combine all parts
        full_summary_text = "\n".join(summary_parts)
        
        logger.info(f"Summary text length: {len(full_summary_text)} characters")
        
        # Split by sentences to avoid cutting words (Google TTS limit: 5000 bytes)
        max_chunk_size = 4000
        chunks = []
        current_chunk = ""
        
        sentences = full_summary_text.split('. ')
        for sentence in sentences:
            sentence_with_dot = sentence + '. '
            if len((current_chunk + sentence_with_dot).encode('utf-8')) <= max_chunk_size:
                current_chunk += sentence_with_dot
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence_with_dot
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        logger.info(f"Split summary into {len(chunks)} chunks for TTS")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_files = []
            total_duration = 0
            
            for i, chunk in enumerate(chunks):
                chunk_path = f"{temp_dir}/chunk_{i}.mp3"
                
                tts_result = synthesize_speech(
                    text=chunk,
                    voice="wavenet_female",  # WaveNet for better quality (more natural voice)
                    speed=1.0,
                    output_path=chunk_path
                )
                
                if tts_result.get("status") == "success":
                    audio_files.append(tts_result.get("audio_path"))
                    total_duration += tts_result.get("duration_seconds", 0)
                else:
                    logger.warning(f"TTS failed for chunk {i}: {tts_result.get('error_message')}")
            
            if not audio_files:
                return {
                    "status": "error",
                    "error_message": "No audio chunks generated"
                }
            
            # 5. Combine all chunks into one file
            final_audio_path = f"{temp_dir}/audio_summary_final.mp3"
            
            if len(audio_files) == 1:
                final_audio_path = audio_files[0]
            else:
                import shutil
                with open(final_audio_path, 'wb') as outfile:
                    for audio_file in audio_files:
                        if os.path.exists(audio_file):
                            with open(audio_file, 'rb') as infile:
                                shutil.copyfileobj(infile, outfile)
                
                logger.info(f"Combined {len(audio_files)} audio chunks")
            
            audio_path = final_audio_path
            duration_seconds = total_duration
            
            downloads_dir = Path.home() / "Downloads"
            if not downloads_dir.exists():
                downloads_dir = Path.home() / "Downloads"
            if not downloads_dir.exists():
                downloads_dir = Path("/tmp/podcasts")
            
            downloads_dir.mkdir(parents=True, exist_ok=True)
            persistent_path = downloads_dir / f"audio_summary_{episode_id or session_id}.mp3"
            
            import shutil
            if os.path.exists(audio_path):
                shutil.copy2(audio_path, str(persistent_path))
            else:
                return {
                    "status": "error",
                    "error_message": "Audio file not generated"
                }
            
            logger.info(f"Audio summary generated: {persistent_path} ({duration_seconds:.1f}s)")
            
            return {
                "status": "success",
                "audio_path": str(persistent_path),
                "duration_seconds": duration_seconds,
                "articles_used": [a.get("url") for a in articles],
                "summary_text": full_summary_text,
                "articles_count": len(articles)
            }
        
    except Exception as e:
        import traceback
        logger.error(f"Error generating audio summary: {e}")
        logger.debug(traceback.format_exc())
        return {
            "status": "error",
            "error_message": str(e)
        }

