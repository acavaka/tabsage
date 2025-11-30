"""Flask web application for knowledge graph visualization"""

import os
import logging
from flask import Flask, render_template, jsonify, request
from typing import Dict, Any, List

from tools.kg_client import get_kg_instance

logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route('/')
def index():
    """Main page with graph visualization."""
    return render_template('graph.html')

@app.route('/mindmap')
def mindmap():
    """Mindmap graph visualization (NotebookLM-style)."""
    return render_template('mindmap.html')


@app.route('/graph_data')
def graph_data():
    """API endpoint for getting graph data (for mindmap)."""
    try:
        kg = get_kg_instance()
        
        # Get articles
        articles = []
        if hasattr(kg, 'db'):
            try:
                articles_ref = kg.db.collection("articles")
                for article_doc in articles_ref.stream():
                    article_data = article_doc.to_dict()
                    articles.append(article_data)
            except Exception as e:
                logger.warning(f"Could not get articles from Firestore: {e}")
                # Fallback: return empty list
        
        # Get snapshot (works for both in-memory and Firestore)
        try:
            snapshot = kg.get_snapshot(limit=200)
            entities = snapshot.get("nodes", [])
        except Exception as e:
            logger.warning(f"Could not get snapshot: {e}")
            entities = []
        
        # Get relations
        relations = []
        if hasattr(kg, 'db'):
            try:
                relations_ref = kg.db.collection("relations")
                for relation_doc in relations_ref.stream():
                    relation_data = relation_doc.to_dict()
                    relations.append(relation_data)
                    if len(relations) >= 500:
                        break
            except Exception as e:
                logger.warning(f"Could not get relations from Firestore: {e}")
        elif hasattr(kg, 'edges'):
            # InMemory fallback
            relations = kg.edges[:500]
        
        # Create connections between articles through shared entities
        article_connections = []
        if articles:
            # Group entities by articles from relations
            article_entities = {}
            
            # From relations
            for rel in relations:
                article_url = rel.get("article_url")
                if article_url:
                    if article_url not in article_entities:
                        article_entities[article_url] = set()
                    # Add subject and object as entities
                    subject = rel.get("subject", "").strip()
                    obj = rel.get("object", "").strip()
                    if subject:
                        article_entities[article_url].add(subject)
                    if obj:
                        article_entities[article_url].add(obj)
            
            # From entities (if they have article_url)
            for entity in entities:
                entity_name = entity.get("canonical_name", "").strip()
                if not entity_name:
                    continue
                
                # Check article_url or article_urls
                article_url = entity.get("article_url")
                article_urls = entity.get("article_urls", [])
                
                if article_url:
                    if article_url not in article_entities:
                        article_entities[article_url] = set()
                    article_entities[article_url].add(entity_name)
                
                # Also process article_urls (list)
                if article_urls:
                    for url in article_urls:
                        if url not in article_entities:
                            article_entities[url] = set()
                        article_entities[url].add(entity_name)
            
            # Find common entities between articles
            article_urls = list(article_entities.keys())
            for i, url1 in enumerate(article_urls):
                for url2 in article_urls[i+1:]:
                    common_entities = article_entities[url1] & article_entities[url2]
                    if common_entities:
                        article_connections.append({
                            "source": url1,
                            "target": url2,
                            "common_entities": list(common_entities)[:5],  # First 5
                            "common_count": len(common_entities)
                        })
        
        return jsonify({
            "articles": articles,
            "entities": entities,
            "relations": relations,
            "article_connections": article_connections  # Connections between articles
        })
    except Exception as e:
        logger.error(f"Error getting graph data: {e}", exc_info=True)
        # Return empty data instead of error
        return jsonify({
            "articles": [],
            "entities": [],
            "relations": [],
            "error": str(e)
        })

@app.route('/api/graph')
def get_graph():
    """API endpoint for getting graph data."""
    try:
        kg = get_kg_instance()
        
        # Get snapshot (works for both in-memory and Firestore)
        try:
            snapshot = kg.get_snapshot(limit=200)
            nodes = snapshot.get("nodes", [])
        except Exception as e:
            logger.warning(f"Could not get snapshot: {e}")
            nodes = []
        
        # Get edges (for Firestore)
        edges = []
        if hasattr(kg, 'db'):
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
                    if len(edges) >= 500:  # Limit number of edges
                        break
            except Exception as e:
                logger.warning(f"Could not get edges from Firestore: {e}")
        elif hasattr(kg, 'edges'):
            # InMemory fallback
            edges = kg.edges[:500] if hasattr(kg, 'edges') else []
        
        return jsonify({
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "nodes_count": len(nodes),
                "edges_count": len(edges)
            }
        })
    except Exception as e:
        logger.error(f"Error getting graph: {e}", exc_info=True)
        # Return empty data instead of error
        return jsonify({
            "nodes": [],
            "edges": [],
            "stats": {
                "nodes_count": 0,
                "edges_count": 0
            },
            "error": str(e)
        })


@app.route('/api/stats')
def get_stats():
    """API endpoint for getting graph statistics."""
    try:
        kg = get_kg_instance()
        stats = kg.get_graph_stats()
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/articles')
def get_articles():
    """API endpoint for getting article list."""
    try:
        kg = get_kg_instance()
        if hasattr(kg, 'db'):
            articles_ref = kg.db.collection("articles")
            articles = []
            for article_doc in articles_ref.stream():
                article_data = article_doc.to_dict()
                article_data["article_id"] = article_doc.id
                articles.append(article_data)
            
            return jsonify({"articles": articles})
        else:
            return jsonify({"articles": []})
    except Exception as e:
        logger.error(f"Error getting articles: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/search')
def search_articles():
    """API endpoint for searching articles."""
    try:
        query = request.args.get('q', '')
        limit = int(request.args.get('limit', 10))
        
        if not query:
            return jsonify({"articles": []})
        
        kg = get_kg_instance()
        if hasattr(kg, 'search_articles_by_topic'):
            results = kg.search_articles_by_topic(query, limit=limit)
            return jsonify({"articles": results})
        else:
            return jsonify({"articles": []})
    except Exception as e:
        logger.error(f"Error searching articles: {e}")
        return jsonify({"error": str(e)}), 500


def run_server(host='127.0.0.1', port=5000, debug=False):
    """Launches web server."""
    # Cloud Run compatibility: use PORT env var if set
    port = int(os.getenv('PORT', port))
    host = os.getenv('HOST', host)
    logger.info(f"Starting web server on http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_server(debug=True)

