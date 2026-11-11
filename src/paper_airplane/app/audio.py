"""Airflow loops and the launch whoosh.

A missing device or file logs a warning and leaves the window silent.
The level function does not touch the mixer.
"""

from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)

MASTER_DEFAULT = 0.8
SLEW_FLIGHT_S = 0.05
SLEW_QUIET_S = 0.3


def audio_levels(v_m_s: float, v_star: float) -> tuple[float, float]:
    """Low and high loop gains for a true airspeed, before the master gain.

    ``V_ref`` is ``3 V*``. The extra loudness and the high-loop weight follow
    ``(V / V_ref)^2``, clamped to the unit interval.
    """
    v_ref = 3.0 * v_star
    if v_ref <= 0.0:
        ratio = 0.0
    else:
        ratio = min(1.0, max(0.0, v_m_s / v_ref))
    volume = 0.12 + 0.78 * ratio * ratio
    return ((1.0 - ratio) * volume, ratio * volume)


def _sound_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "assets" / "sound"


class FlightAudio:
    """Two seamless loops plus one whoosh. Volumes slew; the loops stay running."""

    def __init__(self) -> None:
        self.master = MASTER_DEFAULT
        self.muted = False
        self.enabled = False
        self._low = None
        self._high = None
        self._whoosh = None
        self._low_vol = 0.0
        self._high_vol = 0.0

    def start(self) -> None:
        """Open the mixer and start both loops at silence. Failure stays quiet."""
        try:
            import pygame

            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.set_num_channels(3)
            folder = _sound_dir()
            low = pygame.mixer.Sound(str(folder / "airflow_loop.wav"))
            high = pygame.mixer.Sound(str(folder / "airflow_loop_high.wav"))
            whoosh = pygame.mixer.Sound(str(folder / "launch_whoosh.wav"))
            low_channel = pygame.mixer.Channel(0)
            high_channel = pygame.mixer.Channel(1)
            low_channel.play(low, loops=-1)
            high_channel.play(high, loops=-1)
            low_channel.set_volume(0.0)
            high_channel.set_volume(0.0)
            self._low = low_channel
            self._high = high_channel
            self._whoosh = whoosh
            self.enabled = True
        except Exception as exc:
            log.warning("Flight audio is off: %s", exc)
            self.enabled = False

    def play_whoosh(self) -> None:
        """Play the launch one-shot. A mute or a dead mixer skips it."""
        if not self.enabled or self.muted or self._whoosh is None:
            return
        try:
            import pygame

            channel = pygame.mixer.Channel(2)
            channel.set_volume(self.master)
            channel.play(self._whoosh)
        except Exception as exc:
            log.warning("Launch whoosh did not play: %s", exc)

    def update(self, phase: str, v_m_s: float, v_star: float, dt_s: float) -> None:
        """Aim the loops at this frame's airspeed, or fade them out off the rail."""
        if not self.enabled or self._low is None or self._high is None:
            return
        if phase == "playing":
            if self.muted:
                low_target, high_target = 0.0, 0.0
            else:
                low_target, high_target = audio_levels(v_m_s, v_star)
                low_target *= self.master
                high_target *= self.master
            tau = SLEW_FLIGHT_S
        else:
            low_target, high_target = 0.0, 0.0
            tau = SLEW_QUIET_S
        self._low_vol = _approach(self._low_vol, low_target, dt_s, tau)
        self._high_vol = _approach(self._high_vol, high_target, dt_s, tau)
        try:
            self._low.set_volume(self._low_vol)
            self._high.set_volume(self._high_vol)
        except Exception as exc:
            log.warning("Flight audio volume failed: %s", exc)
            self.enabled = False

    def toggle_mute(self) -> bool:
        self.muted = not self.muted
        return self.muted


def _approach(current: float, target: float, dt_s: float, tau_s: float) -> float:
    if tau_s <= 0.0 or dt_s <= 0.0:
        return target
    step = min(1.0, dt_s / tau_s)
    return current + (target - current) * step
