"""
KG Builder Agent Usage Example

This example demonstrates full text processing pipeline:
1. Ingest Agent - text normalization and chunking
2. KG Builder Agent - entity and relationship extraction from chunks

Run:
    python examples/kg_builder_example.py

Requirements:
    - GEMINI_API_KEY set in config.py
    - All project dependencies installed

Example result:
    ✅ Ingest complete!
       Title: Artificial Intelligence in Medicine
       Language: en
       Chunks: 2
    
    ✅ KG Builder complete!
       Entities: 8
       Relations: 5
       Chunks processed: 2
    
    🏷️  Entities:
       1. [ORGANIZATION] Google Health (confidence: 0.95)
       2. [ORGANIZATION] Stanford University (confidence: 0.90)
       ...
    
    🔗 Relations:
       1. Google Health --[developed]--> diagnostic algorithm (confidence: 0.85)
       2. Stanford University --[conducted]--> clinical trials (confidence: 0.80)
       ...
"""

import asyncio
import os
import sys

# Add path to src for importing project modules

from agents.ingest_agent import run_once as ingest_run_once
from agents.kg_builder_agent import run_once as kg_builder_run_once
from core.config import GEMINI_API_KEY


async def main():
    """
    Main function for full pipeline example: Ingest -> KG Builder
    
    Demonstrates:
    1. Text processing via Ingest Agent (normalization, chunking)
    2. Knowledge extraction via KG Builder Agent (entities, relationships)
    3. Saving results to Knowledge Graph
    
    Expected result:
    - Text processed and chunked
    - Entities extracted (organizations, persons, concepts)
    - Relationships between entities extracted
    - Data saved to knowledge graph
    """
    
    print("🚀 TabSage Pipeline: Ingest -> KG Builder\n")
    print("=" * 70)
    
    # ============================================================
    # Step 1: Ingest Agent - text processing
    # ============================================================
    print("\n📥 Step 1: Ingest Agent - text processing\n")
    print("Ingest Agent performs:")
    print("  - Text normalization (ad removal, formatting)")
    print("  - Chunking for subsequent processing")
    print("  - Language detection")
    print("  - Title and brief summary generation\n")
    
    # Sample text about AI in medicine
    # Text contains entities (organizations, persons) and relationships
    sample_text = """
    Artificial Intelligence in Medicine
    
    Google Health company developed a new algorithm for disease diagnosis.
    Researchers from Stanford University conducted clinical trials.
    Results showed 30% improvement in diagnostic accuracy.
    
    Dr. Smith from Mayo Clinic commented: "This is a revolutionary breakthrough".
    Technology is already being used in clinics in Boston and New York.
    """
    
    # Prepare payload for Ingest Agent
    ingest_payload = {
        "raw_text": sample_text,
        "metadata": {"source": "example", "type": "article"},
        "session_id": "pipeline_session_001",
        "episode_id": "episode_001"
    }
    
    print(f"📋 Input:")
    print(f"   Text length: {len(sample_text)} characters")
    print(f"   Session ID: {ingest_payload['session_id']}\n")
    
    # Call Ingest Agent
    ingest_result = await ingest_run_once(ingest_payload)
    
    if "error_message" in ingest_result:
        print(f"❌ Ingest Error: {ingest_result['error_message']}")
        print("\n💡 Troubleshooting:")
        print("   - Check GEMINI_API_KEY in config.py")
        print("   - Make sure all dependencies are installed")
        return
    
    print("✅ Ingest complete!")
    print(f"   📝 Title: {ingest_result.get('title')}")
    print(f"   🌐 Language: {ingest_result.get('language')}")
    print(f"   📦 Chunks: {len(ingest_result.get('chunks', []))}")
    print(f"   📄 Summary: {ingest_result.get('summary', '')[:100]}...")
    
    # ============================================================
    # Step 2: KG Builder Agent - knowledge extraction
    # ============================================================
    print("\n" + "=" * 70)
    print("\n🔗 Step 2: KG Builder Agent - entity and relationship extraction\n")
    print("KG Builder Agent performs:")
    print("  - Entity extraction (organizations, persons, concepts)")
    print("  - Relationship extraction between entities")
    print("  - Entity type determination (ORGANIZATION, PERSON, CONCEPT)")
    print("  - Confidence score calculation for entities and relationships\n")
    
    # Prepare payload for KG Builder Agent
    # Pass chunks from Ingest Agent for processing
    kg_payload = {
        "chunks": ingest_result.get("chunks", []),  # Text chunks for analysis
        "title": ingest_result.get("title", ""),  # Title for context
        "language": ingest_result.get("language", ""),  # Language for correct processing
        "session_id": ingest_result.get("session_id"),  # Session ID for tracking
        "episode_id": ingest_result.get("episode_id"),  # Episode ID
        "metadata": ingest_payload.get("metadata", {})  # Article metadata
    }
    
    print(f"📋 Input:")
    print(f"   Chunks to process: {len(kg_payload['chunks'])}")
    print(f"   Title: {kg_payload['title']}\n")
    
    # Call KG Builder Agent
    kg_result = await kg_builder_run_once(kg_payload)
    
    if "error_message" in kg_result:
        print(f"❌ KG Builder Error: {kg_result['error_message']}")
        return
    
    print("✅ KG Builder complete!")
    print(f"\n📊 Extraction Results:")
    print(f"   🏷️  Entities: {len(kg_result.get('entities', []))}")
    print(f"   🔗 Relations: {len(kg_result.get('relations', []))}")
    print(f"   📦 Chunks processed: {len(kg_result.get('chunk_extractions', []))}")
    
    # Print extracted entity details
    entities = kg_result.get("entities", [])
    if entities:
        print(f"\n🏷️  Extracted Entities (showing first 10):")
        print("-" * 70)
        for i, entity in enumerate(entities[:10], 1):
            entity_type = entity.get('type', 'UNKNOWN')
            name = entity.get('canonical_name', 'N/A')
            confidence = entity.get('confidence', 0)
            print(f"   {i:2d}. [{entity_type:12s}] {name:30s} (confidence: {confidence:.2f})")
            # Show aliases if present
            aliases = entity.get("aliases", [])
            if aliases:
                aliases_str = ', '.join(aliases[:3])
                if len(aliases) > 3:
                    aliases_str += f" (+{len(aliases) - 3} more)"
                print(f"       └─ Aliases: {aliases_str}")
    
    # Print extracted relationship details
    relations = kg_result.get("relations", [])
    if relations:
        print(f"\n🔗 Extracted Relations (showing first 10):")
        print("-" * 70)
        for i, relation in enumerate(relations[:10], 1):
            subject = relation.get('subject', 'N/A')
            predicate = relation.get('predicate', 'N/A')
            obj = relation.get('object', 'N/A')
            confidence = relation.get('confidence', 0)
            print(f"   {i:2d}. {subject:25s} --[{predicate:15s}]--> {obj:25s} (confidence: {confidence:.2f})")
    
    # Show entity type statistics
    if entities:
        entity_types = {}
        for entity in entities:
            entity_type = entity.get('type', 'UNKNOWN')
            entity_types[entity_type] = entity_types.get(entity_type, 0) + 1
        
        if entity_types:
            print(f"\n📊 Entity Types Distribution:")
            for etype, count in sorted(entity_types.items(), key=lambda x: x[1], reverse=True):
                print(f"   {etype}: {count}")
    
    print("\n" + "=" * 70)
    print("\n✅ Pipeline Complete!")
    print("\n💡 Next steps:")
    print("   - Check examples/view_kg_stats.py to see graph statistics")
    print("   - Try examples/full_pipeline_example.py for complete pipeline")
    print("   - Use examples/export_kg.py to export graph to JSON")


if __name__ == "__main__":
    asyncio.run(main())

