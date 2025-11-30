"""
Telegram Bot for TabSage - article processing and database search

This module implements Telegram bot which is the main interface
for user interaction with TabSage system.

Architecture:
- Uses python-telegram-bot library
- Integrated with all agents through their run_once functions
- Supports processing multiple URLs simultaneously
- Integrated with Firestore for search and storage

Main functions:
1. Article URL processing:
   - Parsing via web_scraper
   - Processing through Ingest → KG Builder → Summary pipeline
   - Saving to Firestore
   - Sending summary to user

2. Database search:
   - Using Intent Recognition Agent to understand query
   - Search via Firestore with relevance
   - Sending results with links

3. Commands:
   - /start, /help - help
   - /stats - graph statistics
   - /graph - graph information
   - /export_graph - export graph to GraphML

Features:
- Processing multiple URLs in one message
- Finding related articles via graph
- Duplicate check before processing
- Formatted messages with Markdown
"""

import asyncio
import logging
import os
from typing import Dict, Any, Optional, List

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from telegram.error import TimedOut, NetworkError

from agents.intent_agent import recognize_intent, UserIntent
from tools.web_scraper import scrape_url
from agents.ingest_agent import run_once as ingest_run_once
from agents.kg_builder_agent import run_once as kg_builder_run_once
from agents.summary_agent import run_once as summary_run_once
from schemas.models import IngestPayload, KGBuilderPayload
from core.config import get_config, TELEGRAM_BOT_TOKEN
from tools.kg_client import get_kg_instance
from memory.shared_memory import get_shared_memory
from workflows.resumable import create_article_processing_workflow, WorkflowStatus
from tools.podcast_generator import generate_podcast_from_articles
from pathlib import Path
import os

logger = logging.getLogger(__name__)


def format_summary_message(summary_data: Dict[str, Any], related_articles: Optional[List[Dict[str, Any]]] = None) -> str:
    """Formats summary for sending to Telegram"""
    title = summary_data.get("title", "No title")
    summary = summary_data.get("summary", "")
    key_points = summary_data.get("key_points", [])
    intents = summary_data.get("intents", [])
    values = summary_data.get("values", [])
    url = summary_data.get("url", "")
    
    message = f"📄 *{title}*\n\n"
    
    if summary:
        message += f"📝 *Резюме:*\n{summary}\n\n"
    
    if key_points:
        message += "🔑 *Ключевые моменты:*\n"
        for point in key_points[:5]:  # Limit to 5
            message += f"• {point}\n"
        message += "\n"
    
    if intents:
        message += "💡 *Интенты:*\n"
        for intent in intents[:3]:
            message += f"• {intent}\n"
        message += "\n"
    
    if values:
        message += "⭐ *Ценности:*\n"
        for value in values[:3]:
            message += f"• {value}\n"
        message += "\n"
    
    if url:
        message += f"🔗 [Оригинальная статья]({url})\n\n"
    
    if related_articles:
        message += "📚 *Похожие материалы:*\n"
        for i, related in enumerate(related_articles[:3], 1):
            related_title = related.get("title", "Без названия")
            related_url = related.get("url", "")
            if related_url:
                message += f"{i}. [{related_title}]({related_url})\n"
        message += "\n"
    
    message += "🎧 Запросить аудио версию: /audio"
    
    return message


async def process_article_url(url: str, chat_id: int, bot, session_id: Optional[str] = None) -> Dict[str, Any]:
    """Processes article by URL using Shared Memory.
    
    Args:
        url: Article URL to process
        chat_id: Chat ID for sending messages
        bot: Telegram bot instance
        session_id: Session ID for shared memory (if None, generated automatically)
        
    Returns:
        Dictionary with processing results
    """
    try:
        shared_mem = get_shared_memory()
        if session_id is None:
            session_id = f"telegram_{chat_id}_{hash(url)}"
        namespace = f"session_{session_id}"
        
        # Duplicate check (if Firestore)
        kg = get_kg_instance()
        if hasattr(kg, 'get_article'):
            existing = kg.get_article(url)
            if existing:
                await bot.send_message(
                    chat_id=chat_id,
                    text="ℹ️ Статья уже была обработана ранее. Показываю сохраненное резюме..."
                )
                return existing
        
        # 1. Download (with timeout)
        await bot.send_message(
            chat_id=chat_id,
            text=f"📥 Скачиваю статью..."
        )
        
        try:
            scraped = await asyncio.wait_for(
                asyncio.to_thread(scrape_url, url, timeout=90),  # Pass timeout to scraper
                timeout=120  # 2 minutes for download (increased for slow sites and retries)
            )
        except asyncio.TimeoutError:
            return {"error": "Таймаут при скачивании статьи. URL может быть недоступен или статья слишком большая."}
        if scraped.get("status") != "success":
            return {"error": scraped.get("error_message", "Download error")}
        
        article_text = scraped.get("text", "")
        title = scraped.get("title", "No title")
        
        if not article_text:
            return {"error": "Пустой текст после парсинга"}
        
        # 2. Ingest (with timeout)
        await bot.send_message(
            chat_id=chat_id,
            text="🔄 Обрабатываю текст..."
        )
        
        try:
            ingest_result = await asyncio.wait_for(
                ingest_run_once(IngestPayload(
                    raw_text=article_text,  # Process entire text (up to 100K characters)
                    metadata={"url": url, "title": title, "source": "telegram"},
                    session_id="telegram_session",
                    episode_id="telegram_episode"
                ).model_dump()),
                timeout=300  # 5 minutes for ingest (increased for large articles and LLM processing)
            )
        except asyncio.TimeoutError:
            return {"error": "Таймаут при обработке текста. Статья слишком большая или LLM обрабатывает медленно."}
        
        if "error_message" in ingest_result:
            return {"error": f"Ошибка обработки: {ingest_result['error_message']}"}
        
        shared_mem.set("ingest_result", ingest_result, namespace=namespace, ttl_seconds=3600)
        shared_mem.set("article_text", article_text, namespace=namespace, ttl_seconds=3600)
        shared_mem.set("article_title", title, namespace=namespace, ttl_seconds=3600)
        shared_mem.set("article_url", url, namespace=namespace, ttl_seconds=3600)
        
        kg_payload = KGBuilderPayload(
            chunks=ingest_result.get("chunks", []),  # Process all chunks
            title=ingest_result.get("title", ""),
            language=ingest_result.get("language", ""),
            session_id="telegram_session",
            episode_id="telegram_episode",
            metadata={"url": url}
        )
        
        asyncio.create_task(kg_builder_run_once(kg_payload.model_dump()))
        
        # 4. Summary (with timeout)
        await bot.send_message(
            chat_id=chat_id,
            text="📝 Генерирую резюме..."
        )
        
        try:
            summary_result = await asyncio.wait_for(
                summary_run_once(
                    article_text=article_text,  # Process entire text (up to 50K characters for summary)
                    title=title,
                    url=url
                ),
                timeout=240  # 4 minutes for summary (increased for LLM processing)
            )
        except asyncio.TimeoutError:
            return {"error": "Таймаут при генерации резюме. Статья слишком большая или LLM обрабатывает медленно."}
        
        shared_mem.set("summary_result", summary_result, namespace=namespace, ttl_seconds=3600)
        
        # 5. Save article to Firestore
        try:
            if hasattr(kg, 'add_article'):  # Firestore
                article_data = {
                    "url": url,
                    "title": title,
                    "summary": summary_result.get("summary", ""),
                    "key_points": summary_result.get("key_points", []),
                    "intents": summary_result.get("intents", []),
                    "values": summary_result.get("values", []),
                    "trends": summary_result.get("trends", []),
                    "unusual_points": summary_result.get("unusual_points", []),
                    "ingest_result": ingest_result
                }
                kg.add_article(article_data)
                logger.info(f"Article saved to Firestore: {url}")
                
                if hasattr(kg, 'find_related_articles'):
                    related = kg.find_related_articles(url, limit=3)
                    summary_result["related_articles"] = related
        except Exception as e:
            logger.warning(f"Failed to save article to Firestore: {e}")
        
        return summary_result
        
    except Exception as e:
        logger.error(f"Error processing article: {e}", exc_info=True)
        return {"error": str(e)}


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles user messages"""
    user_message = update.message.text
    chat_id = update.effective_chat.id
    context._chat_id = chat_id
    
    try:
        # Recognize intent
        intent_result = await recognize_intent(user_message)
        intent = intent_result.get("intent", UserIntent.UNKNOWN)
        
        if intent == UserIntent.PROCESS_URL:
            # URL processing (can be multiple)
            url_text = intent_result.get("parameters", {}).get("url") or user_message.strip()
            
            # Extract all URLs from message
            import re
            url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
            urls = url_pattern.findall(url_text)
            
            if not urls:
                urls = [url_text]
            
            if len(urls) == 1:
                try:
                    result = await asyncio.wait_for(
                        process_article_url(urls[0], chat_id, context.bot),
                        timeout=600  # 10 minutes total timeout (increased for Cloud Run)
                    )
                except asyncio.TimeoutError:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="⏱️ Обработка заняла слишком много времени. Попробуйте позже или обработайте статью по частям."
                    )
                    return
                except Exception as e:
                    logger.error(f"Error in handle_message: {e}", exc_info=True)
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"❌ Произошла ошибка: {str(e)}"
                    )
                    return
                
                if "error" in result:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"❌ Ошибка: {result['error']}"
                    )
                else:
                    message = format_summary_message(result)
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=message,
                        parse_mode="Markdown",
                        disable_web_page_preview=False
                    )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"📚 Найдено {len(urls)} URL. Обрабатываю параллельно..."
                )
                
                tasks = []
                for i, url in enumerate(urls, 1):
                    task = asyncio.create_task(
                        process_article_url(url, chat_id, context.bot)
                    )
                    tasks.append((i, url, task))
                
                # Send notification about processing start
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"🚀 Начал параллельную обработку {len(urls)} статей..."
                )
                
                successful = 0
                failed = 0
                results_summary = []
                
                try:
                    task_results = await asyncio.gather(
                        *[task for _, _, task in tasks],
                        return_exceptions=True  # Don't interrupt on error in one task
                    )
                except Exception as e:
                    logger.error(f"Error in gather: {e}", exc_info=True)
                    task_results = [e] * len(tasks)
                
                for idx, ((i, url, _), result) in enumerate(zip(tasks, task_results)):
                    try:
                        if isinstance(result, Exception):
                            if isinstance(result, asyncio.TimeoutError):
                                failed += 1
                                await context.bot.send_message(
                                    chat_id=chat_id,
                                    text=f"⏱️ Таймаут при обработке {i}/{len(urls)}. Статья слишком большая."
                                )
                            else:
                                failed += 1
                                logger.error(f"Error processing URL {i}: {result}", exc_info=True)
                                await context.bot.send_message(
                                    chat_id=chat_id,
                                    text=f"❌ Ошибка при обработке {i}/{len(urls)}: {str(result)}"
                                )
                            continue
                        
                        if "error" in result:
                            failed += 1
                            await context.bot.send_message(
                                chat_id=chat_id,
                                text=f"❌ Ошибка при обработке {i}/{len(urls)}: {result['error']}"
                            )
                        else:
                            successful += 1
                            related = result.get("related_articles", [])
                            message = format_summary_message(result, related_articles=related)
                            
                            # Send summary
                            await context.bot.send_message(
                                chat_id=chat_id,
                                text=f"✅ Article {i}/{len(urls)}:\n\n{message}",
                                parse_mode="Markdown",
                                disable_web_page_preview=False
                            )
                            
                            results_summary.append({
                                "index": i,
                                "url": url,
                                "title": result.get("title", "No title")
                            })
                    except Exception as e:
                        failed += 1
                        logger.error(f"Error processing result for URL {i}: {e}", exc_info=True)
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=f"❌ Error processing result {i}/{len(urls)}: {str(e)}"
                        )
                
                # Summary with brief summary
                summary_text = f"✅ Processing completed!\n\n"
                summary_text += f"📊 Statistics:\n"
                summary_text += f"• Successful: {successful} ✅\n"
                summary_text += f"• Errors: {failed} ❌\n\n"
                
                if results_summary:
                    summary_text += "📚 Processed articles:\n"
                    for item in results_summary:
                        summary_text += f"{item['index']}. {item['title'][:50]}...\n"
                
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=summary_text
                )
                return
            
                # This block already processed above for multiple URLs
                pass
        
        elif intent == UserIntent.SEARCH_DATABASE:
            # Database search via Firestore (with improved relevant search)
            query = intent_result.get("parameters", {}).get("query", user_message)
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🔍 Ищу в базе данных: '{query}'..."
            )
            
            try:
                kg = get_kg_instance()
                if hasattr(kg, 'search_articles_by_topic'):
                    results = kg.search_articles_by_topic(query, limit=5)
                    
                    if results:
                        message = f"📚 Найдено {len(results)} статей:\n\n"
                        for i, article in enumerate(results, 1):
                            title = article.get("title", "No title")
                            url = article.get("url", "")
                            summary = article.get("summary", "")[:150] + "..." if len(article.get("summary", "")) > 150 else article.get("summary", "")
                            relevance = article.get("relevance_score", 0)
                            
                            message += f"{i}. *{title}*\n"
                            if summary:
                                message += f"   _{summary}_\n"
                            if relevance > 0:
                                message += f"   ⭐ Релевантность: {relevance}\n"
                            if url:
                                message += f"   [Читать]({url})\n"
                            message += "\n"
                        
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=message,
                            parse_mode="Markdown",
                            disable_web_page_preview=False
                        )
                    else:
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=f"❌ Ничего не найдено по запросу '{query}'"
                        )
                else:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text="⚠️ Поиск доступен только с Firestore. Установите KG_PROVIDER=firestore"
                    )
            except Exception as e:
                logger.error(f"Error searching database: {e}")
                await context.bot.send_message(
                    chat_id=chat_id,
                        text=f"❌ Ошибка поиска: {str(e)}"
                )
        
        elif intent == UserIntent.GENERATE_AUDIO:
            # Audio podcast generation (NotebookLM-style)
            await generate_audio_handler(update, context)
        
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text="🤔 Не понял запрос. Отправьте URL статьи для обработки или используйте команды:\n/search - поиск в базе данных\n/audio - генерация аудио"
            )
            
    except Exception as e:
        logger.error(f"Error handling message: {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ Произошла ошибка: {str(e)}"
        )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /start command"""
    await update.message.reply_text(
        "👋 Hello! I'm TabSage Bot.\n\n"
        "Send article URL, and I will:\n"
        "• Analyze it\n"
        "• Create summary with key points\n"
        "• Extract intents and values\n"
        "• Add to knowledge graph\n\n"
        "Commands:\n"
        "/search - database search\n"
        "/stats - graph statistics\n"
        "/help - help\n"
        "/audio - audio podcast generation"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /help command"""
    help_text = """📚 *Помощь TabSage Bot*

*Как использовать:*

1️⃣ *Обработать статью:*
   Просто отправь URL статьи:
   ```
   https://habr.com/ru/articles/519982/
   ```

2️⃣ *Поиск в базе данных:*
   Напиши запрос или используй /search:
   ```
   найти микросервисы
   поиск event-driven архитектура
   ```

3️⃣ *Статистика:*
   /stats - показывает статистику графа знаний

4️⃣ *Аудио подкаст (в стиле NotebookLM):*
   /audio [тема] - сгенерировать подкаст по теме
   /audio [URL1] [URL2] ... - сгенерировать подкаст из статей

*Примеры запросов:*
• Отправь URL → получи резюме
• "найти архитектура" → поиск в базе данных
• "все статьи про AI" → список статей по теме

*Возможности:*
• Все статьи сохраняются в граф знаний
• Можно искать по любым темам
• Ссылки на источники в каждом резюме"""
    
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /stats command"""
    try:
        logger.info("Getting graph stats...")
        kg = get_kg_instance()
        logger.info(f"KG instance type: {type(kg)}")
        logger.info(f"KG_PROVIDER: {os.getenv('KG_PROVIDER', 'not set')}")
        stats = kg.get_graph_stats()
        logger.info(f"Stats result: {stats}")
        
        stats_text = f"""📊 *Статистика графа знаний*

📄 Статей: {stats.get('articles_count', 0)}
🔷 Узлов: {stats.get('nodes_count', 0)}
🔗 Связей: {stats.get('edges_count', 0)}

*Типы сущностей:*
"""
        entity_types = stats.get('entity_types', {})
        for entity_type, count in sorted(entity_types.items(), key=lambda x: x[1], reverse=True)[:5]:
            stats_text += f"• {entity_type}: {count}\n"
        
        stats_text += "\n💾 Хранилище: "
        if hasattr(kg, 'project_id'):
            stats_text += f"Firestore ({kg.project_id})"
        else:
            stats_text += "В памяти"
        
        await update.message.reply_text(stats_text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        await update.message.reply_text(f"❌ Ошибка получения статистики: {str(e)}")


async def graph_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /graph command - graph export"""
    try:
        kg = get_kg_instance()
        snapshot = kg.get_snapshot(limit=100)
        
        # Form brief graph information
        nodes = snapshot.get("nodes", [])
        edges_count = snapshot.get("edges_count", 0)
        
        graph_text = f"""🗺️ *Граф знаний*

🔷 Узлов: {len(nodes)}
🔗 Связей: {edges_count}

*Топ-10 узлов по важности:*
"""
        for i, node in enumerate(nodes[:10], 1):
            name = node.get("canonical_name", "N/A")
            entity_type = node.get("type", "N/A")
            confidence = node.get("confidence", 0)
            graph_text += f"{i}. [{entity_type}] {name} ({confidence:.2f})\n"
        
        graph_text += "\n💡 Для полного экспорта используй: /export_graph"
        await update.message.reply_text(graph_text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error getting graph: {e}")
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")


async def export_graph_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /export_graph command - export graph to GraphML"""
    try:
        from tools.graph_export import export_to_graphml
        
        file_path = export_to_graphml()
        
        if file_path and os.path.exists(file_path):
            with open(file_path, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename="graph.graphml",
                    caption="📊 Экспорт графа знаний в GraphML"
                )
        else:
            await update.message.reply_text("❌ Ошибка экспорта графа")
    except Exception as e:
        logger.error(f"Error exporting graph: {e}")
        await update.message.reply_text(f"❌ Ошибка экспорта: {str(e)}")


async def generate_audio_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles audio summary generation from articles (NotebookLM-style)"""
    from tools.audio_summary import generate_audio_summary
    
    chat_id = update.effective_chat.id
    user_message = update.message.text
    
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text="🎙️ Генерирую аудио резюме (в стиле NotebookLM)..."
        )
        
        import re
        url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        urls = url_pattern.findall(user_message)
        
        if urls:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"📚 Найдено {len(urls)} статей. Создаю аудио резюме..."
            )
            
            result = await generate_audio_summary(
                article_urls=urls,
                session_id=f"telegram_{chat_id}",
                episode_id=f"audio_{hash(str(urls)) % 10000}"
            )
        else:
            # Search by topic
            topic = user_message.replace("/audio", "").replace("/podcast", "").strip()
            if not topic:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ Укажи тему или URL статей. Например:\n"
                         "/audio микросервисы\n"
                         "или\n"
                         "/audio https://habr.com/... https://habr.com/..."
                )
                return
            
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"🔍 Ищу статьи по теме '{topic}'..."
            )
            
            result = await generate_audio_summary(
                topic=topic,
                session_id=f"telegram_{chat_id}",
                episode_id=f"audio_{hash(topic) % 10000}"
            )
        
        if result.get("status") == "error":
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Ошибка генерации аудио: {result.get('error_message', 'Неизвестная ошибка')}"
            )
            return
        
        # Send audio file
        audio_path = result.get("audio_path")
        duration = result.get("duration_seconds", 0)
        articles_count = result.get("articles_count", len(result.get("articles_used", [])))
        
        if audio_path and Path(audio_path).exists():
            # Send only audio file to user (without additional messages)
            with open(audio_path, "rb") as audio_file:
                await context.bot.send_audio(
                    chat_id=chat_id,
                    audio=audio_file,
                    title=f"Аудио резюме из {articles_count} статей",
                    duration=int(duration) if duration > 0 else None,
                    performer="TabSage AI",
                    caption=f"✅ Аудио резюме готово!\n📊 Статей: {articles_count}\n⏱️ Длительность: {duration/60:.1f} мин"
                )
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"⚠️ Аудио сгенерировано, но файл не найден: {audio_path}"
            )
            
    except Exception as e:
        import traceback
        logger.error(f"Error in generate_audio_handler: {e}")
        logger.debug(traceback.format_exc())
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ Ошибка генерации аудио: {str(e)}"
        )


def create_bot() -> Application:
    """Creates and configures Telegram bot"""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("graph", graph_command))
    application.add_handler(CommandHandler("export_graph", export_graph_command))
    application.add_handler(CommandHandler("search", lambda u, c: handle_message(u, c)))
    application.add_handler(CommandHandler("audio", lambda u, c: handle_message(u, c)))
    
    # Message handling
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    return application


async def main():
    """Bot startup"""
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    logger.info("Starting TabSage Telegram Bot...")
    
    try:
        logger.info("Creating bot application...")
        application = create_bot()
        logger.info("Bot application created successfully")
        
        # Start bot
        logger.info("Initializing bot...")
        await application.initialize()
        logger.info("Bot initialized")
        
        logger.info("Starting bot...")
        await application.start()
        logger.info("Bot started")
        
        logger.info("Starting polling...")
        await application.updater.start_polling()
        logger.info("Polling started")
        
        logger.info("Bot is running and ready to receive messages...")
        
        # Wait for stop
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Stopping bot...")
            await application.updater.stop()
            await application.stop()
            await application.shutdown()
    except Exception as e:
        logger.error(f"Error starting bot: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())

