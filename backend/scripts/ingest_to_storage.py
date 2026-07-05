import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.storage import ingest_json_documents, ingest_documents
from app.services.knowledge_base import KNOWLEDGE_BASE, LAW_METADATA, load_knowledge_base


def build_records():
    load_knowledge_base()
    records = []
    grouped = {}
    for clause_id, clause_data in KNOWLEDGE_BASE.items():
        law_id = clause_data.get("law_id")
        law_meta = LAW_METADATA.get(law_id, {})
        record = grouped.setdefault(
            law_id,
            {
                "law_id": law_id,
                "law_name": law_meta.get("law_name", ""),
                "summary": law_meta.get("summary", ""),
                "category": law_meta.get("category", "all"),
                "metadata": {"law_name": law_meta.get("law_name", "")},
                "clauses": [],
            },
        )
        record["clauses"].append(
            {
                "id": clause_id,
                "content": clause_data.get("content", ""),
                "position": clause_data.get("position", {}),
                "cross_references": clause_data.get("cross_references", []),
            }
        )
    return list(grouped.values())


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest processed legal JSON into the configured storage backend")
    parser.add_argument("--records", action="store_true", help="Print the generated record count and exit")
    args = parser.parse_args()

    records = build_records()
    if args.records:
        print(f"Prepared {len(records)} record(s)")
        return 0

    count = ingest_documents(records)
    print(f"Ingested {count} record(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
