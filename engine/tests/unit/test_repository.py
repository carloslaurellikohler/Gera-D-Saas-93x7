from gera_d_engine.storage import JsonFileReportRepository
from tests.fixtures.sample_result import build_sample_result


def test_save_and_load_round_trip(tmp_path):
    repo = JsonFileReportRepository(tmp_path)
    result = build_sample_result()

    path = repo.save(result)
    assert path.endswith(f"{result.interaction_id}.json")

    loaded = repo.load(result.interaction_id)
    assert loaded.interaction_id == result.interaction_id
    assert loaded.overall_score == result.overall_score
    assert len(loaded.scores_by_criterion) == len(result.scores_by_criterion)
    assert loaded.calibration_version == result.calibration_version
