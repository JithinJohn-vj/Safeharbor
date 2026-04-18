import hashlib
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Chunk legal/*.md into Chroma for RAG"

    def handle(self, *args, **options):
        try:
            import chromadb
        except ImportError:
            self.stderr.write("Install chromadb: pip install chromadb")
            return

        legal_dir = Path(settings.BASE_DIR) / "legal_docs"
        if not legal_dir.is_dir():
            self.stderr.write(f"Create {legal_dir} and add .md excerpts")
            return

        path = settings.CHROMA_PATH
        Path(path).mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(path))
        col = client.get_or_create_collection(
            name="safeharbor_legal",
            metadata={"description": "EU/UK gambling law excerpts"},
        )

        chunks: list[str] = []
        metas: list[dict] = []
        ids: list[str] = []

        for md in sorted(legal_dir.glob("*.md")):
            text = md.read_text(encoding="utf-8")
            part = 0
            size = 1200
            for i in range(0, len(text), size):
                chunk = text[i : i + size].strip()
                if len(chunk) < 40:
                    continue
                cid = hashlib.sha256(f"{md.name}-{part}".encode()).hexdigest()[:32]
                ids.append(cid)
                chunks.append(chunk)
                metas.append({"source": md.name})
                part += 1

        if not ids:
            self.stdout.write("No chunks produced")
            return

        col.upsert(ids=ids, documents=chunks, metadatas=metas)
        self.stdout.write(self.style.SUCCESS(f"Ingested {len(ids)} chunks into Chroma"))
