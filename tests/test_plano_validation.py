from flujo.plano import render_validation_report, validate_evento


def test_validate_evento_ok_masivo_con_testeo():
    ev = {
        "nombre": "Festival Validado",
        "duracion_horas": 6,
        "voluntarios": 7,
        "asistentes_estimados": 2500,
        "incluye_testeo": True,
        "masivo": True,
    }
    report = validate_evento(ev)
    assert report["ok"] is True
    assert report["summary"]["stands"] == 2
    assert report["summary"]["zonas"] == 1
    assert report["summary"]["mesas"] >= 3


def test_validate_evento_detecta_datos_invalidos():
    report = validate_evento({"nombre": "", "duracion_horas": 0, "voluntarios": 0})
    assert report["ok"] is False
    assert "Falta nombre" in " ".join(report["errors"])
    assert "duracion_horas" in " ".join(report["errors"])
    assert "voluntarios" in " ".join(report["errors"])


def test_render_validation_report_contiene_resumen():
    text = render_validation_report({
        "nombre": "Evento",
        "duracion_horas": 4,
        "voluntarios": 3,
        "asistentes_estimados": 100,
    })
    assert "VALIDACION RIDER/PLANO" in text
    assert "Estado: OK" in text
    assert "mesas:" in text
