"""Full pipeline example: Ingest -> KG Builder -> Topic Discovery -> Scriptwriter"""

import asyncio
import os
import sys

# Add path to src

from agents.ingest_agent import run_once as ingest_run_once
from agents.kg_builder_agent import run_once as kg_builder_run_once
from agents.topic_discovery_agent import run_once as topic_discovery_run_once
from agents.scriptwriter_agent import run_once as scriptwriter_run_once
from core.config import GEMINI_API_KEY


async def main():
    """Complete podcast creation pipeline"""
    
    print("🚀 TabSage Full Pipeline\n")
    print("=" * 60)
    
    session_id = "full_pipeline_session"
    episode_id = "episode_001"
    
    # Step 1: Ingest
    print("\n📥 Step 1: Ingest Agent\n")
    
    sample_text = """
    Artificial Intelligence in Medicine
    
    Google Health company developed a new algorithm for disease diagnosis.
    Researchers from Stanford University conducted clinical trials.
    Results showed 30% improvement in diagnostic accuracy.
    
    Dr. Smith from Mayo Clinic commented: "This is a revolutionary breakthrough".
    Technology is already being used in clinics in Boston and New York.
    
    Professor Johnson from MIT noted the importance of ethical aspects of using AI.
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
    print("\n" + "=" * 60)
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
    print("\n" + "=" * 60)
    print("\n🔍 Step 3: Topic Discovery Agent\n")
    
    topic_payload = {
        "session_id": session_id,
        "episode_id": episode_id,
        "max_topics": 5
    }
    
    topic_result = await topic_discovery_run_once(topic_payload)
    
    if "error_message" in topic_result:
        print(f"❌ Topic Discovery Error: {topic_result['error_message']}")
        return
    
    topics = topic_result.get("topics", [])
    print(f"✅ Topic Discovery: {len(topics)} topics discovered")
    
    if topics:
        print(f"\n📋 Topics:")
        for i, topic in enumerate(topics[:3], 1):  # Show first 3
            print(f"   {i}. {topic.get('title')}")
            print(f"      Difficulty: {topic.get('difficulty')}, "
                  f"Length: {topic.get('estimated_length_minutes')} min")
        
        # Step 4: Scriptwriter
        print("\n" + "=" * 60)
        print("\n✍️  Step 4: Scriptwriter Agent\n")
        
        # Use first topic
        selected_topic = topics[0]
        
        # Convert dict to Topic object, then to dict for payload
        from schemas.models import Topic
        topic_obj = Topic(**selected_topic)
        
        script_payload = {
            "topic": topic_obj.dict(),  # Pydantic model -> dict for serialization
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
        
        print(f"\n📝 Script Segments:")
        for i, segment in enumerate(segments[:5], 1):  # Show first 5
            print(f"   {i}. [{segment.get('segment_type')}] {segment.get('timing')}")
            print(f"      {segment.get('content', '')[:100]}...")
    
    print("\n" + "=" * 60)
    print("\n✅ Full Pipeline Complete!")


if __name__ == "__main__":
    asyncio.run(main())

