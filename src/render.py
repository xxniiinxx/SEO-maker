from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"


def get_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(enabled_extensions=("html", "xml", "md")),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render(template_path: str, **context) -> str:
    return get_env().get_template(template_path).render(**context)
