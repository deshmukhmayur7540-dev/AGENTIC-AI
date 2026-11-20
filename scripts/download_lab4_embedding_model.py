"""Explicitly download the pinned Lab 4 model; normal application startup never downloads it."""

import json
from pathlib import Path
import sys

from huggingface_hub import snapshot_download

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.labs.lab4.embedding_service import EMBEDDING_DIMENSION, MODEL_ID, MODEL_REVISION
from config import settings


def main() -> None:
    destination = Path(settings.lab4_embedding_model_path).resolve()
    downloaded_path = snapshot_download(
        repo_id=MODEL_ID,
        revision=MODEL_REVISION,
        local_dir=str(destination),
        allow_patterns=[
            ".gitattributes",
            "README.md",
            "config.json",
            "config_sentence_transformers.json",
            "modules.json",
            "sentence_bert_config.json",
            "1_Pooling/config.json",
            "model.safetensors",
            "tokenizer.json",
            "tokenizer_config.json",
            "special_tokens_map.json",
            "vocab.txt",
        ],
    )
    model_files = [path for path in destination.rglob("*") if path.is_file()]
    total_bytes = sum(path.stat().st_size for path in model_files)
    if not (destination / "model.safetensors").is_file():
        raise RuntimeError(f"Model download did not create model.safetensors in {destination}.")
    (destination / "courseagentai_model.json").write_text(
        json.dumps(
            {
                "model_id": MODEL_ID,
                "revision": MODEL_REVISION,
                "dimension": EMBEDDING_DIMENSION,
                "license": "Apache-2.0",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    model_files = [path for path in destination.rglob("*") if path.is_file()]
    total_bytes = sum(path.stat().st_size for path in model_files)
    print(f"Model: {MODEL_ID}")
    print(f"Revision: {MODEL_REVISION}")
    print(f"Directory: {downloaded_path}")
    print(f"Files: {len(model_files)}")
    print(f"Bytes: {total_bytes}")


if __name__ == "__main__":
    main()
