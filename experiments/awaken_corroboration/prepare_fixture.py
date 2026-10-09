"""Materialize only the two hash-pinned PCM members of the private bundle."""
import hashlib
import json
import os
from pathlib import Path
import zipfile


def main():
    root=Path(__file__).resolve().parents[2]
    fixture=json.loads((root/"tests/fixtures/awaken_positive.json").read_text())
    with zipfile.ZipFile(os.environ["RHYTHMALIGN_AWAKEN_REPRO_ZIP"]) as archive:
        audio={n:archive.read(n) for n in fixture["audio_sha256"]}
    for name,sha in fixture["audio_sha256"].items():
        assert hashlib.sha256(audio[name]).hexdigest()==sha,name
    dest=root/"results/awaken/bundle"
    dest.mkdir(parents=True,exist_ok=True)
    for name,data in audio.items():
        (dest/name).write_bytes(data)
    print("Prepared both hash-verified PCM fixtures in ignored local storage")


if __name__=="__main__":
    main()
