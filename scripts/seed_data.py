#!/usr/bin/env python3
"""
Seed the vector database with example decay and bug patterns.
Run from project root: python scripts/seed_data.py
Or from codedecay/: python -c "import sys; sys.path.insert(0, 'backend'); exec(open('scripts/seed_data.py').read())"
"""

import os
import sys

# Allow running from codedecay/ or from codedecay/backend/
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))

from data.vector_store import VectorStore
from utils.logger import setup_logger

logger = setup_logger(__name__)


def seed_decay_patterns(vector_store: VectorStore) -> None:
    patterns = [
        {
            "id": "pattern_001",
            "code": """
def process_data(data):
    for i in range(len(data)):
        for j in range(len(data[i])):
            for k in range(len(data[i][j])):
                if data[i][j][k] > 0:
                    result = complex_calculation(data[i][j][k])
                    store_result(result)
            """,
            "metadata": {
                "pattern_type": "high_complexity",
                "decay_probability": 0.8,
                "common_issues": "Performance degradation, maintainability issues",
            },
        },
        {
            "id": "pattern_002",
            "code": """
class DataProcessor:
    def __init__(self):
        self.data = []
        self.cache = {}
        self.config = {}
        self.validators = []
        self.transformers = []
        self.filters = []
            """,
            "metadata": {
                "pattern_type": "high_coupling",
                "decay_probability": 0.7,
                "common_issues": "Difficult to refactor, tight coupling",
            },
        },
        {
            "id": "pattern_003",
            "code": """
global_cache = {}
global_config = {}
global_state = {}

def update_data(key, value):
    global_cache[key] = value
    global_state['modified'] = True
            """,
            "metadata": {
                "pattern_type": "global_state",
                "decay_probability": 0.85,
                "common_issues": "Testing difficulty, race conditions",
            },
        },
    ]
    for p in patterns:
        vector_store.add_decay_pattern(p["id"], p["code"], p["metadata"])
        logger.info(f"Added pattern: {p['id']}")


def seed_bug_patterns(vector_store: VectorStore) -> None:
    bug_patterns = [
        {
            "id": "bug_001",
            "code": "def divide_numbers(a, b):\n    return a / b  # No zero check!",
            "bug_type": "division_by_zero",
            "severity": "high",
            "metadata": {
                "description": "Missing zero division check",
                "fix": "Add if b == 0: check",
            },
        },
        {
            "id": "bug_002",
            "code": 'query = f"SELECT * FROM users WHERE id = {data[\'id\']}"  # SQL injection!',
            "bug_type": "sql_injection",
            "severity": "critical",
            "metadata": {
                "description": "SQL injection vulnerability",
                "fix": "Use parameterized queries",
            },
        },
        {
            "id": "bug_003",
            "code": "def save_password(password):\n    with open('passwords.txt', 'w') as f:\n        f.write(password)",
            "bug_type": "security",
            "severity": "critical",
            "metadata": {
                "description": "Plaintext password storage",
                "fix": "Hash passwords with bcrypt",
            },
        },
    ]
    for b in bug_patterns:
        vector_store.add_bug_pattern(
            b["id"], b["code"], b["bug_type"], b["severity"], b["metadata"]
        )
        logger.info(f"Added bug pattern: {b['id']}")


def main() -> None:
    logger.info("Starting database seeding...")
    os.chdir(ROOT)
    vector_store = VectorStore()
    seed_decay_patterns(vector_store)
    seed_bug_patterns(vector_store)
    logger.info("Database seeding complete.")


if __name__ == "__main__":
    main()
