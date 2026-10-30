import html
from importlib.resources import files


def asset_path(name: str):
    if name not in {"flowtoken.js", "flowtoken.css"}:
        raise ValueError("Unknown asset")
    return files("py_flowtoken").joinpath("static", "py_flowtoken", name)


def assets(base_url: str = "/static/flowtoken") -> str:
    base_url = html.escape(base_url.rstrip("/"), quote=True)
    return f'<link rel="stylesheet" href="{base_url}/flowtoken.css"><script type="module" src="{base_url}/flowtoken.js"></script>'
