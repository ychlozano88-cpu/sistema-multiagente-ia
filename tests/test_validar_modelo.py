# -*- coding: utf-8 -*-
"""Tests del control de calidad previo a publicar un modelo (Fase 10d)."""
import importlib.util
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "validar_modelo", os.path.join(ROOT, "scripts", "pipeline", "validar_modelo.py"))
vm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vm)

VIGENTE = {"r2_ensemble": 0.9147, "kappa_clasificacion": 0.7196, "r2_xgb": 0.9149, "r2_lstm": 0.9035}


def test_aprueba_modelo_igual_o_mejor():
    ok, motivos, _ = vm.evaluar(VIGENTE, {"r2_ensemble": 0.92, "kappa_clasificacion": 0.73})
    assert ok and motivos == []


def test_aprueba_leve_caida_dentro_de_tolerancia():
    ok, _, _ = vm.evaluar(VIGENTE, {"r2_ensemble": 0.90, "kappa_clasificacion": 0.70})
    assert ok


def test_rechaza_caida_de_r2():
    ok, motivos, _ = vm.evaluar(VIGENTE, {"r2_ensemble": 0.88, "kappa_clasificacion": 0.72})
    assert not ok and any("R²" in m for m in motivos)


def test_rechaza_caida_de_kappa():
    ok, motivos, _ = vm.evaluar(VIGENTE, {"r2_ensemble": 0.915, "kappa_clasificacion": 0.60})
    assert not ok and any("Kappa" in m for m in motivos)


def test_rechaza_debajo_del_minimo_absoluto_sin_vigente():
    ok, _, _ = vm.evaluar(None, {"r2_ensemble": 0.70})
    assert not ok


def test_aprueba_sin_vigente_si_supera_minimo():
    ok, _, _ = vm.evaluar(None, {"r2_ensemble": 0.90})
    assert ok


def test_rechaza_metricas_incompletas():
    ok, _, _ = vm.evaluar(VIGENTE, {"mae_ensemble": 5.0})
    assert not ok


def test_main_codigos_de_salida(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    vig = tmp_path / "vig.json"
    vig.write_text(json.dumps(VIGENTE))
    bueno = tmp_path / "bueno.json"
    bueno.write_text(json.dumps({"r2_ensemble": 0.915, "kappa_clasificacion": 0.72}))
    malo = tmp_path / "malo.json"
    malo.write_text(json.dumps({"r2_ensemble": 0.80, "kappa_clasificacion": 0.72}))
    assert vm.main(["--vigente", str(vig), "--nuevo", str(bueno)]) == 0
    assert vm.main(["--vigente", str(vig), "--nuevo", str(malo)]) == 1
    assert vm.main(["--nuevo", str(tmp_path / "no_existe.json")]) == 2
