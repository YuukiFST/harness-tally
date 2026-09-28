"""Summarise meta/models.json and endpoints/*.json into a Markdown table.

Run by catalogue.sh; output goes to meta/summary.md.
Usage: python summarize.py > meta/summary.md
"""

import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent


def load_endpoints(model_id: str) -> dict | None:
    path = HERE / "endpoints" / (model_id.replace("/", "_").replace(":", "_") + ".json")
    if not path.exists():
        return None
    body = json.loads(path.read_text(encoding="utf-8"))
    return body.get("data")


def per_million(price: str) -> str:
    return f"{float(price) * 1e6:.3g}"


def free_rows(models: list[dict]) -> list[str]:
    rows = []
    for m in sorted(models, key=lambda m: -m["created"]):
        if not m["id"].endswith(":free"):
            continue
        params = m.get("supported_parameters", [])
        eps = (load_endpoints(m["id"]) or {}).get("endpoints", [])
        providers = ", ".join(
            f"{e['provider_name']} ({e.get('quantization')}, up {e.get('uptime_last_1d') or 0:.0f}%/1d)" for e in eps
        )
        twin = load_endpoints(m["id"][:-5])
        twin_eps = (twin or {}).get("endpoints", [])
        twin_prices = sorted(
            (float(e["pricing"]["prompt"]), float(e["pricing"]["completion"]), e["provider_name"]) for e in twin_eps
        )
        twin_txt = "none" if not twin_prices else "; ".join(
            f"{p}: ${i * 1e6:.3g}/${o * 1e6:.3g}" for i, o, p in twin_prices
        )
        rows.append(
            "| `{id}` | {created} | {exp} | {ctx} | {maxout} | {tools} | {tc} | {n} | {prov} | {twin} |".format(
                id=m["id"],
                created=datetime.fromtimestamp(m["created"], timezone.utc).date(),
                exp=m.get("expiration_date"),
                ctx=m["context_length"],
                maxout=(m.get("top_provider") or {}).get("max_completion_tokens"),
                tools="tools" in params,
                tc="tool_choice" in params,
                n=len(eps),
                prov=providers or "?",
                twin=twin_txt,
            )
        )
    return rows


def main() -> None:
    models = json.loads((HERE / "meta" / "models.json").read_text(encoding="utf-8"))["data"]
    print("| id | created (UTC) | expiration_date | context | max output | tools | tool_choice | free endpoints | free providers | paid twin in/out per 1M |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for row in free_rows(models):
        print(row)


if __name__ == "__main__":
    main()
