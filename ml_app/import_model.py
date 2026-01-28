import json, joblib, sklearn
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
from sklearn.pipeline import Pipeline


@dataclass(frozen=True)
class ModelBundle:
    root : Path
    pipe : Pipeline
    meta : dict[str, Any]
    report_test : Optional[str] = None


def load_sklearn_model_bundle(
    path: str | Path,
    *,
    model_filename: str = "model.joblib",
    meta_filename: str = "meta.json",
    report_filename: str = "report_test.txt",
    expected_steps: tuple[str, ...] = ("feat", "clf"),
    strict_versions: bool = False,
) -> ModelBundle:
    """
    Загружает sklearn Pipeline + meta.json из директории

    Аргументы, которые обычно удобны:
      - path: директория модели (…/2025-12-25_1830_logreg_v1) ИЛИ путь к model.joblib
      - strict_versions: если True — падать при несовпадении sklearn-версии (и др. при наличии)
      - expected_steps: контроль, что Pipeline содержит нужные шаги ("feat","clf")
    """
    p = Path(path)

    # Разрешаем передавать либо директорию, либо прямой путь к model.joblib
    root = p if p.is_dir() else p.parent
    model_path = p if p.is_file() else (root / model_filename)
    meta_path = root / meta_filename
    report_path = root / report_filename

    if not model_path.exists():
        raise FileNotFoundError(f"Не найден файл модели: {model_path}")
    if not meta_path.exists():
        raise FileNotFoundError(f"Не найден meta.json: {meta_path}")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    # Проверка версий (минимально полезная для отлова несовместимостей)
    saved_versions = (meta.get("versions") or {})
    saved_sklearn = saved_versions.get("sklearn")
    runtime_sklearn = sklearn.__version__

    if saved_sklearn and saved_sklearn != runtime_sklearn:
        msg = (
            "Несовпадение версий scikit-learn при загрузке модели.\n"
            f"  saved:   {saved_sklearn}\n"
            f"  runtime: {runtime_sklearn}\n"
            "Это может приводить к ошибкам или некорректным результатам."
        )
        if strict_versions:
            raise RuntimeError(msg)
        else:
            import warnings
            warnings.warn(msg, RuntimeWarning)

    pipe = joblib.load(model_path)

    if not isinstance(pipe, Pipeline):
        raise TypeError(f"Ожидался sklearn.pipeline.Pipeline, получено: {type(pipe)!r}")

    missing = [s for s in expected_steps if s not in pipe.named_steps]
    if missing:
        raise ValueError(
            f"Pipeline не содержит ожидаемых шагов {expected_steps}. "
            f"Отсутствуют: {missing}. Имеются: {tuple(pipe.named_steps.keys())}"
        )

    report_test = report_path.read_text(encoding="utf-8") if report_path.exists() else None
    return ModelBundle(root=root, pipe=pipe, meta=meta, report_test=report_test)