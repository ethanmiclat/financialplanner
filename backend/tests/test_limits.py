import limits as L


def test_catch_up_bands_are_not_monotonic():
    assert L.elective_401k_limit(35) == 24_500
    assert L.elective_401k_limit(50) == 32_500
    assert L.elective_401k_limit(60) == 35_750
    assert L.elective_401k_limit(63) == 35_750
    assert L.elective_401k_limit(64) == 32_500   # drops back to the 50+ band


def test_ira_and_hsa_limits():
    assert L.ira_limit(30) == 7_500
    assert L.ira_limit(50) == 8_600
    assert L.hsa_limit("self_only", 40) == 4_400
    assert L.hsa_limit("family", 40) == 8_750
    assert L.hsa_limit("family", 55) == 9_750


def test_roth_phaseout_boundaries():
    full = L.roth_ira_eligibility(100_000, "single", 30)
    assert full["status"] == "full" and full["allowed"] == 7_500

    at_start = L.roth_ira_eligibility(153_000, "single", 30)
    assert at_start["status"] == "partial"

    at_end = L.roth_ira_eligibility(168_000, "single", 30)
    assert at_end["status"] == "phased_out" and at_end["allowed"] == 0

    mfj = L.roth_ira_eligibility(247_000, "married_filing_jointly", 30)
    assert mfj["status"] == "partial" and 0 < mfj["allowed"] < 7_500


def test_partial_phaseout_is_monotonic_decreasing():
    prev = 10_000
    for magi in range(153_000, 168_000, 1_000):
        allowed = L.roth_ira_eligibility(magi, "single", 30)["allowed"]
        assert allowed <= prev
        prev = allowed


def test_mandatory_roth_catchup():
    assert L.catch_up_must_be_roth(55, 200_000) is True
    assert L.catch_up_must_be_roth(55, 100_000) is False
    assert L.catch_up_must_be_roth(35, 200_000) is False   # no catch-up at 35
    assert L.catch_up_must_be_roth(55, None) is False      # unknown wages: don't assert


def test_unknown_year_is_an_error():
    try:
        L.load_limits(1999)
    except ValueError as e:
        assert "1999" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_ira_limit_is_capped_by_earned_income():
    """You can't contribute more to an IRA than you earned — the binding limit for a
    student on a part-time wage, and irrelevant for anyone above the statutory cap."""
    assert L.ira_limit(20, 2026, earned_income=4_000) == 4_000
    assert L.ira_limit(20, 2026, earned_income=13_500) == 7_500   # statutory cap wins
    assert L.ira_limit(20, 2026, earned_income=0) == 0
    assert L.ira_limit(20, 2026) == 7_500                          # unknown income


def test_roth_eligibility_respects_the_earned_income_cap():
    e = L.roth_ira_eligibility(4_000, "single", 20, 2026, earned_income=4_000)
    assert e["full_limit"] == 4_000 and e["allowed"] == 4_000


def test_phaseout_floor_never_exceeds_the_earned_income_cap():
    """The $200 phase-out floor must not hand someone more room than they earned."""
    e = L.roth_ira_eligibility(167_900, "single", 30, 2026, earned_income=150)
    assert e["allowed"] <= 150
