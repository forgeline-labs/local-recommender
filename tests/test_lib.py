"""Black-box tests for the public ``local_recommender.recommend`` API.

Every test cites the acceptance criterion (AC-n) from the specification.
"""

import copy
import math

import pytest

from local_recommender import recommend

EXAMPLE = [
    {"user": "u1", "item": "a"},
    {"user": "u2", "item": "a"},
    {"user": "u2", "item": "b"},
]


def scores(result):
    return {entry["item"]: entry["score"] for entry in result}


def test_ac1_example_returns_b_with_six_decimal_score():
    result = recommend(EXAMPLE, "u1")
    assert result == [{"item": "b", "score": 0.707107}]
    assert abs(result[0]["score"] - 0.707107) <= 0.000001


def test_ac1_example_with_explicit_limit():
    assert recommend(EXAMPLE, "u1", limit=5) == recommend(EXAMPLE, "u1")


def test_ac2_unknown_user_returns_empty_list():
    assert recommend(EXAMPLE, "unknown") == []


def test_ac2_empty_input_returns_empty_list():
    assert recommend([], "u1") == []
    assert recommend([], "unknown") == []


def test_ac3_seen_items_are_not_candidates():
    # u2 has seen both a and b, so nothing remains as a candidate.
    assert recommend(EXAMPLE, "u2") == []


def test_ac3_candidate_without_common_user_is_excluded():
    interactions = [
        {"user": "u1", "item": "a"},
        {"user": "u2", "item": "a"},
        {"user": "u9", "item": "z"},
    ]
    assert recommend(interactions, "u1") == []


def test_ac3_only_common_user_candidates_appear():
    interactions = [
        {"user": "u1", "item": "a"},
        {"user": "u2", "item": "a"},
        {"user": "u2", "item": "b"},
        {"user": "u9", "item": "c"},
    ]
    assert [entry["item"] for entry in recommend(interactions, "u1")] == ["b"]


def test_ac4_duplicate_pairs_do_not_change_output():
    duplicated = EXAMPLE + EXAMPLE + [EXAMPLE[0]]
    assert recommend(duplicated, "u1") == recommend(EXAMPLE, "u1")
    assert scores(recommend(duplicated, "u1"))["b"] == pytest.approx(0.707107, abs=0.000001)


def test_ac5_ties_after_rounding_are_sorted_by_ascii_item():
    # ``b`` and ``c`` publish the same rounded score; ``b`` sorts first even
    # though its unrounded score is the smaller of the two.
    interactions = [
        {"user": "u0", "item": "a"},
        {"user": "u1", "item": "b"},
        {"user": "u1", "item": "d"},
        {"user": "u10", "item": "a"},
        {"user": "u10", "item": "b"},
        {"user": "u10", "item": "c"},
        {"user": "u10", "item": "d"},
        {"user": "u11", "item": "c"},
        {"user": "u11", "item": "d"},
        {"user": "u12", "item": "a"},
        {"user": "u13", "item": "b"},
        {"user": "u13", "item": "d"},
        {"user": "u14", "item": "b"},
        {"user": "u14", "item": "d"},
        {"user": "u2", "item": "a"},
        {"user": "u2", "item": "b"},
        {"user": "u2", "item": "d"},
        {"user": "u3", "item": "a"},
        {"user": "u3", "item": "c"},
        {"user": "u3", "item": "d"},
        {"user": "u4", "item": "b"},
        {"user": "u4", "item": "d"},
        {"user": "u5", "item": "b"},
        {"user": "u5", "item": "d"},
        {"user": "u6", "item": "d"},
        {"user": "u7", "item": "b"},
        {"user": "u7", "item": "c"},
        {"user": "u9", "item": "a"},
        {"user": "u9", "item": "b"},
        {"user": "u9", "item": "d"},
    ]
    result = recommend(interactions, "u0", limit=3)
    assert [entry["item"] for entry in result] == ["d", "b", "c"]
    assert result[1]["score"] == result[2]["score"] == 0.408248


def test_ac5_exact_tie_is_sorted_by_ascii_item_regardless_of_input_order():
    # U(a)={u1,u2}, U(b)={u2,u3}, U(c)={u2,u4}: both candidates score 0.5.
    # ``c`` is listed before ``b`` in the input to catch stable-order sorting.
    interactions = [
        {"user": "u1", "item": "a"},
        {"user": "u2", "item": "a"},
        {"user": "u3", "item": "c"},
        {"user": "u2", "item": "c"},
        {"user": "u4", "item": "b"},
        {"user": "u2", "item": "b"},
    ]
    result = recommend(interactions, "u1")
    assert [entry["item"] for entry in result] == ["b", "c"]
    assert result[0]["score"] == result[1]["score"] == pytest.approx(0.5, abs=0.000001)


def test_ac6_limit_one_returns_the_first_recommendation():
    interactions = EXAMPLE + [{"user": "u2", "item": "c"}]
    full = recommend(interactions, "u1")
    limited = recommend(interactions, "u1", limit=1)
    assert limited == full[:1]
    assert len(limited) == 1


@pytest.mark.parametrize("limit", [0, 101, -1, 1000, True, False, 1.0, "1", None])
def test_ac6_invalid_limits_raise_value_error(limit):
    with pytest.raises(ValueError):
        recommend(EXAMPLE, "u1", limit=limit)


@pytest.mark.parametrize("limit", [1, 2, 100])
def test_ac6_valid_limits_are_accepted(limit):
    assert isinstance(recommend(EXAMPLE, "u1", limit=limit), list)


def test_ac7_extra_field_is_rejected():
    interactions = [{"user": "u1", "item": "a", "rating": 5}]
    with pytest.raises(ValueError):
        recommend(interactions, "u1")


def test_ac7_missing_field_is_rejected():
    with pytest.raises(ValueError):
        recommend([{"user": "u1"}], "u1")
    with pytest.raises(ValueError):
        recommend([{"item": "a"}], "u1")


def test_ac7_non_list_interactions_are_rejected():
    for value in (None, {"user": "u1", "item": "a"}, "[]", 5, ()):
        with pytest.raises(ValueError):
            recommend(value, "u1")


def test_ac7_non_dict_records_are_rejected():
    for value in ("u1,a", 5, None, ["u1", "a"]):
        with pytest.raises(ValueError):
            recommend([value], "u1")


@pytest.mark.parametrize("field", ["user", "item"])
def test_ac7_non_string_identifiers_are_rejected(field):
    record = {"user": "u1", "item": "a"}
    record[field] = 5
    with pytest.raises(ValueError):
        recommend([record], "u1")


@pytest.mark.parametrize("value", ["", "a" * 33, "a b", "ü", 5, None, True])
def test_ac7_invalid_target_user_is_rejected(value):
    with pytest.raises(ValueError):
        recommend(EXAMPLE, value)


def test_ac7_invalid_identifiers_in_records_are_rejected():
    with pytest.raises(ValueError):
        recommend([{"user": "u 1", "item": "a"}], "u1")
    with pytest.raises(ValueError):
        recommend([{"user": "u1", "item": "a" * 33}], "u1")


def test_ac8_reordering_input_preserves_output():
    forward = recommend(EXAMPLE, "u1")
    backward = recommend(list(reversed(EXAMPLE)), "u1")
    assert forward == backward


def test_ac8_reordering_keeps_order_and_scores_for_many_candidates():
    interactions = [
        {"user": f"u{user}", "item": item}
        for user in range(6)
        for item in ("a", "b", "c", "d", "e")
        if (user + ord(item)) % 2 == 0
    ]
    expected = recommend(interactions, "u0", limit=100)
    for seed in range(5):
        shuffled = copy.deepcopy(interactions)
        shuffled.reverse()
        shuffled = shuffled[seed:] + shuffled[:seed]
        assert recommend(shuffled, "u0", limit=100) == expected


def test_ac9_call_does_not_mutate_interactions():
    interactions = copy.deepcopy(EXAMPLE)
    snapshot = copy.deepcopy(interactions)
    recommend(interactions, "u1")
    assert interactions == snapshot


def test_ac9_second_call_with_another_dataset_is_isolated():
    first = recommend(EXAMPLE, "u1")
    second = recommend([{"user": "x", "item": "p"}, {"user": "y", "item": "p"}], "x")
    third = recommend(EXAMPLE, "u1")
    assert second == []
    assert first == third == [{"item": "b", "score": 0.707107}]


def test_ac10_score_sums_contributions_of_two_seen_items():
    # Sim(a, c) = 1/sqrt(2*2) = 0.5 and Sim(b, c) = 1/sqrt(2*2) = 0.5.
    # The published score is the sum (1.0), not the average (0.5).
    interactions = [
        {"user": "u1", "item": "a"},
        {"user": "u1", "item": "b"},
        {"user": "u2", "item": "a"},
        {"user": "u2", "item": "c"},
        {"user": "u3", "item": "b"},
        {"user": "u3", "item": "c"},
    ]
    result = recommend(interactions, "u1")
    assert scores(result) == {"c": pytest.approx(1.0, abs=0.000001)}


def test_ac11_too_many_records_raise_value_error():
    interactions = [
        {"user": f"u{index % 100}", "item": f"i{index % 100}"} for index in range(10001)
    ]
    with pytest.raises(ValueError):
        recommend(interactions, "u0")


def test_ac11_too_many_users_raise_value_error():
    interactions = [{"user": f"u{index}", "item": "a"} for index in range(1001)]
    with pytest.raises(ValueError):
        recommend(interactions, "u0")


def test_ac11_too_many_items_raise_value_error():
    interactions = [{"user": "u0", "item": f"i{index}"} for index in range(1001)]
    with pytest.raises(ValueError):
        recommend(interactions, "u0")


def test_ac11_inclusive_limits_are_accepted():
    interactions = [
        {"user": f"u{user}", "item": f"i{(user * 10 + offset) % 1000}"}
        for user in range(1000)
        for offset in range(10)
    ]
    assert len(interactions) == 10000
    result = recommend(interactions, "u0", limit=100)
    assert isinstance(result, list)
    assert len(result) <= 100


def test_scores_are_finite_and_never_negative_zero():
    result = recommend(EXAMPLE, "u1")
    for entry in result:
        assert math.isfinite(entry["score"])
        assert type(entry["score"]) is float
        assert str(entry["score"]) != "-0.0"
        assert round(entry["score"], 6) == entry["score"]


def test_default_limit_is_five():
    interactions = [{"user": "u1", "item": "a"}, {"user": "u2", "item": "a"}]
    interactions.extend({"user": "u2", "item": f"i{index}"} for index in range(8))
    interactions.extend({"user": "u3", "item": f"i{index}"} for index in range(8))
    result = recommend(interactions, "u1")
    assert len(result) == 5
    assert [entry["item"] for entry in result] == [f"i{index}" for index in range(5)]
