"""
Complete TabSage Pipeline Example

This example demonstrates complete text processing cycle from start to finish:
1. Ingest Agent - text normalization and chunking
2. KG Builder Agent - entity and relationship extraction
3. Topic Discovery Agent - topic discovery for podcast
4. Scriptwriter Agent - podcast script generation
5. Audio Producer Agent - audio prompt generation
6. Evaluator Agent - content quality evaluation
7. Publisher Agent - result publication

Run:
    python examples/complete_pipeline_example.py

Requirements:
    - GEMINI_API_KEY set in config.py
    - All project dependencies installed
    - Audio Producer needs access to Google Cloud Text-to-Speech API

Example result:
    ✅ Ingest: Artificial Intelligence in Medicine (2 chunks)
    ✅ KG Builder: 15 entities, 12 relations
    ✅ Topic Discovery: 3 topics discovered
    ✅ Scriptwriter: 8 segments, 15 minutes
    ✅ Audio Producer: 8 TTS prompts generated
    ✅ Evaluator: Quality score 0.85
    ✅ Publisher: Published successfully
"""

import asyncio
import os
import sys

# Add path to src for importing project modules

from agents.ingest_agent import run_once as ingest_run_once
from agents.kg_builder_agent import run_once as kg_builder_run_once
from agents.topic_discovery_agent import run_once as topic_discovery_run_once
from agents.scriptwriter_agent import run_once as scriptwriter_run_once
from agents.audio_producer_agent import run_once as audio_producer_run_once
from agents.evaluator_agent import run_once as evaluator_run_once
from agents.publisher_agent import run_once as publisher_run_once
from schemas.models import Topic
from core.config import GEMINI_API_KEY


async def main():
    """Complete podcast creation and publication pipeline"""
    
    print("🚀 TabSage Complete Pipeline\n")
    print("=" * 70)
    
    session_id = "complete_pipeline_session"
    episode_id = "episode_complete_001"
    
    # Step 1: Ingest
    print("\n📥 Step 1: Ingest Agent\n")
    
    sample_text = """
    Artificial Intelligence in Medicine: Revolution in Diagnosis
    
    Google Health company developed a new algorithm for disease diagnosis based on machine learning.
    Researchers from Stanford University conducted large-scale clinical trials of this algorithm.
    Results showed 30% improvement in diagnostic accuracy compared to traditional methods.
    
    Dr. Smith from Mayo Clinic commented: "This is a revolutionary breakthrough in medical diagnosis".
    Technology is already being used in clinics in Boston and New York with positive results.
    
    Professor Johnson from MIT noted the importance of ethical aspects of using AI in medicine.
    It is necessary to ensure algorithm transparency and patient data protection.
    """
    
    ingest_payload = {
        "raw_text": sample_text,
        "metadata": {"source": "example", "type": "article"},
        "session_id": session_id,
        "episode_id": episode_id
    }
    
    ingest_result = await ingest_run_once(ingest_payload)
    
    if "error_message" in ingest_result:
        print(f"❌ Ingest Error: {ingest_result['error_message']}")
        return
    
    print(f"✅ Ingest: {ingest_result.get('title')} ({len(ingest_result.get('chunks', []))} chunks)")
    
    # Step 2: KG Builder
    print("\n" + "=" * 70)
    print("\n🔗 Step 2: KG Builder Agent\n")
    
    kg_payload = {
        "chunks": ingest_result.get("chunks", []),
        "title": ingest_result.get("title", ""),
        "language": ingest_result.get("language", ""),
        "session_id": session_id,
        "episode_id": episode_id
    }
    
    kg_result = await kg_builder_run_once(kg_payload)
    
    if "error_message" in kg_result:
        print(f"❌ KG Builder Error: {kg_result['error_message']}")
        return
    
    print(f"✅ KG Builder: {len(kg_result.get('entities', []))} entities, "
          f"{len(kg_result.get('relations', []))} relations")
    
    # Step 3: Topic Discovery
    print("\n" + "=" * 70)
    print("\n🔍 Step 3: Topic Discovery Agent\n")
    
    topic_payload = {
        "session_id": session_id,
        "episode_id": episode_id,
        "max_topics": 3
    }
    
    topic_result = await topic_discovery_run_once(topic_payload)
    
    if "error_message" in topic_result:
        print(f"❌ Topic Discovery Error: {topic_result['error_message']}")
        return
    
    topics = topic_result.get("topics", [])
    print(f"✅ Topic Discovery: {len(topics)} topics discovered")
    
    if not topics:
        print("⚠️  No topics found, cannot continue")
        return
    
    # Step 4: Scriptwriter
    print("\n" + "=" * 70)
    print("\n✍️  Step 4: Scriptwriter Agent\n")
    
    selected_topic = topics[0]
    topic_obj = Topic(**selected_topic)
    
    script_payload = {
        "topic": topic_obj.dict(),
        "target_audience": "General audience interested in AI and healthcare",
        "format": "informative",
        "session_id": session_id,
        "episode_id": episode_id
    }
    
    script_result = await scriptwriter_run_once(script_payload)
    
    if "error_message" in script_result:
        print(f"❌ Scriptwriter Error: {script_result['error_message']}")
        return
    
    segments = script_result.get("segments", [])
    print(f"✅ Scriptwriter: {len(segments)} segments, "
          f"{script_result.get('total_estimated_minutes', 0)} minutes")
    
    # Step 5: Audio Producer
    print("\n" + "=" * 70)
    print("\n🎙️  Step 5: Audio Producer Agent\n")
    
    audio_payload = {
        "segments": script_result.get("segments", []),
        "full_script": script_result.get("full_script", ""),
        "session_id": session_id,
        "episode_id": episode_id
    }
    
    audio_result = await audio_producer_run_once(audio_payload)
    
    if "error_message" in audio_result:
        print(f"❌ Audio Producer Error: {audio_result['error_message']}")
        return
    
    tts_prompts = audio_result.get("tts_prompts", [])
    print(f"✅ Audio Producer: {len(tts_prompts)} TTS prompts generated")
    print(f"   Target LUFS: {audio_result.get('recommendations', {}).get('target_lufs', -16.0)}")
    
    # Step 6: Evaluator
    print("\n" + "=" * 70)
    print("\n📊 Step 6: Evaluator Agent\n")
    
    eval_payload = {
        "text": script_result.get("full_script", ""),
        "session_id": session_id,
        "episode_id": episode_id
    }
    
    eval_result = await evaluator_run_once(eval_payload)
    
    if "error_message" in eval_result:
        print(f"❌ Evaluator Error: {eval_result['error_message']}")
    else:
        text_eval = eval_result.get("text_evaluation")
        if text_eval:
            print(f"✅ Evaluator:")
            print(f"   Factuality: {text_eval.get('factuality', 0):.2f}")
            print(f"   Coherence: {text_eval.get('coherence', 0):.2f}")
            print(f"   Relevance: {text_eval.get('relevance', 0):.2f}")
    
    # Step 7: Publisher
    print("\n" + "=" * 70)
    print("\n📤 Step 7: Publisher Agent\n")
    
    pub_payload = {
        "script": script_result,
        "audio_file_path": None,  # In reality, this will be path to generated audio
        "session_id": session_id,
        "episode_id": episode_id
    }
    
    pub_result = await publisher_run_once(pub_payload)
    
    if "error_message" in pub_result:
        print(f"❌ Publisher Error: {pub_result['error_message']}")
    else:
        print(f"✅ Publisher: Published to {len(pub_result.get('publication_urls', {}))} platforms")
        for platform, url in pub_result.get("publication_urls", {}).items():
            print(f"   {platform}: {url}")
    
    print("\n" + "=" * 70)
    print("\n✅ Complete Pipeline Finished!")
    print(f"\n📈 Summary:")
    print(f"   - Entities extracted: {len(kg_result.get('entities', []))}")
    print(f"   - Topics discovered: {len(topics)}")
    print(f"   - Script segments: {len(segments)}")
    print(f"   - TTS prompts: {len(tts_prompts)}")
    print(f"   - Published: {pub_result.get('published', False)}")


if __name__ == "__main__":
    asyncio.run(main())

