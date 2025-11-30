"""
Script for viewing knowledge graph statistics

This script shows:
- Overall graph statistics (number of nodes, edges)
- Entity type distribution
- Top nodes by confidence score
- Data storage information

Run:
    python examples/view_kg_stats.py

Example output:
    📊 KNOWLEDGE GRAPH STATISTICS
    ============================================================
    
    🔷 Total nodes: 150
    🔗 Total edges: 200
    
    📋 Entity types:
       ORGANIZATION: 45 (30.0%)
       PERSON: 30 (20.0%)
       CONCEPT: 75 (50.0%)
    
    🔝 Top-20 nodes by confidence:
       1. [ORGANIZATION] Google Health (confidence: 0.95)
       2. [PERSON] Dr. Smith (confidence: 0.90)
       ...
"""

import sys
from pathlib import Path

# Add path to project for importing modules

from tools.kg_client import get_kg_instance


def main():
    """
    Prints knowledge graph statistics
    
    Shows:
    - Overall statistics (nodes, edges, articles)
    - Entity type distribution
    - Top nodes by confidence
    - Storage information
    """
    
    print("=" * 70)
    print("📊 KNOWLEDGE GRAPH STATISTICS")
    print("=" * 70)
    print()
    
    # Get Knowledge Graph instance
    print("📡 Loading Knowledge Graph...")
    kg = get_kg_instance()
    
    # Get graph statistics
    stats = kg.get_graph_stats()
    snapshot = kg.get_snapshot(limit=50)  # Top-50 nodes for display
    
    # Overall statistics
    print("📈 Overall Statistics:")
    print("-" * 70)
    print(f"   🔷 Total nodes (entities): {stats.get('nodes_count', 0)}")
    print(f"   🔗 Total edges (relations): {stats.get('edges_count', 0)}")
    print(f"   📄 Processed articles: {stats.get('articles_count', 0)}")
    print()
    
    # Entity type distribution
    entity_types = stats.get('entity_types', {})
    if entity_types:
        total_entities = sum(entity_types.values())
        print("📋 Entity Type Distribution:")
        print("-" * 70)
        for entity_type, count in sorted(entity_types.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_entities * 100) if total_entities > 0 else 0
            bar = "█" * int(percentage / 2)  # Visual bar
            print(f"   {entity_type:20s}: {count:4d} ({percentage:5.1f}%) {bar}")
        print()
    else:
        print("📋 Entity types: No data\n")
    
    # Top nodes by confidence
    nodes = snapshot.get('nodes', [])
    if nodes:
        print("🔝 Top-20 nodes by confidence score:")
        print("-" * 70)
        for i, node in enumerate(nodes[:20], 1):
            node_id = node.get('node_id', 'N/A')
            name = node.get('canonical_name', 'N/A')
            confidence = node.get('confidence', 0)
            entity_type = node.get('type', 'UNKNOWN')
            aliases_count = len(node.get('aliases', []))
            
            # Format output
            name_display = name[:30] + "..." if len(name) > 30 else name
            print(f"   {i:2d}. [{entity_type:12s}] {name_display:33s} "
                  f"(confidence: {confidence:.2f}", end="")
            if aliases_count > 0:
                print(f", {aliases_count} aliases)", end="")
            print(")")
        print()
    else:
        print("🔝 Top nodes: Graph is empty\n")
    
    # Storage information
    print("=" * 70)
    print("💾 DATA STORAGE")
    print("=" * 70)
    print()
    
    # Determine storage type
    storage_type = type(kg).__name__
    
    if "InMemory" in storage_type:
        print("⚠️  WARNING: Using InMemoryKnowledgeGraph")
        print("   - Data stored in Python process memory")
        print("   - Data is NOT persistent (lost on restart)")
        print("   - Suitable for development and testing")
        print()
        print("💡 For production, recommended to use:")
        print("   • FirestoreKnowledgeGraph (Google Cloud Firestore)")
        print("   • Neo4j (graph database)")
        print("   • Amazon Neptune (graph database)")
        print("   • pgVector + PostgreSQL (vector database)")
    elif "Firestore" in storage_type:
        print("✅ Using FirestoreKnowledgeGraph")
        print("   - Data stored in Google Cloud Firestore")
        print("   - Data is persistent and scalable")
        print("   - Suitable for production")
    else:
        print(f"📦 Using: {storage_type}")
    
    print()
    print("📝 Useful commands:")
    print("   - python examples/export_kg.py - export graph to JSON")
    print("   - python examples/view_kg_stats.py - view statistics")
    print()

if __name__ == "__main__":
    main()

