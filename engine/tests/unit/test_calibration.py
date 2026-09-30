from gera_d_engine.calibration import load_calibration


def test_calibration_version_is_set():
    calibration = load_calibration()
    assert calibration.calibration_version == "93x7 Franq | Calibration v1.0"


def test_six_criteria_defined():
    calibration = load_calibration()
    assert set(calibration.criteria.keys()) == {
        "posicionamento",
        "conexao",
        "sondagem",
        "direcionamento",
        "encaminhamento",
        "eficiencia_conducao",
    }


def test_classify_band_boundaries():
    calibration = load_calibration()
    assert calibration.classify_band(10.0).key == "excelente"
    assert calibration.classify_band(8.0).key == "excelente"
    assert calibration.classify_band(7.9).key == "atencao"
    assert calibration.classify_band(7.0).key == "atencao"
    assert calibration.classify_band(6.9).key == "desenvolvimento_prioritario"
    assert calibration.classify_band(6.0).key == "desenvolvimento_prioritario"
    assert calibration.classify_band(5.9).key == "desenvolvimento_critico"
    assert calibration.classify_band(0.0).key == "desenvolvimento_critico"


def test_format_score_line():
    calibration = load_calibration()
    line = calibration.format_score_line(8.2, "Posicionamento")
    assert line == "● 8,2 | POSICIONAMENTO"
