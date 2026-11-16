# -*- coding: utf-8 -*-
"""
validar_modelo.py — DenguePredict SMA-ML/DL
===========================================
FASE 10d — Control de calidad antes de publicar un modelo reentrenado.

Compara las métricas del modelo recién entrenado (metrics.json) con las del
modelo vigente en producción y decide si el nuevo puede publicarse.

Criterios (todos deben cumplirse):
  1. R² del ensamble >= mínimo absoluto        (por defecto 0.85)
  2. R² del ensamble >= R² vigente - tolerancia (por defecto 0.02)
  3. Kappa de clasificación >= Kappa vigente - tolerancia_kappa (por defecto 0.05)

Nota: cuando llegan datos nuevos el set de prueba cambia (split dinámico
max_ano - 2), por eso se usa una tolerancia en vez de exigir mejora estricta.

Uso:
    python scripts/pipeline/validar_modelo.py \
        --vigente data/models/metrics_vigente.json \
        --nuevo   data/models/metrics.json

Código de salida: 0 = aprobado, 1 = rechazado, 2 = error de entrada.
Si existe GITHUB_OUTPUT escribe `aprobado=true|false`; si existe
GITHUB_STEP_SUMMARY agrega una tabla comparativa al resumen del workflow.
"""

import argparse
import json
import os
import sys


def cargar(path):
    if not path or not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def evaluar(vigente, nuevo, min_r2=0.85, tol_r2=0.02, tol_kappa=0.05):
    """Devuelve (aprobado: bool, motivos: list[str], filas: list[tuple])."""
    motivos = []
    r2_new = nuevo.get("r2_ensemble")
    kappa_new = nuevo.get("kappa_clasificacion")

    if r2_new is None:
        return False, ["El modelo nuevo no reporta r2_ensemble."], []

    if r2_new < min_r2:
        motivos.append(f"R² ensamble {r2_new:.4f} por debajo del mínimo {min_r2:.2f}.")

    filas = []
    if vigente:
        r2_old = vigente.get("r2_ensemble")
        kappa_old = vigente.get("kappa_clasificacion")
        if r2_old is not None and r2_new < r2_old - tol_r2:
            motivos.append(
                f"R² ensamble empeora: {r2_new:.4f} vs vigente {r2_old:.4f} (tolerancia {tol_r2})."
            )
        if kappa_old is not None and kappa_new is not None and kappa_new < kappa_old - tol_kappa:
            motivos.append(
                f"Kappa empeora: {kappa_new:.4f} vs vigente {kappa_old:.4f} (tolerancia {tol_kappa})."
            )
        for clave in ["r2_ensemble", "r2_xgb", "r2_lstm", "mae_ensemble", "rmse_ensemble",
                      "kappa_clasificacion", "acc_clasificacion"]:
            filas.append((clave, vigente.get(clave), nuevo.get(clave)))
    else:
        for clave in ["r2_ensemble", "r2_xgb", "r2_lstm", "kappa_clasificacion"]:
            filas.append((clave, None, nuevo.get(clave)))

    return len(motivos) == 0, motivos, filas


def _fmt(v):
    return "—" if v is None else (f"{v:.4f}" if isinstance(v, float) else str(v))


def main(argv=None):
    p = argparse.ArgumentParser(description="Control de calidad del modelo reentrenado")
    p.add_argument("--vigente", help="metrics.json del modelo en producción")
    p.add_argument("--nuevo", required=True, help="metrics.json del modelo reentrenado")
    p.add_argument("--min-r2", type=float, default=float(os.environ.get("QA_MIN_R2", 0.85)))
    p.add_argument("--tol-r2", type=float, default=float(os.environ.get("QA_TOL_R2", 0.02)))
    p.add_argument("--tol-kappa", type=float, default=float(os.environ.get("QA_TOL_KAPPA", 0.05)))
    a = p.parse_args(argv)

    nuevo = cargar(a.nuevo)
    if nuevo is None:
        print(f"ERROR: no existe {a.nuevo}")
        return 2
    vigente = cargar(a.vigente)

    aprobado, motivos, filas = evaluar(vigente, nuevo, a.min_r2, a.tol_r2, a.tol_kappa)

    print("=" * 65)
    print("  Control de calidad del modelo reentrenado")
    print("=" * 65)
    print(f"  {'Métrica':<22}{'Vigente':>12}{'Nuevo':>12}")
    for k, old, new in filas:
        print(f"  {k:<22}{_fmt(old):>12}{_fmt(new):>12}")
    print("-" * 65)
    if aprobado:
        print("  APROBADO — el modelo nuevo puede publicarse.")
    else:
        print("  RECHAZADO — se mantiene el modelo vigente:")
        for m in motivos:
            print(f"   - {m}")

    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"aprobado={'true' if aprobado else 'false'}\n")
            f.write(f"motivos={' | '.join(motivos)}\n")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write("### Control de calidad del modelo\n\n| Métrica | Vigente | Nuevo |\n|---|---|---|\n")
            for k, old, new in filas:
                f.write(f"| {k} | {_fmt(old)} | {_fmt(new)} |\n")
            f.write("\n" + ("✅ **Aprobado** — modelo publicado\n" if aprobado else
                            "❌ **Rechazado** — se mantiene el modelo vigente\n\n" +
                            "\n".join(f"- {m}" for m in motivos) + "\n"))

    return 0 if aprobado else 1


if __name__ == "__main__":
    sys.exit(main())
