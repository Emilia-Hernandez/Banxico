from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple

import matplotlib.pyplot as plt
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
OUT_DIR = BASE_DIR / "output"

# Archivos esperados en la carpeta inflacion/
FILES = {
    "CP151": BASE_DIR / "CP151.xlsx",  # Inflacion anual general/subyacente/no subyacente
    "CP154": BASE_DIR / "CP154.xlsx",  # INPC por componentes (indices)
    "CF86": BASE_DIR / "CF86.xlsx",    # Tipo de cambio FIX
    "CF114": BASE_DIR / "CF114.xlsx",  # Tasas Cetes
}


def _find_row(df: pd.DataFrame, label: str) -> int:
    mask = df.iloc[:, 0].astype(str).str.strip().eq(label)
    matches = df.index[mask]
    if len(matches) == 0:
        raise ValueError(f"No se encontro la fila '{label}'.")
    return int(matches[0])


def read_banxico_excel(path: Path) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """Lee el formato tipico de Excel de Banxico (metadatos + bloque de datos)."""
    raw = pd.read_excel(path, header=None)

    title_row = _find_row(raw, "Título")
    code_row = _find_row(raw, "Fecha")

    titles = raw.iloc[title_row, 1:].tolist()
    codes = raw.iloc[code_row, 1:].tolist()

    columns = ["fecha"]
    metadata: Dict[str, str] = {}

    seen: Dict[str, int] = {}
    for code, title in zip(codes, titles):
        code = str(code).strip()
        title = str(title).strip()

        if code in seen:
            seen[code] += 1
            unique_code = f"{code}_{seen[code]}"
        else:
            seen[code] = 1
            unique_code = code

        columns.append(unique_code)
        metadata[unique_code] = title

    data = raw.iloc[code_row + 1 :, : len(columns)].copy()
    data.columns = columns

    data["fecha"] = pd.to_datetime(data["fecha"], errors="coerce")
    data = data.dropna(subset=["fecha"])

    for c in data.columns[1:]:
        data[c] = pd.to_numeric(data[c].replace("N/E", pd.NA), errors="coerce")

    data = data.sort_values("fecha").reset_index(drop=True)
    return data, metadata


def _save_clean_csv(code: str, df: pd.DataFrame) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_DIR / f"{code}_clean.csv", index=False)


def _plot_inflacion_anual(cp151: pd.DataFrame, titles: Dict[str, str]) -> None:
    series = ["SP30578", "SP74662", "SP74665"]
    available = [s for s in series if s in cp151.columns]
    if not available:
        return

    data = cp151[["fecha", *available]].copy()
    data = data[data["fecha"] >= (data["fecha"].max() - pd.DateOffset(years=12))]

    plt.figure(figsize=(11, 6))
    for s in available:
        plt.plot(data["fecha"], data[s], label=titles.get(s, s), linewidth=2)

    plt.title("Inflacion anual: general, subyacente y no subyacente")
    plt.ylabel("% anual")
    plt.xlabel("Fecha")
    plt.grid(alpha=0.25)
    plt.legend(frameon=False, fontsize=9)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "01_inflacion_anual.png", dpi=180)
    plt.close()


def _plot_inpc_componentes(cp154: pd.DataFrame, titles: Dict[str, str]) -> None:
    candidates = ["SP1", "SP74626", "SP74628", "SP66540"]
    available = [s for s in candidates if s in cp154.columns]
    if not available:
        return

    data = cp154[["fecha", *available]].copy().dropna()
    data = data[data["fecha"] >= (data["fecha"].max() - pd.DateOffset(years=8))]

    # Reescala cada serie a 100 al inicio del periodo para comparabilidad.
    for s in available:
        first = data[s].iloc[0]
        if pd.notna(first) and first != 0:
            data[s] = 100 * data[s] / first

    plt.figure(figsize=(11, 6))
    for s in available:
        short_label = titles.get(s, s).split(",")[-1].strip()
        plt.plot(data["fecha"], data[s], label=short_label, linewidth=2)

    plt.title("INPC y componentes (base 100 al inicio del periodo)")
    plt.ylabel("Indice reescalado")
    plt.xlabel("Fecha")
    plt.grid(alpha=0.25)
    plt.legend(frameon=False, fontsize=9)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "02_inpc_componentes.png", dpi=180)
    plt.close()


def _plot_tipo_cambio(cf86: pd.DataFrame, titles: Dict[str, str]) -> None:
    code = "SP17908"
    if code not in cf86.columns:
        return

    data = cf86[["fecha", code]].copy().dropna()
    data = data[data["fecha"] >= (data["fecha"].max() - pd.DateOffset(years=12))]

    plt.figure(figsize=(11, 5.5))
    plt.plot(data["fecha"], data[code], color="#1f77b4", linewidth=2)
    plt.title("Tipo de cambio FIX (promedio mensual)")
    plt.ylabel("Pesos por USD")
    plt.xlabel("Fecha")
    plt.grid(alpha=0.25)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "03_tipo_cambio_fix.png", dpi=180)
    plt.close()


def _plot_cetes(cf114: pd.DataFrame, titles: Dict[str, str]) -> None:
    series = ["SF282", "SF3338", "SF3270", "SF3367"]
    available = [s for s in series if s in cf114.columns]
    if not available:
        return

    data = cf114[["fecha", *available]].copy()
    data = data[data["fecha"] >= (data["fecha"].max() - pd.DateOffset(years=12))]

    plt.figure(figsize=(11, 6))
    for s in available:
        label = titles.get(s, s).split(",")[0]
        plt.plot(data["fecha"], data[s], label=label, linewidth=2)

    plt.title("Curva Cetes (promedio mensual)")
    plt.ylabel("% anual")
    plt.xlabel("Fecha")
    plt.grid(alpha=0.25)
    plt.legend(frameon=False, fontsize=9)
    plt.tight_layout()
    plt.savefig(OUT_DIR / "04_cetes.png", dpi=180)
    plt.close()


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    cp151, t151 = read_banxico_excel(FILES["CP151"])
    cp154, t154 = read_banxico_excel(FILES["CP154"])
    cf86, t86 = read_banxico_excel(FILES["CF86"])
    cf114, t114 = read_banxico_excel(FILES["CF114"])

    _save_clean_csv("CP151", cp151)
    _save_clean_csv("CP154", cp154)
    _save_clean_csv("CF86", cf86)
    _save_clean_csv("CF114", cf114)

    _plot_inflacion_anual(cp151, t151)
    _plot_inpc_componentes(cp154, t154)
    _plot_tipo_cambio(cf86, t86)
    _plot_cetes(cf114, t114)

    print(f"Listo. Archivos generados en: {OUT_DIR}")


if __name__ == "__main__":
    main()
