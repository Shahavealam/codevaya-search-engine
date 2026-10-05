"""Print Atlas Search + Vector Search index definitions.

Atlas Search/Vector indexes are managed in Atlas (UI/Terraform/Atlas API),
not via createIndex. Pipe this output into your Atlas automation, then verify
dimensions match EMBEDDING_DIMS (default 1536 for text-embedding-3-small).
"""
import json
import sys

sys.path.insert(0, ".")
from app.config import get_settings
from app.db.indexes import atlas_search_index_definition, atlas_vector_index_definition


def main() -> None:
    s = get_settings()
    s.validate_vector_dims(s.embedding_dims)
    print(json.dumps(atlas_search_index_definition(s.atlas_search_index), indent=2))
    print(json.dumps(atlas_vector_index_definition(
        s.atlas_vector_index, s.atlas_vector_field, s.embedding_dims), indent=2))


if __name__ == "__main__":
    main()
