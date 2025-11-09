from __future__ import annotations

# Точечные импорты из внутренних модулей
from .config import get_config, project_root
# пример: хелперы/модель/GUI — если они у вас есть

# Примерные удобные алиасы (раскоммментируйте, если модули есть)
# from .model_keras import build_mlp
# from .gui.app import GUIApp

__all__ = [
    "get_config",
    "project_root",
    # "set_seed",
    # "build_mlp",
    # "GUIApp",
]
