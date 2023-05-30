"""Calculate OBP and COBP stats from game data."""
from dataclasses import dataclass
from typing import Iterator, Mapping

from baseball_obp_and_cobp.game import Game
from baseball_obp_and_cobp.play import Play
from baseball_obp_and_cobp.player import Player


@dataclass
class OBPCounters:
    hits: int = 0
    walks: int = 0
    hit_by_pitches: int = 0
    at_bats: int = 0
    sacrifice_flys: int = 0


def get_player_to_game_on_base_percentage(
    game: Game, is_conditional: bool = False, explain: bool = False
) -> dict[str, float]:
    return {
        player.id: _get_players_on_base_percentage(player, game.inning_to_plays, is_conditional, explain)
        for player in game.players
    }


def _get_players_on_base_percentage(
    player: Player, inning_to_plays: Mapping[int, list[Play]], is_conditional: bool = False, explain: bool = False
) -> float:
    explain_lines: list[str] = []
    obp_counters = OBPCounters()
    for play in player.plays:
        play_description_prefix = _get_play_description_prefix(play)
        result = play.result
        other_plays_on_base_in_inning = list(_get_other_plays_on_base_in_inning(play, inning_to_plays[play.inning]))
        if is_conditional and not other_plays_on_base_in_inning:
            _add_explanation_line(explain_lines, play_description_prefix, "N/A (no other on-base in inning)")
            continue

        if result.is_at_bat:
            obp_counters.at_bats += 1

        if result.is_hit:
            obp_counters.hits += 1
            _add_explanation_line(explain_lines, play_description_prefix, "HIT, AB")
        elif result.is_walk:
            obp_counters.walks += 1
            _add_explanation_line(explain_lines, play_description_prefix, "WALK")
        elif result.is_hit_by_pitch:
            obp_counters.hit_by_pitches += 1
            _add_explanation_line(explain_lines, play_description_prefix, "HBP")
        elif any(modifier.is_sacrifice_fly for modifier in play.modifiers):
            obp_counters.sacrifice_flys += 1
            _add_explanation_line(explain_lines, play_description_prefix, "SF, AB")
        elif result.is_at_bat:
            _add_explanation_line(explain_lines, play_description_prefix, "AB")
        else:
            _add_explanation_line(explain_lines, play_description_prefix, "Unused for OBP")

    numerator = obp_counters.hits + obp_counters.walks + obp_counters.hit_by_pitches
    denominator = obp_counters.at_bats + obp_counters.walks + obp_counters.hit_by_pitches + obp_counters.sacrifice_flys
    try:
        on_base_percentage = numerator / denominator
    except ZeroDivisionError:
        on_base_percentage = 0.0

    measurement = "COBP" if is_conditional else "OBP"
    explain_lines.insert(0, f"{player.name}: {measurement} = {round(on_base_percentage, 3)}")
    explain_lines.append(
        f"  > hits={obp_counters.hits} + walks={obp_counters.walks} + hit_by_pitches={obp_counters.hit_by_pitches} == {numerator}"  # noqa: E501
    )
    explain_lines.append(
        f"  > at_bats={obp_counters.at_bats} + walks={obp_counters.walks} + hit_by_pitches={obp_counters.hit_by_pitches} + sacrifice_flys={obp_counters.sacrifice_flys} == {denominator}"  # noqa: E501
    )
    explain_lines.append("")
    if explain:
        print("\n".join(explain_lines))

    return on_base_percentage


def _add_explanation_line(explain_lines: list[str], play_description_prefix: str, resultant: str) -> None:
    explain_lines.append(f"{play_description_prefix} => {resultant}")


def _get_play_description_prefix(play: Play) -> str:
    """Build a descriptive play prefix."""
    play_description_prefix = f"- {play.result.name}"
    if play.modifiers:
        modifiers = "/".join(modifier.name for modifier in play.modifiers)
        play_description_prefix = f"{play_description_prefix}/{modifiers}"

    return f"{play_description_prefix} ({play.play_descriptor})"


def _get_other_plays_on_base_in_inning(play: Play, innings_plays: list[Play]) -> Iterator[Play]:
    for inning_play in innings_plays:
        result = inning_play.result
        if any([result.is_hit, result.is_walk, result.is_hit_by_pitch]) and play != inning_play:
            yield inning_play
