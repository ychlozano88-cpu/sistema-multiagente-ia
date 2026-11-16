# -*- coding: utf-8 -*-
"""Tests del descubrimiento de versiones de OpenDengue (Fase 10a)."""
from unittest import mock

from agente_1_recoleccion import AgenteRecoleccion as A


class _Resp:
    def __init__(self, data, status=200):
        self._data, self.status_code = data, status

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


LISTADO = [
    {"name": ".DS_Store", "type": "file"},
    {"name": "V1.0", "type": "dir"},
    {"name": "V1.2.2", "type": "dir"},
    {"name": "V1.3", "type": "dir"},
    {"name": "V1.3.1", "type": "dir"},
    {"name": "V1.10", "type": "dir"},
]


def test_version_a_tupla():
    assert A.version_a_tupla("V1.3.1") == (1, 3, 1)
    assert A.version_a_tupla("v2.0") == (2, 0)
    assert A.version_a_tupla(".DS_Store") == ()
    assert A.version_a_tupla(None) == ()


def test_comparacion_de_versiones():
    t = A.version_a_tupla
    assert t("V1.3.1") > t("V1.3")
    assert t("V1.10") > t("V1.9")      # orden numérico, no alfabético
    assert not t("V1.3") > t("V1.3")


def test_listar_releases_ordena_y_construye_urls():
    with mock.patch("agente_1_recoleccion.requests.get", return_value=_Resp(LISTADO)):
        rel = A.listar_releases_opendengue()
    assert [v for v, _ in rel] == ["V1.10", "V1.3.1", "V1.3", "V1.2.2", "V1.0"]
    v, urls = rel[1]
    assert urls[0].endswith("/V1.3.1/Temporal_extract_V1_3_1.zip")
    assert urls[1].endswith("/V1.3.1/Temporal_extract_V1_3_1.csv")


def test_listar_releases_usa_respaldo_si_falla_la_api():
    with mock.patch("agente_1_recoleccion.requests.get", return_value=_Resp({}, status=403)):
        rel = A.listar_releases_opendengue()
    assert rel[0][0] == A.OPENDENGUE_RELEASES[0][0]


def test_ultima_version():
    with mock.patch("agente_1_recoleccion.requests.get", return_value=_Resp(LISTADO)):
        assert A.ultima_version_opendengue() == "V1.10"


# ── Detección de nueva versión (verificar_actualizacion.hay_nueva_version) ──

import json
import os
import runpy

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _verificar(tmp_path, registro, ultima):
    # runpy devuelve una copia del namespace: se parchea el de las funciones (__globals__)
    g = runpy.run_path(os.path.join(_ROOT, "scripts", "pipeline", "verificar_actualizacion.py"),
                       run_name="lib")["hay_nueva_version"].__globals__
    vf = tmp_path / "data_version.json"
    if registro is not None:
        vf.write_text(json.dumps(registro))
    g["VERSION_FILE"] = str(vf)
    g["METRICS_FILE"] = str(tmp_path / "metrics.json")
    g["obtener_sha_github"] = lambda: ("abc123", "2026-11-03")
    with mock.patch.object(A, "ultima_version_opendengue", classmethod(lambda cls: ultima)):
        return g["hay_nueva_version"](), vf


def test_detecta_version_mas_nueva(tmp_path):
    (nueva, *_), _ = _verificar(tmp_path, {"version_dataset": "V1.3"}, "V1.3.1")
    assert nueva


def test_no_reentrena_version_ya_rechazada(tmp_path):
    (nueva, *_), _ = _verificar(tmp_path, {"version_dataset": "V1.3", "version_rechazada": "V1.3.1"}, "V1.3.1")
    assert not nueva


def test_reentrena_si_aparece_version_posterior_a_la_rechazada(tmp_path):
    (nueva, *_), _ = _verificar(tmp_path, {"version_dataset": "V1.3", "version_rechazada": "V1.3.1"}, "V1.4")
    assert nueva


def test_sin_registro_establece_linea_base(tmp_path):
    (nueva, *_), vf = _verificar(tmp_path, None, "V1.3.1")
    assert not nueva
    assert json.loads(vf.read_text())["version_dataset"] == "V1.3.1"
