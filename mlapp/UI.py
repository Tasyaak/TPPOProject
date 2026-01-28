import traceback, threading, sqlite3, json, tkinter as tk, pandas as pd
from tkinter import ttk, font
from tkinter.scrolledtext import ScrolledText
from pygments import lex
from pygments.lexers import CppLexer
from pygments.token import Token
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


def apply_dark_cpp_editor_style(text : tk.Text) -> None:
    text.configure(
        wrap="none",
        undo=True,
        maxundo=-1,
        bg="#1e1e1e",
        fg="#d4d4d4",
        insertbackground="#d4d4d4",
        selectbackground="#264f78",
        selectforeground="#ffffff",
        borderwidth=0,
        relief="flat",
    )

    try:
        text.configure(font=("Cascadia Code", 11))
    except tk.TclError:
        fixed = font.nametofont("TkFixedFont")
        fixed.configure(size=11)
        text.configure(font=fixed)

    f = font.Font(font=text["font"])
    tabw = f.measure(" " * 4)
    text.configure(tabs=(tabw,))
    text.tag_configure("current_line", background="#252526")


CPP_TAGS = (
    "tok_keyword", "tok_type", "tok_func", "tok_name",
    "tok_string", "tok_number", "tok_comment",
    "tok_op", "tok_punct", "tok_preproc", "tok_error",
)

def _token_to_tag(ttype):
    if ttype in Token.Comment.Preproc or ttype in Token.Comment.PreprocFile:
        return "tok_preproc"
    if ttype in Token.Comment:
        return "tok_comment"
    if ttype in Token.Name.Class or ttype in Token.Keyword.Type:
        return "tok_type"
    if ttype in Token.Keyword:
        return "tok_keyword"
    if ttype in Token.Name.Function:
        return "tok_func"
    if ttype in Token.Name:
        return "tok_name"
    if ttype in Token.String:
        return "tok_string"
    if ttype in Token.Number:
        return "tok_number"
    if ttype in Token.Operator:
        return "tok_op"
    if ttype in Token.Punctuation:
        return "tok_punct"
    if ttype in Token.Error:
        return "tok_error"
    return None


class CppSyntaxHighlighter:
    def __init__(self, text: tk.Text, *, debounce_ms: int = 120) -> None:
        self.text = text
        self.lexer = CppLexer()
        self.debounce_ms = debounce_ms
        self._after_id = None

        text.tag_configure("tok_keyword", foreground="#c586c0")
        text.tag_configure("tok_type",    foreground="#4090d6")
        text.tag_configure("tok_func",    foreground="#dcdcaa")
        text.tag_configure("tok_name",    foreground="#9cdcfe")
        text.tag_configure("tok_string",  foreground="#ce9178")
        text.tag_configure("tok_number",  foreground="#b5ce89")
        text.tag_configure("tok_comment", foreground="#6a9955")
        text.tag_configure("tok_preproc", foreground="#808080")
        text.tag_configure("tok_op",      foreground="#d4d4d4")
        text.tag_configure("tok_punct",   foreground="#d4d4d4")
        text.tag_configure("tok_error",   foreground="#f44747", underline=True)

        text.bind("<KeyRelease>", self._schedule, add="+")
        text.bind("<<Paste>>", self._schedule, add="+")
        text.bind("<<Cut>>", self._schedule, add="+")
        text.bind("<<Undo>>", self._schedule, add="+")
        text.bind("<<Redo>>", self._schedule, add="+")
        text.bind("<ButtonRelease-1>", self._update_current_line, add="+")
        text.bind("<KeyRelease>", self._update_current_line, add="+")

        self.highlight_now()
        self._update_current_line()

    def _schedule(self, event=None):
        if self._after_id is not None:
            self.text.after_cancel(self._after_id)
        self._after_id = self.text.after(self.debounce_ms, self.highlight_now)

    def highlight_now(self):
        self._after_id = None
        code = self.text.get("1.0", "end-1c")

        for tag in CPP_TAGS:
            self.text.tag_remove(tag, "1.0", "end")

        pos = 0
        for ttype, value in lex(code, self.lexer):
            if not value:
                continue
            tag = _token_to_tag(ttype)
            if tag:
                start = f"1.0 + {pos} chars"
                end = f"1.0 + {pos + len(value)} chars"
                self.text.tag_add(tag, start, end)
            pos += len(value)

    def _update_current_line(self, event=None):
        self.text.tag_remove("current_line", "1.0", "end")
        line = self.text.index("insert").split(".")[0]
        self.text.tag_add("current_line", f"{line}.0", f"{line}.0 lineend+1c")


class CompileErrorAdvisorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()

        self._closing = threading.Event()
        self._worker_thread = None

        bundle = load_sklearn_model_bundle(
            MODELS_DIR / "sgd_log_regression_1",
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
        apply_dark_cpp_editor_style(self.code_text)
        self.cpp_hl = CppSyntaxHighlighter(self.code_text)

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

        self.protocol("WM_DELETE_WINDOW", self.on_close_clicked)


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
            if self._closing.is_set():
                return
            try:
                reco = self.get_recommendation(cpp_code)
            except Exception:
                reco = "Ошибка при анализе:\n" + traceback.format_exc()

            if not self._closing.is_set():
                self.after(0, self._finish_analysis, reco)

        self._worker_thread = threading.Thread(target=worker, daemon=True)
        self._worker_thread.start()


    def _finish_analysis(self, recommendation: str) -> None:
        self.reco_var.set(recommendation)
        self.status_var.set("Готово")
        self.check_btn.configure(state="normal")


    def on_close_clicked(self) -> None:
        self._closing.set()
        try:
            self.check_btn.configure(state="disabled")
            self.clear_btn.configure(state="disabled")
        except Exception:
            pass
        clear_build_tmp()
        self.destroy()


if __name__ == "__main__":
    enable_windows_dpi_awareness()
    app = CompileErrorAdvisorApp()
    app.mainloop()