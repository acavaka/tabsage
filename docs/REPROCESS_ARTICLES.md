# Article Reprocessing for Graph Update

This script reprocesses articles from Firestore, updating entities and relationships with correct `article_url`, enabling visualization of relationships between articles.

## Usage

### Reprocess All Articles:
```bash
export KG_PROVIDER=firestore
export GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
python scripts/reprocess_articles.py --all
```

### Reprocess Specific URLs:
```bash
export KG_PROVIDER=firestore
export GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
python scripts/reprocess_articles.py --urls \
  https://habr.com/ru/articles/853038/ \
  https://habr.com/ru/articles/873332/
```

## What the Script Does:

1. **Downloads articles** from Firestore or by specified URLs
2. **Processes via Ingest Agent** - normalizes text, splits into chunks
3. **Processes via KG Builder Agent** - extracts entities and relationships, **saving `article_url`**
4. **Generates Summary** - creates brief summary
5. **Updates Firestore** - saves updated data with correct relationships

## Result:

After reprocessing:
- Entities linked to articles via `article_url`
- Relationships linked to articles via `article_url`
- Visualization shows relationships between articles through common entities
- Graph displays complete knowledge structure

## Verify Result:

1. Start web server: `python run_web.py`
2. Open http://localhost:5001/mindmap
3. You should see:
   - Articles as central nodes
   - Entities around articles
   - Relationships between entities (gray lines)
   - **Relationships between articles through common entities (red dashed lines)**

## Troubleshooting:

If relationships still don't display:
1. Check that `article_url` is saved in Firestore:
   ```python
   from tabsage.tools.kg_client import get_kg_instance
   kg = get_kg_instance()
   if hasattr(kg, 'db'):
       entities = kg.db.collection("entities").limit(5).stream()
       for e in entities:
           print(e.to_dict().get("article_url"))
   ```

2. Check script logs for errors
3. Make sure `KG_PROVIDER=firestore` is set
