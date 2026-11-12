"""GameConfig defaults and validation."""

from game.config import DEFAULT_CONFIG, GameConfig


def test_build_plan_defaults():
    cfg = GameConfig()
    assert cfg.observation_k == 8
    assert cfg.jump_duration == 1
    assert cfg.roll_duration == 1
    assert cfg.coin_reward == 1.0
    assert cfg.step_reward == 0.01
    assert cfg.crash_penalty == -100.0
    assert cfg.initial_speed == 1.0
    assert cfg.speed_increment == 0.05
    assert cfg.speed_interval_rows == 50
    assert cfg.default_seed == 42
    assert cfg.train_climbing_enabled is True
    assert cfg.num_lanes == 3
    assert cfg.start_lane == 1


def test_default_config_singleton_matches():
    assert DEFAULT_CONFIG.observation_k == GameConfig().observation_k


def test_validate_rejects_bad_values():
    try:
        GameConfig(observation_k=0).validate()
        assert False, "expected ValueError"
    except ValueError:
        pass

    try:
        GameConfig(start_lane=5).validate()
        assert False, "expected ValueError"
    except ValueError:
        pass
