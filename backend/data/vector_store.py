# backend/data/vector_store.py

import chromadb
from typing import Dict
from utils.config import config
from utils.logger import setup_logger

logger = setup_logger(__name__)


class VectorStore:
    """Vector database for pattern matching (RAG)"""

    def __init__(self, persist_directory: str = None):
        self.persist_directory = persist_directory or config.VECTOR_DB_PATH

        try:
            self.client = chromadb.PersistentClient(path=self.persist_directory)
        except TypeError:
            # Older ChromaDB
            from chromadb.config import Settings
            self.client = chromadb.Client(
                Settings(
                    chroma_db_impl="duckdb+parquet",
                    persist_directory=self.persist_directory,
                )
            )

        self.decay_patterns = self.client.get_or_create_collection(
            name="decay_patterns",
            metadata={"description": "Code decay patterns from historical data"},
        )

        self.bug_patterns = self.client.get_or_create_collection(
            name="bug_patterns",
            metadata={"description": "Bug-prone code patterns"},
        )

        logger.info(f"VectorStore initialized at {self.persist_directory}")

    def add_decay_pattern(
        self,
        pattern_id: str,
        code_snippet: str,
        metadata: Dict,
    ):
        """Add a decay pattern to vector DB"""
        try:
            self.decay_patterns.add(
                ids=[pattern_id],
                documents=[code_snippet],
                metadatas=[metadata],
            )
            logger.debug(f"Added decay pattern: {pattern_id}")
        except Exception as e:
            logger.error(f"Error adding decay pattern: {e}")
            raise

    def find_similar_patterns(
        self,
        code_snippet: str,
        n_results: int = 5,
    ) -> Dict:
        """Find similar decay patterns"""
        try:
            results = self.decay_patterns.query(
                query_texts=[code_snippet],
                n_results=n_results,
            )
            logger.debug(f"Found {len(results['ids'][0])} similar patterns")
            return results
        except Exception as e:
            logger.error(f"Error querying patterns: {e}")
            return {"ids": [[]], "distances": [[]], "metadatas": [[]]}

    def add_bug_pattern(
        self,
        pattern_id: str,
        code_snippet: str,
        bug_type: str,
        severity: str,
        metadata: Dict,
    ):
        """Add a bug pattern"""
        try:
            full_metadata = {
                "bug_type": bug_type,
                "severity": severity,
                **metadata,
            }
            self.bug_patterns.add(
                ids=[pattern_id],
                documents=[code_snippet],
                metadatas=[full_metadata],
            )
            logger.debug(f"Added bug pattern: {pattern_id}")
        except Exception as e:
            logger.error(f"Error adding bug pattern: {e}")
            raise

    def find_bug_patterns(
        self,
        code_snippet: str,
        n_results: int = 5,
    ) -> Dict:
        """Find similar bug patterns"""
        try:
            results = self.bug_patterns.query(
                query_texts=[code_snippet],
                n_results=n_results,
            )
            return results
        except Exception as e:
            logger.error(f"Error querying bug patterns: {e}")
            return {"ids": [[]], "distances": [[]], "metadatas": [[]]}
