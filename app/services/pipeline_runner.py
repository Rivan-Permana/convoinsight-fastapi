import json
import tempfile
import pandas as pd
from typing import Dict, Any, Optional, Tuple, Union

# PandasAI + LiteLLM
from pandasai import SmartDataframe
from pandasai_litellm.litellm import LiteLLM
from litellm import completion

from .prompts import PromptLoader

class InferenceEngine:
    """
    Jalankan alur: Orchestrator (LLM) -> 3 agen PandasAI (Manipulator, Visualizer, Analyzer) -> Compiler (LLM).
    - Orchestrator system prompt diambil bulat-bulat dari file pipeline (tanpa perubahan).
    - Result dibuat minimal untuk MVP: text final + (opsional) chart_html / chart_path.
    """
    def __init__(self, model: str, api_key: str, pipeline_path: str):
        self.model = model
        self.api_key = api_key
        self.loader = PromptLoader(pipeline_path)
        import os
        os.environ.setdefault("GEMINI_API_KEY", self.api_key)
        self.llm = LiteLLM(model=self.model, api_key=self.api_key)

    def _schema_overview(self, df: pd.DataFrame, sample_rows: int = 5) -> str:
        head = df.head(sample_rows)
        return json.dumps({
            "columns": list(df.columns),
            "dtypes": {c: str(t) for c, t in df.dtypes.items()},
            "sample": head.to_dict(orient="records")
        }, ensure_ascii=False)

    def _ask_orchestrator(self, user_question: str, schema_json: str) -> Dict[str, str]:
        sys_prompt = self.loader.orchestrator_system_prompt()
        user_content = (
            "User question:\n"
            f"{user_question}\n\n"
            "Dataset schema (JSON):\n"
            f"{schema_json}\n\n"
            "Ingat: Kembalikan STRICT JSON dengan keys persis: "
            "manipulator_prompt, visualizer_prompt, analyzer_prompt, compiler_instruction."
        )
        resp = completion(
            model=self.model,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.1
        )
        text = resp["choices"][0]["message"]["content"]
        # robust JSON parse
        try:
            return json.loads(text)
        except Exception:
            import re
            m = re.search(r'\{[\s\S]*\}', text)
            if not m:
                raise ValueError("Gagal parse JSON dari Orchestrator.")
            return json.loads(m.group(0))

    def _run_pandasai(self, df: pd.DataFrame, prompt: str) -> Any:
        sdf = SmartDataframe(df, config={"llm": self.llm, "save_charts": False, "enforce_privacy": True, "seed": 1})
        return sdf.chat(prompt)

    def _extract_dataframe(self, result: Any) -> pd.DataFrame:
        # PandasAI v3 biasanya mengembalikan DataFrameResponse / pandas.DataFrame
        try:
            from pandasai.core.response.dataframe import DataFrameResponse
            if isinstance(result, DataFrameResponse):
                return result.value
        except Exception:
            pass
        if isinstance(result, pd.DataFrame):
            return result
        raise ValueError("Manipulator tidak mengembalikan DataFrame yang valid.")

    def _extract_visual(self, result: Any) -> Tuple[Optional[str], Optional[str]]:
        """
        Kembalikan (html_string, figure_png_bytes_optional)
        - Bila result HTML table / plotly.to_html -> html_string tersedia
        - Untuk MVP kita cukup kirim HTML (ChartGallery di FE bisa render via iframe/innerHTML)
        """
        # Heuristik umum:
        if isinstance(result, str) and ("<html" in result.lower() or "<table" in result.lower() or "plotly" in result.lower()):
            return result, None
        try:
            # ChartResponse: punya .value untuk figure / html
            html = getattr(result, "value", None)
            if isinstance(html, str):
                return html, None
        except Exception:
            pass
        # Fallback: kirim string apapun sebagai html (FE bisa tampilkan sebagai note)
        return str(result), None

    def _compile_response(self, compiler_instruction: str, facts: Dict[str, Any]) -> str:
        messages = [
            {"role": "system", "content": compiler_instruction},
            {"role": "user", "content": json.dumps(facts, ensure_ascii=False)}
        ]
        resp = completion(model=self.model, messages=messages, temperature=0.1)
        return resp["choices"][0]["message"]["content"]

    def infer(self, df: pd.DataFrame, question: str) -> Dict[str, Any]:
        # 1) Orchestrate
        schema_json = self._schema_overview(df)
        plan = self._ask_orchestrator(question, schema_json)

        # 2) Manipulate -> dataframe terolah
        manip = self._run_pandasai(df, plan["manipulator_prompt"])
        df2 = self._extract_dataframe(manip)

        # 3) Visualize -> html chart/table
        visual = self._run_pandasai(df2, plan["visualizer_prompt"])
        chart_html, _ = self._extract_visual(visual)

        # 4) Analyze -> text analisis
        analysis = self._run_pandasai(df2, plan["analyzer_prompt"])
        analysis_text = str(analysis)

        # 5) Compile -> final narrative
        compiled = self._compile_response(plan["compiler_instruction"], {
            "question": question,
            "columns": list(df2.columns),
            "preview": df2.head(10).to_dict(orient="records"),
            "analysis": analysis_text
        })

        return {
            "plan": plan,
            "analysis_text": analysis_text,
            "compiled": compiled,
            "chart_html": chart_html
        }
