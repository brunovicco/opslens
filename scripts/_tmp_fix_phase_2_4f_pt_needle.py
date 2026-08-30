from pathlib import Path

path = Path("scripts/_tmp_patch_phase_2_4f_closeout_docs.py")
text = path.read_text()
old = "- catálogo Glue explícito de GHSA sobre Silver autoritativo e analytics Athena com custo limitado sobre evidência nested;"
new = "- catálogo Glue explícito para GHSA sobre Silver autoritativo e analytics nested no Athena com custo limitado;"
count = text.count(old)
if count != 2:
    raise RuntimeError(f"expected exactly two temporary PT-BR occurrences, found {count}")
path.write_text(text.replace(old, new))
print("corrected PT-BR architecture tuple in temporary patch script")
