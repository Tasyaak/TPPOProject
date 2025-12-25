from importlib import import_module


def prepare_param_grids(model_cfg : dict, *, prefix : str = "clf__") -> list[dict] | None:
    grids = model_cfg.get("grid", None)
    if not grids:
        return None
    out = []
    for g in grids:
        out.append({f"{prefix}{k}": v for k, v in g.items()})
    return out


def _infer_max_resources_from_grid(param_grid, resource_name : str):
    vals = []
    grids = param_grid if isinstance(param_grid, list) else [param_grid]
    for g in grids:
        if resource_name in g:
            v = g[resource_name]
            if isinstance(v, (list, tuple)):
                vals.extend([x for x in v if x is not None])
    return max(vals) if vals else None


def _import_obj(path : str):
    mod, name = path.rsplit(".", 1)
    return getattr(import_module(mod), name)