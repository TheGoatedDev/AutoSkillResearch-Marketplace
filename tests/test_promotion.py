from scripts.promotion import decide_promotion


class TestDecidePromotion:
    def _config(self, **overrides):
        config = {
            "metrics": {
                "eval_quality": {"tolerance": 0.02, "minimum": 0.6},
                "trigger_accuracy": {"tolerance": 0.05, "minimum": 0.7},
                "token_efficiency": {"tolerance": 0.10, "minimum": None},
            },
            "elo_confidence_threshold": 1520,
            "elo_minimum_matches": 5,
        }
        config.update(overrides)
        return config

    def test_all_checks_pass_returns_keep(self):
        result = decide_promotion(config=self._config(), candidate_elo=1530, matches_played=6,
            metrics_old={"eval_quality": 0.72, "trigger_accuracy": 0.85, "token_efficiency": 0.50},
            metrics_new={"eval_quality": 0.78, "trigger_accuracy": 0.84, "token_efficiency": 0.52})
        assert result["decision"] == "keep"

    def test_below_minimum_matches_returns_defer(self):
        result = decide_promotion(config=self._config(), candidate_elo=1530, matches_played=3,
            metrics_old={"eval_quality": 0.72}, metrics_new={"eval_quality": 0.80})
        assert result["decision"] == "defer"

    def test_metric_below_hard_floor_returns_discard(self):
        result = decide_promotion(config=self._config(), candidate_elo=1530, matches_played=6,
            metrics_old={"eval_quality": 0.65, "trigger_accuracy": 0.80},
            metrics_new={"eval_quality": 0.55, "trigger_accuracy": 0.80})
        assert result["decision"] == "discard"
        assert "hard floor" in result["reason"].lower() or "floor" in result["reason"].lower()

    def test_elo_below_threshold_returns_discard(self):
        result = decide_promotion(config=self._config(), candidate_elo=1505, matches_played=6,
            metrics_old={"eval_quality": 0.72}, metrics_new={"eval_quality": 0.75})
        assert result["decision"] == "discard"
        assert "elo" in result["reason"].lower()

    def test_regression_beyond_tolerance_returns_discard(self):
        result = decide_promotion(config=self._config(), candidate_elo=1530, matches_played=6,
            metrics_old={"eval_quality": 0.80, "trigger_accuracy": 0.90},
            metrics_new={"eval_quality": 0.85, "trigger_accuracy": 0.80})
        assert result["decision"] == "discard"
        assert "tolerance" in result["reason"].lower()

    def test_no_improvement_returns_discard(self):
        result = decide_promotion(config=self._config(), candidate_elo=1530, matches_played=6,
            metrics_old={"eval_quality": 0.80, "trigger_accuracy": 0.90},
            metrics_new={"eval_quality": 0.80, "trigger_accuracy": 0.90})
        assert result["decision"] == "discard"

    def test_null_minimum_skips_floor_check(self):
        result = decide_promotion(config=self._config(), candidate_elo=1530, matches_played=6,
            metrics_old={"token_efficiency": 0.50}, metrics_new={"token_efficiency": 0.55})
        assert result["decision"] == "keep"
