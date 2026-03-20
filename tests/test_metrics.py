from scripts.metrics import compute_eval_quality, compute_trigger_accuracy, compute_token_efficiency


class TestEvalQuality:
    def test_all_wins(self):
        matches = [{"winner": "candidate"}] * 5
        assert compute_eval_quality(matches) == 1.0

    def test_all_losses(self):
        matches = [{"winner": "champion"}] * 5
        assert compute_eval_quality(matches) == 0.0

    def test_draws_count_half(self):
        matches = [{"winner": "draw"}] * 4
        assert compute_eval_quality(matches) == 0.5

    def test_mixed(self):
        matches = [{"winner": "candidate"}, {"winner": "champion"}, {"winner": "draw"}]
        assert compute_eval_quality(matches) == 0.5

    def test_empty_returns_zero(self):
        assert compute_eval_quality([]) == 0.0


class TestTriggerAccuracy:
    def test_all_correct(self):
        cases = [{"expected_trigger": True, "actual_trigger": True}, {"expected_trigger": False, "actual_trigger": False}]
        assert compute_trigger_accuracy(cases) == 1.0

    def test_all_wrong(self):
        cases = [{"expected_trigger": True, "actual_trigger": False}, {"expected_trigger": False, "actual_trigger": True}]
        assert compute_trigger_accuracy(cases) == 0.0

    def test_mixed(self):
        cases = [{"expected_trigger": True, "actual_trigger": True}, {"expected_trigger": True, "actual_trigger": False}]
        assert compute_trigger_accuracy(cases) == 0.5

    def test_empty_returns_zero(self):
        assert compute_trigger_accuracy([]) == 0.0


class TestTokenEfficiency:
    def test_equal_tokens(self):
        assert compute_token_efficiency(100, 100) == 0.5

    def test_candidate_more_concise(self):
        assert compute_token_efficiency(200, 100) == 1.0

    def test_candidate_more_verbose(self):
        assert compute_token_efficiency(100, 200) == 0.25

    def test_candidate_extremely_concise(self):
        assert compute_token_efficiency(1000, 100) == 1.0

    def test_zero_candidate_tokens_returns_neutral(self):
        assert compute_token_efficiency(100, 0) == 0.5
