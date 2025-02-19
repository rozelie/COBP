"""Calculate SP (Slugging Percentage) stats from game data."""
from dataclasses import dataclass, field

from pyretrosheet.models.game import Game
from pyretrosheet.models.play import Play
from pyretrosheet.models.player import Player

from cobp.stats.conditions import ConditionFunction, is_conditional_play, is_leadoff_play, is_sequential_play
from cobp.stats.stat import Stat
from cobp.utils import TEAM_PLAYER_ID, get_players_plays


@dataclass
class SP(Stat):
    """Slugging Percentage."""

    singles: int = 0
    doubles: int = 0
    triples: int = 0
    home_runs: int = 0
    at_bats: int = 0
    explanation: list[str] = field(default_factory=list)
    game_to_stat: dict[str, "SP"] = field(default_factory=dict)

    @property
    def numerator(self) -> int:
        return sum([self.singles, 2 * self.doubles, 3 * self.triples, 4 * self.home_runs])

    @property
    def denominator(self) -> int:
        return self.at_bats

    def add_arithmetic(self) -> None:
        numerator = f"*1 * 1B={self.singles} + 2 * 2B={self.doubles} + 3 * 3B={self.triples} + 4 * HR={self.home_runs} = {self.numerator}*"  # noqa
        denominator = f"*AB={self.at_bats}*"
        self.explanation.extend([numerator, denominator])

    @property
    def value(self) -> float:
        try:
            return self.numerator / self.denominator
        except ZeroDivisionError:
            return 0.0


PlayerToSP = dict[str, SP]


def get_player_to_sp(games: list[Game], players: list[Player]) -> PlayerToSP:
    return _get_player_to_sp(games, players, condition=None)


def get_player_to_csp(games: list[Game], players: list[Player]) -> PlayerToSP:
    """Conditional Slugging Percentage."""
    return _get_player_to_sp(games, players, condition=is_conditional_play)


def get_player_to_ssp(games: list[Game], players: list[Player]) -> PlayerToSP:
    """Sequential Slugging Percentage."""
    return _get_player_to_sp(games, players, condition=is_sequential_play)


def get_player_to_lsp(games: list[Game], players: list[Player]) -> PlayerToSP:
    """Leadoff Slugging Percentage."""
    return _get_player_to_sp(games, players, condition=is_leadoff_play)


def _get_player_to_sp(games: list[Game], players: list[Player], condition: ConditionFunction | None) -> PlayerToSP:
    player_to_sp = {player.id: _get_sp(games, player, condition=condition) for player in players}
    player_to_sp[TEAM_PLAYER_ID] = _get_teams_sp(player_to_sp)
    return player_to_sp


def _get_sp(games: list[Game], player: Player, condition: ConditionFunction | None) -> SP:
    sp = SP()
    for game, plays in get_players_plays(games, player):
        game_sp = SP()
        for play in plays:
            if condition:
                is_condition = condition(game, play)
                if not is_condition.is_met:
                    sp.add_play(play, resultant=is_condition.reason, color="red")
                    continue

            _increment_sp_counters(play, sp, game_sp)
            sp.add_play(play)

        sp.game_to_stat[game.id.raw] = game_sp

    sp.add_arithmetic()
    return sp


def _increment_sp_counters(play: Play, sp: SP, game_sp: SP) -> None:
    if play.is_an_at_bat():
        sp.at_bats += 1
        game_sp.at_bats += 1

    if play.is_single():
        sp.singles += 1
        game_sp.singles += 1
    elif play.is_double():
        sp.doubles += 1
        game_sp.doubles += 1
    elif play.is_triple():
        sp.triples += 1
        game_sp.triples += 1
    elif play.is_home_run():
        sp.home_runs += 1
        game_sp.home_runs += 1


def _get_teams_sp(player_to_sp: PlayerToSP) -> SP:
    team_sp = SP()
    for sp in player_to_sp.values():
        team_sp.singles += sp.singles
        team_sp.doubles += sp.doubles
        team_sp.triples += sp.triples
        team_sp.home_runs += sp.home_runs
        team_sp.at_bats += sp.at_bats
        for game_id, game_sp in sp.game_to_stat.items():
            if game_id not in team_sp.game_to_stat:
                team_sp.game_to_stat[game_id] = SP()

            team_game_sp = team_sp.game_to_stat[game_id]
            team_game_sp.singles += game_sp.singles
            team_game_sp.doubles += game_sp.doubles
            team_game_sp.triples += game_sp.triples
            team_game_sp.home_runs += game_sp.home_runs
            team_game_sp.at_bats += game_sp.at_bats

    return team_sp
