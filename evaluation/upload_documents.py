#!/usr/bin/env python3
"""
Document Uploader for RAG A/B Testing

Uploads the same documents to both AnythingLLM and Private AI Chatspace
to ensure fair comparison.
"""

import asyncio
import yaml
from pathlib import Path
from typing import Dict, List

from rag_wrappers import AnythingLLMWrapper, PrivateAIChatspaceWrapper


def load_config(config_path: str = "config.yaml") -> Dict:
    """Load configuration from YAML file"""
    with open(config_path) as f:
        return yaml.safe_load(f)


def get_test_documents(docs_dir: str = "test_data/documents") -> List[Path]:
    """Get list of test documents to upload"""
    docs_path = Path(docs_dir)
    if not docs_path.exists():
        return []
    
    # Supported file types
    extensions = [".pdf", ".txt", ".md", ".docx"]
    
    documents = []
    for ext in extensions:
        documents.extend(docs_path.glob(f"*{ext}"))
    
    return sorted(documents)


async def upload_to_both_systems(
    documents: List[Path],
    anythingllm: AnythingLLMWrapper,
    privateai: PrivateAIChatspaceWrapper
):
    """Upload documents to both systems"""
    
    print(f"\nUploading {len(documents)} documents to both systems...")
    print("=" * 60)
    
    results = {
        "anythingllm": [],
        "privateai": []
    }
    
    for doc in documents:
        print(f"\n📄 {doc.name}")
        
        # Upload to AnythingLLM
        try:
            print("  → AnythingLLM: uploading...", end=" ", flush=True)
            result = await anythingllm.upload_document(str(doc))
            print(f"✓ ({result.get('location', 'ok')})")
            results["anythingllm"].append({
                "file": doc.name,
                "status": "success",
                "location": result.get("location")
            })
        except Exception as e:
            print(f"✗ Error: {e}")
            results["anythingllm"].append({
                "file": doc.name,
                "status": "error",
                "error": str(e)
            })
        
        # Upload to Private AI Chatspace
        try:
            print("  → PrivateAI:   uploading...", end=" ", flush=True)
            result = await privateai.upload_document(str(doc))
            print(f"✓ (id: {result.get('id', 'ok')})")
            results["privateai"].append({
                "file": doc.name,
                "status": "success",
                "id": result.get("id")
            })
        except Exception as e:
            print(f"✗ Error: {e}")
            results["privateai"].append({
                "file": doc.name,
                "status": "error",
                "error": str(e)
            })
    
    # Wait for embeddings
    print("\n⏳ Waiting for embeddings to complete...")
    await asyncio.sleep(10)  # Give systems time to embed
    
    # Summary
    print("\n" + "=" * 60)
    print("UPLOAD SUMMARY")
    print("=" * 60)
    
    a_success = sum(1 for r in results["anythingllm"] if r["status"] == "success")
    p_success = sum(1 for r in results["privateai"] if r["status"] == "success")
    
    print(f"AnythingLLM: {a_success}/{len(documents)} successful")
    print(f"PrivateAI:   {p_success}/{len(documents)} successful")
    
    return results


async def main():
    """Main entry point"""
    print("RAG A/B Testing - Document Uploader")
    print("=" * 60)
    
    # Load config
    config_path = Path(__file__).parent / "config.yaml"
    if not config_path.exists():
        print(f"ERROR: Config file not found: {config_path}")
        print("Copy config.example.yaml to config.yaml and fill in your values.")
        return
    
    config = load_config(str(config_path))
    
    # Get documents
    docs_dir = Path(__file__).parent / "test_data" / "documents"
    documents = get_test_documents(str(docs_dir))
    
    if not documents:
        print(f"\nNo documents found in {docs_dir}")
        print("Add PDF, TXT, MD, or DOCX files to test_data/documents/")
        return
    
    print(f"\nFound {len(documents)} documents:")
    for doc in documents:
        print(f"  - {doc.name}")
    
    # Create wrappers
    anythingllm = AnythingLLMWrapper(
        base_url=config["anythingllm"]["base_url"],
        api_key=config["anythingllm"]["api_key"],
        workspace_slug=config["anythingllm"]["workspace_slug"]
    )
    
    privateai = PrivateAIChatspaceWrapper(
        base_url=config["privateai"]["base_url"],
        workspace_id=config["privateai"]["workspace_id"],
        email=config["privateai"].get("email"),
        password=config["privateai"].get("password"),
        api_key=config["privateai"].get("api_key")
    )
    
    # Upload
    results = await upload_to_both_systems(documents, anythingllm, privateai)
    
    # Cleanup
    await anythingllm.close()
    await privateai.close()
    
    print("\n✅ Done! You can now run: python run_evaluation.py")


if __name__ == "__main__":
    asyncio.run(main())
