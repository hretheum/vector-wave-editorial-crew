def test_import_vector_wave_audiences_structure():
    from ai_writing_flow.crews import VECTOR_WAVE_AUDIENCES, AudienceCrew

    assert isinstance(VECTOR_WAVE_AUDIENCES, dict)
    assert len(VECTOR_WAVE_AUDIENCES) >= 3
    # Basic keys existence
    sample = next(iter(VECTOR_WAVE_AUDIENCES.values()))
    assert all(k in sample for k in ("description", "values", "pain_points", "preferred_depth"))

    # AudienceCrew should access the same mapping
    crew = AudienceCrew()
    assert crew.audiences is VECTOR_WAVE_AUDIENCES
