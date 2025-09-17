import re
from pathlib import Path

class PromptLoader:
    """
    Loader untuk mengekstrak *system content/config prompt* Orchestrator dari file pipeline
    TANPA mengubah isinya. Kita cari triple-quoted string yang mengandung
    'You are the Orchestrator' dan pakai secara utuh.
    """
    def __init__(self, pipeline_path: str):
        self.pipeline_path = Path(pipeline_path)
        if not self.pipeline_path.exists():
            raise FileNotFoundError(f"Pipeline file not found: {pipeline_path}")
        self._text = self.pipeline_path.read_text(encoding="utf-8", errors="ignore")

    def orchestrator_system_prompt(self) -> str:
        triples = re.findall(r'("""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\')', self._text)
        for block in triples:
            if "You are the Orchestrator" in block:
                # strip the surrounding triple quotes only; isi dibiarkan apa adanya
                cleaned = block.strip()
                if cleaned.startswith('"""') and cleaned.endswith('"""'):
                    return cleaned[3:-3].strip()
                if cleaned.startswith("'''") and cleaned.endswith("'''"):
                    return cleaned[3:-3].strip()
        raise ValueError("Orchestrator system prompt tidak ditemukan di file pipeline.")
