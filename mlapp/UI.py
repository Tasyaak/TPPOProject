import traceback, threading, sqlite3, json, tkinter as tk, pandas as pd
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from processing_cpp import compile_get_error_info, strip_cpp_comments, safe_extract_context, clear_build_tmp
from .normalize_data import build_features_from_ctx, error_tokenizer
from .import_model import load_sklearn_model_bundle
from config import MODELS_DIR, DB_PATH


def enable_windows_dpi_awareness() -> None:
    import os
    if os.name != "nt":
        return

    import ctypes
    from ctypes import wintypes

    try:
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = (HANDLE)-4
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        set_ctx = user32.SetProcessDpiAwarenessContext
        set_ctx.argtypes = [wintypes.HANDLE]
        set_ctx.restype = wintypes.BOOL

        if set_ctx(wintypes.HANDLE(-4)):
            return
    except Exception:
        pass

    try:
        # PROCESS_PER_MONITOR_DPI_AWARE = 2 (Win8.1+)
        shcore = ctypes.WinDLL("shcore", use_last_error=True)
        shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass

    try:
        # System DPI aware (Vista+)
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.SetProcessDPIAware()
    except Exception:
        pass


class CompileErrorAdvisorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        bundle = load_sklearn_model_bundle(
            MODELS_DIR / "sgd_log_regression_2",
            strict_versions=False,
            expected_steps=("feat", "clf"),
        )
        self.pipe = bundle.pipe
        self.meta = bundle.meta

        self.title("ML C++ Compile Error Advisor")
        self.minsize(900, 600)

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        root = ttk.Frame(self, padding=12)
        root.grid(row=0, column=0, sticky="nsew")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        header = ttk.Label(
            root,
            text="Вставьте исходный C++ код и нажмите «Получить рекомендацию»",
        )
        header.grid(row=0, column=0, sticky="w")

        code_frame = ttk.LabelFrame(root, text="Исходный код", padding=8)
        code_frame.grid(row=1, column=0, sticky="nsew", pady=(10, 10))
        code_frame.columnconfigure(0, weight=1)
        code_frame.rowconfigure(0, weight=1)

        self.code_text = ScrolledText(code_frame, wrap="none", height=18, undo=True)
        self.code_text.grid(row=0, column=0, sticky="nsew")

        self.code_text.insert(
            "1.0",
            "#include <iostream>\n\nint main() {\n    std::cout << \"Hello\" << std::endl;\n    return 0;\n}\n",
        )

        controls = ttk.Frame(root)
        controls.grid(row=2, column=0, sticky="ew")
        controls.columnconfigure(2, weight=1)

        self.check_btn = ttk.Button(controls, text="Получить рекомендацию", command=self.on_check_clicked)
        self.check_btn.grid(row=0, column=0, sticky="w")

        self.clear_btn = ttk.Button(controls, text="Очистить", command=self.on_clear_clicked)
        self.clear_btn.grid(row=0, column=1, sticky="w", padx=(8, 0))

        self.status_var = tk.StringVar(value="Готово")
        status = ttk.Label(controls, textvariable=self.status_var)
        status.grid(row=0, column=2, sticky="e")

        out_frame = ttk.LabelFrame(root, text="Рекомендация", padding=8)
        out_frame.grid(row=3, column=0, sticky="nsew")
        out_frame.columnconfigure(0, weight=1)

        self.reco_var = tk.StringVar(value="Нажмите «Получить рекомендацию»")
        self.reco_msg = tk.Message(out_frame, textvariable=self.reco_var, width=850, justify="left")
        self.reco_msg.grid(row=0, column=0, sticky="ew")


    def on_clear_clicked(self) -> None:
        self.code_text.delete("1.0", "end")
        self.reco_var.set("Нажмите «Получить рекомендацию»")
        self.status_var.set("Очищено")


    def get_recommendation(self, cpp_code : str) -> str:
        source_code = strip_cpp_comments(cpp_code)
        if not source_code:
            return "Вставьте исходный C++ код, затем нажмите «Получить рекомендацию»"
        
        error_text, error_line = compile_get_error_info(source_code)
        if not error_text or not error_line:
            return "Вставленный код не имеет ошибок компиляции"

        ctx = safe_extract_context(source_code, error_line, with_macros = True, radius = 2)

        ctx_tokens, ctx_numeric = build_features_from_ctx(ctx)
        error_text_tokens = error_tokenizer(error_text)

        X = pd.DataFrame([{
            "error_text_tokens": json.dumps(error_text_tokens, ensure_ascii=False),
            "ctx_tokens": json.dumps(ctx_tokens, ensure_ascii=False),
            "ctx_numeric": json.dumps(ctx_numeric, ensure_ascii=False),
        }])

        label = int(self.pipe.predict(X)[0])

        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("""
                            SELECT recommendation
                            FROM recommendations
                            WHERE recommendation_id = ?
                        """, (label,))
            row = cur.fetchone()

        return row[0] if row else "Рекомендация для данного класса не найдена"


    def on_check_clicked(self) -> None:
        cpp_code = self.code_text.get("1.0", "end-1c")

        self.check_btn.configure(state="disabled")
        self.status_var.set("Анализирую...")

        def worker() -> None:
            try:
                reco = self.get_recommendation(cpp_code)
            except Exception:
                reco = "Ошибка при анализе:\n" + traceback.format_exc()
            self.after(0, self._finish_analysis, reco)

        threading.Thread(target=worker, daemon=True).start()


    def _finish_analysis(self, recommendation: str) -> None:
        self.reco_var.set(recommendation)
        self.status_var.set("Готово")
        self.check_btn.configure(state="normal")


if __name__ == "__main__":
    enable_windows_dpi_awareness()
    app = CompileErrorAdvisorApp()
    app.mainloop()