"""Knowledge graph export to various formats"""

import logging
from typing import Optional
from pathlib import Path
from datetime import datetime

from tools.kg_client import get_kg_instance

logger = logging.getLogger(__name__)


def export_to_graphml(output_path: Optional[str] = None) -> Optional[str]:
    """Exports graph to GraphML format.
    
    Args:
        output_path: Path to save file (if None, created automatically)
        
    Returns:
        Path to created file or None on error
    """
    try:
        kg = get_kg_instance()
        snapshot = kg.get_snapshot(limit=1000)
        nodes = snapshot.get("nodes", [])
        edges_count = snapshot.get("edges_count", 0)
        
        edges = []
        if hasattr(kg, 'db'):  # Firestore
            try:
                relations_ref = kg.db.collection("relations")
                for relation_doc in relations_ref.stream():
                    relation_data = relation_doc.to_dict()
                    edges.append({
                        "source": relation_data.get("subject", ""),
                        "target": relation_data.get("object", ""),
                        "label": relation_data.get("predicate", ""),
                        "confidence": relation_data.get("confidence", 0)
                    })
            except Exception as e:
                logger.warning(f"Could not get edges from Firestore: {e}")
        else:
            edges = kg.edges[:1000]
        
        if output_path is None:
            output_dir = Path(__file__).parent.parent.parent.parent / "data" / "exports"
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(output_dir / f"graph_{timestamp}.graphml")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write('<graphml xmlns="http://graphml.graphdrawing.org/xmlns"\n')
            f.write('         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n')
            f.write('         xsi:schemaLocation="http://graphml.graphdrawing.org/xmlns\n')
            f.write('         http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd">\n')
            
            # Attribute definitions
            f.write('  <key id="type" for="node" attr.name="type" attr.type="string"/>\n')
            f.write('  <key id="confidence" for="node" attr.name="confidence" attr.type="double"/>\n')
            f.write('  <key id="label" for="edge" attr.name="label" attr.type="string"/>\n')
            f.write('  <key id="edge_confidence" for="edge" attr.name="confidence" attr.type="double"/>\n')
            
            # Graph
            f.write('  <graph id="knowledge_graph" edgedefault="directed">\n')
            
            # Nodes
            node_ids = {}
            for i, node in enumerate(nodes):
                node_id = f"n{i}"
                node_name = node.get("canonical_name", f"node_{i}")
                node_ids[node.get("node_id", node_name)] = node_id
                
                f.write(f'    <node id="{node_id}">\n')
                f.write(f'      <data key="type">{node.get("type", "ENTITY")}</data>\n')
                f.write(f'      <data key="confidence">{node.get("confidence", 0)}</data>\n')
                f.write(f'      <data key="label">{node_name}</data>\n')
                f.write('    </node>\n')
            
            # Edges
            for edge in edges[:500]:  # Limit for file size
                source = edge.get("subject", "")
                target = edge.get("object", "")
                predicate = edge.get("predicate", "")
                
                # Find node IDs
                source_id = None
                target_id = None
                
                for node_id, graphml_id in node_ids.items():
                    if source in node_id or node_id.endswith(source):
                        source_id = graphml_id
                    if target in node_id or node_id.endswith(target):
                        target_id = graphml_id
                
                if source_id and target_id:
                    f.write(f'    <edge source="{source_id}" target="{target_id}">\n')
                    f.write(f'      <data key="label">{predicate}</data>\n')
                    f.write(f'      <data key="confidence">{edge.get("confidence", 0)}</data>\n')
                    f.write('    </edge>\n')
            
            f.write('  </graph>\n')
            f.write('</graphml>\n')
        
        logger.info(f"Graph exported to: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Error exporting graph: {e}", exc_info=True)
        return None


def export_to_json(output_path: Optional[str] = None) -> Optional[str]:
    """Exports graph to JSON format.
    
    Args:
        output_path: Path to save file
        
    Returns:
        Path to created file or None
    """
    try:
        import json
        
        kg = get_kg_instance()
        snapshot = kg.get_snapshot(limit=1000)
        stats = kg.get_graph_stats()
        
        edges = []
        if hasattr(kg, 'db'):  # Firestore
            try:
                relations_ref = kg.db.collection("relations")
                for relation_doc in relations_ref.stream():
                    relation_data = relation_doc.to_dict()
                    edges.append(relation_data)
            except Exception as e:
                logger.warning(f"Could not get edges from Firestore: {e}")
        else:  # InMemory
            edges = kg.edges[:1000]
        
        export_data = {
            "export_date": datetime.now().isoformat(),
            "statistics": stats,
            "nodes": snapshot.get("nodes", []),
            "edges": edges[:1000]  # Limit
        }
        
        if output_path is None:
            output_dir = Path(__file__).parent.parent.parent.parent / "data" / "exports"
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = str(output_dir / f"graph_{timestamp}.json")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Graph exported to JSON: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Error exporting to JSON: {e}")
        return None

