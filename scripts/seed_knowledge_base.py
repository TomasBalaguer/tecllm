#!/usr/bin/env python3
"""
Script para cargar la base de conocimiento inicial en Pinecone.
Ejecutar: python scripts/seed_knowledge_base.py --tenant-slug <slug>
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.document_processor import get_document_processor
from app.services.vector_store import get_vector_store


KNOWLEDGE_BASE_PATH = Path(__file__).parent.parent / "knowledge_base"


async def seed_knowledge_base(tenant_slug: str):
    """Load initial knowledge base documents for a tenant."""
    print(f"Loading knowledge base for tenant: {tenant_slug}")

    processor = get_document_processor()
    vector_store = get_vector_store()

    total_chunks = 0

    # Process each category folder
    for category in ["competencies", "rubrics", "examples"]:
        folder_path = KNOWLEDGE_BASE_PATH / category
        if not folder_path.exists():
            print(f"  Skipping {category} (folder not found)")
            continue

        print(f"\nProcessing {category}/")

        for file_path in folder_path.glob("*.md"):
            print(f"  - {file_path.name}")

            content = file_path.read_text(encoding="utf-8")
            document_id = f"seed_{category}_{file_path.stem}"

            # Process into chunks
            chunks = processor.process_text(
                text=content,
                document_id=document_id,
                metadata={
                    "title": file_path.stem.replace("_", " ").title(),
                    "document_type": category.rstrip("s"),  # "competencies" -> "competency"
                    "source_file": str(file_path),
                },
            )

            if chunks:
                # Convert to vector store format
                vector_docs = processor.to_vector_documents(chunks)

                # Upsert to Pinecone
                await vector_store.upsert_documents(tenant_slug, vector_docs)
                total_chunks += len(chunks)
                print(f"    ✓ {len(chunks)} chunks indexed")

    print(f"\n{'=' * 50}")
    print(f"✓ Knowledge base loaded successfully!")
    print(f"  Total chunks: {total_chunks}")
    print(f"  Namespace: tenant_{tenant_slug}")
    print(f"{'=' * 50}")


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Seed knowledge base for a tenant")
    parser.add_argument(
        "--tenant-slug",
        required=True,
        help="The tenant slug to load documents for",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without actually doing it",
    )

    args = parser.parse_args()

    if args.dry_run:
        print("DRY RUN - Would process:")
        for category in ["competencies", "rubrics", "examples"]:
            folder_path = KNOWLEDGE_BASE_PATH / category
            if folder_path.exists():
                for file_path in folder_path.glob("*.md"):
                    print(f"  {category}/{file_path.name}")
        return

    await seed_knowledge_base(args.tenant_slug)


if __name__ == "__main__":
    asyncio.run(main())
