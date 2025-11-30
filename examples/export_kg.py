"""
Export Knowledge Graph to JSON file

This script exports the entire knowledge graph to JSON format for:
- Data backup
- Graph analysis with external tools
- Data migration between systems
- Visualization in other tools

Run:
    python examples/export_kg.py

Result:
    - File data/kg_export.json with full graph
    - Export statistics (number of nodes, edges)
    - File size

Example export structure:
    {
      "export_date": "2025-11-29T12:00:00",
      "statistics": {
        "nodes_count": 150,
        "edges_count": 200,
        "articles_count": 10
      },
      "nodes": [...],
      "edges": [...]
    }
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add path to project for importing modules

from tools.kg_client import get_kg_instance


def main():
    """
    Exports knowledge graph to JSON file
    
    Process:
    1. Gets Knowledge Graph instance
    2. Collects graph statistics
    3. Exports nodes and edges
    4. Saves to JSON file
    """
    
    print("📤 Exporting Knowledge Graph to JSON...\n")
    print("=" * 60)
    
    # Get Knowledge Graph instance
    # Uses InMemoryKnowledgeGraph or FirestoreKnowledgeGraph
    # depending on configuration
    print("📊 Loading Knowledge Graph...")
    kg = get_kg_instance()
    
    # Get graph statistics
    stats = kg.get_graph_stats()
    print(f"   Nodes: {stats.get('nodes_count', 0)}")
    print(f"   Edges: {stats.get('edges_count', 0)}")
    print(f"   Articles: {stats.get('articles_count', 0)}\n")
    
    # Get graph snapshot (all nodes, limit for performance)
    print("📸 Creating snapshot...")
    snapshot = kg.get_snapshot(limit=10000)  # Maximum 10000 nodes
    nodes = snapshot.get("nodes", [])
    print(f"   Snapshot nodes: {len(nodes)}\n")
    
    # Prepare export data
    print("📦 Preparing export data...")
    export_data = {
        "export_date": datetime.now().isoformat(),  # Export date and time
        "statistics": stats,  # Graph statistics
        "nodes": nodes,  # All graph nodes
        "edges": kg.edges[:1000],  # Limit number of edges for performance
        "total_nodes": len(kg.nodes),  # Total number of nodes
        "total_edges": len(kg.edges)  # Total number of edges
    }
    
    # Determine path for saving file
    output_file = Path(__file__).parent.parent / "data" / "kg_export.json"
    output_file.parent.mkdir(exist_ok=True)  # Create directory if it doesn't exist
    
    # Save to JSON file
    print(f"💾 Saving to: {output_file}")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)
    
    # Print export results
    file_size_kb = output_file.stat().st_size / 1024
    print("\n" + "=" * 60)
    print("✅ Export Complete!")
    print("=" * 60)
    print(f"\n📁 File: {output_file}")
    print(f"   📊 Nodes: {stats['nodes_count']}")
    print(f"   🔗 Edges: {stats['edges_count']}")
    print(f"   📄 Articles: {stats.get('articles_count', 0)}")
    print(f"   💾 File size: {file_size_kb:.2f} KB")
    print(f"   📅 Export date: {export_data['export_date']}")
    
    print("\n💡 Tips:")
    print("   - Use examples/view_kg_stats.py to view graph statistics")
    print("   - Import this JSON in other tools for visualization")
    print("   - Keep regular backups of your knowledge graph")

if __name__ == "__main__":
    main()

