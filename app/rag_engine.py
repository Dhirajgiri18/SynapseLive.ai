import glob
import hashlib
import json
import os
from pathlib import Path

import lancedb
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

from config import DOCS_DIR, LANCEDB_DIR, RAG_TOP_K


class LocalRAG:
    def __init__(self, db_path: str | Path = LANCEDB_DIR):
        print("[RAG] Initializing local embedding model...", flush=True)
        self.encoder = SentenceTransformer("all-MiniLM-L6-v2")
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        self.db = lancedb.connect(str(self.db_path))
        self.collection_name = "meeting_context"
        self.cache_collection_name = "semantic_cache"
        self.table = self._open_table(self.collection_name)
        self.cache_table = self._open_table(self.cache_collection_name)
        self._manifest_path = self.db_path / ".docs_manifest.json"

    def _open_table(self, name: str):
        if name in self.db.table_names():
            return self.db.open_table(name)
        return None

    def _encode(self, text: str) -> list[float]:
        return self.encoder.encode(text, normalize_embeddings=True).tolist()

    def check_cache(self, text_query: str, similarity_threshold: float = 0.88) -> str | None:
        if self.cache_table is None:
            return None

        results = self.cache_table.search(self._encode(text_query)).limit(1).to_pandas()
        if results.empty:
            return None

        best_match = results.iloc[0]
        distance = float(best_match.get("_distance", 2.0))
        similarity = 1.0 - (distance / 2.0)
        if similarity >= similarity_threshold:
            return str(best_match["response"])
        return None

    def store_cache(self, text_query: str, response: str) -> None:
        if not response or response == "NO_CUE":
            return

        entry = [{
            "id": os.urandom(8).hex(),
            "query": text_query,
            "response": response,
            "vector": self._encode(text_query),
        }]
        if self.cache_table is None:
            self.cache_table = self.db.create_table(
                self.cache_collection_name,
                data=entry,
                mode="overwrite",
            )
        else:
            self.cache_table.add(entry)

    @staticmethod
    def _chunk_text(text: str, chunk_size: int = 400, overlap: int = 80) -> list[str]:
        words = text.split()
        if not words:
            return []
        step = max(1, chunk_size - overlap)
        return [
            " ".join(words[index:index + chunk_size]).strip()
            for index in range(0, len(words), step)
            if words[index:index + chunk_size]
        ]

    @staticmethod
    def _extract_text(filepath: str) -> str:
        extension = Path(filepath).suffix.lower()
        try:
            if extension in {".txt", ".md"}:
                return Path(filepath).read_text(encoding="utf-8", errors="ignore")
            if extension == ".pdf":
                reader = PdfReader(filepath)
                return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as error:
            print(f"[RAG] Could not read {filepath}: {error}")
        return ""

    @staticmethod
    def _fingerprint(files: list[str]) -> str:
        digest = hashlib.sha256()
        for filepath in files:
            path = Path(filepath)
            digest.update(str(path.resolve()).encode("utf-8"))
            digest.update(path.read_bytes())
        return digest.hexdigest()

    def ingest_directory(
        self,
        target_dir: str | Path = DOCS_DIR,
        chunk_size: int = 400,
        overlap: int = 80,
    ) -> int:
        target = Path(target_dir)
        target.mkdir(parents=True, exist_ok=True)
        files = sorted(
            filepath
            for pattern in ("*.txt", "*.md", "*.pdf")
            for filepath in glob.glob(str(target / "**" / pattern), recursive=True)
        )
        if not files:
            print(f"[RAG] No supported documents found in {target}.")
            return 0

        fingerprint = self._fingerprint(files)
        if self.table is not None and self._manifest_path.exists():
            try:
                previous = json.loads(self._manifest_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                previous = {}
            if previous.get("fingerprint") == fingerprint:
                print("[RAG] Knowledge base unchanged, skipping re-index.")
                return 0

        records = []
        for filepath in files:
            source = Path(filepath).name
            text = self._extract_text(filepath)
            for chunk_index, chunk in enumerate(self._chunk_text(text, chunk_size, overlap)):
                records.append({
                    "id": f"{source}:{chunk_index}",
                    "source": source,
                    "chunk_index": chunk_index,
                    "text": chunk,
                    "vector": self._encode(chunk),
                })

        if not records:
            print("[RAG] Documents contained no extractable text.")
            return 0

        self.table = self.db.create_table(
            self.collection_name,
            data=records,
            mode="overwrite",
        )
        self._manifest_path.write_text(
            json.dumps({"fingerprint": fingerprint}, indent=2),
            encoding="utf-8",
        )
        print(f"[RAG] Indexed {len(records)} document chunks.")
        return len(records)

    def query(self, text_query: str, top_k: int = RAG_TOP_K) -> str:
        if self.table is None:
            self.table = self._open_table(self.collection_name)
        if self.table is None:
            return ""

        rows = self.table.search(self._encode(text_query)).limit(top_k).to_list()
        return "\n\n".join(
            f"[{row['source']}]: {row['text']}"
            for row in rows
        )
