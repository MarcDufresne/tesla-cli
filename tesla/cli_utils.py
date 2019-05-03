import json
from typing import Union, List, Dict

import click


def format_distance_unit(value: Union[str, float, int], display_unit: str) -> str:
    if display_unit == "km":
        return f"{float(value) * 1.60934:.0f} {display_unit}"
    return f"{float(value):.0f} {display_unit}"


def format_bool_value(value: Union[str, int, bool], val_true: str, val_false: str) -> str:
    parsed_value = value

    if isinstance(value, str):
        parsed_value = value.lower() in ["yes", "true", "1", "y", "on"]

    return val_true if parsed_value else val_false


def format_duration(hours: float) -> str:
    minutes = int(hours * 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m"


def print_table(rows: List[str], title: str = None):
    if title:
        click.echo(title)

    max_line_len = max(len(l) for l in rows)

    click.echo("-" * max_line_len)
    click.echo("\n".join(rows))
    click.echo("-" * max_line_len)


def debug_print(resp: Dict, indent: int = 2, sort_keys: bool = True):
    click.secho(f"DEBUG =======================================", fg="yellow")
    click.secho(json.dumps(resp, indent=indent, sort_keys=sort_keys), fg="blue")
    click.secho(f"=============================================", fg="yellow")
