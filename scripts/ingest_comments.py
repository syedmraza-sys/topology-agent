
import asyncio
import csv
import sys
import os
from pathlib import Path
from typing import List, Dict, Any

# Ensure src is in pythonpath
sys.path.append(os.getcwd())

from src.config import get_settings
from src.dependencies import init_resources, close_resources, get_session_maker
from src.llm.llm_factory import get_comment_embedding_model
from src.db import vector_client 

async def ingest_csv(file_path: str):
    print(f"Starting ingestion from {file_path}...")
    
    # 1. Initialize App Resources (DB, Logging, etc)
    await init_resources()
    
    try:
        settings = get_settings()
        # 2. Setup Embedding Model
        embed_model = get_comment_embedding_model(settings)
        print(f"Using Embedding Model: {type(embed_model)}")

        # 3. Read CSV
        # Assumes CSV has columns: id, text, ... (rest is metadata)
        records = []
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                records.append(row)
        
        print(f"Found {len(records)} records to ingest.")

        SessionLocal = get_session_maker()
        
        async with SessionLocal() as session:
            count = 0
            for row in records:
                comment_id = row.get("id")
                text_content = row.get("text")
                
                if not comment_id or not text_content:
                    print(f"Skipping row missing id or text: {row}")
                    continue

                # Generate Embedding
                # Note: For large datasets, batching embed_documents is better.
                # Here we do one-by-one for simplicity.
                embedding = embed_model.embed_query(text_content)
                
                # Metadata = everything else in the row
                metadata = {k: v for k, v in row.items() if k not in ("id", "embedding")}
                
                # Upsert
                await vector_client.upsert_comment_embedding(
                    session,
                    comment_id=comment_id,
                    embedding=embedding,
                    metadata=metadata
                )
                count += 1
                if count % 10 == 0:
                    print(f"Ingested {count} records...")

            print(f"Finished! Total ingested: {count}")

    except Exception as e:
        print(f"Error during ingestion: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await close_resources()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/ingest_comments.py <path_to_csv>")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    asyncio.run(ingest_csv(csv_file))
