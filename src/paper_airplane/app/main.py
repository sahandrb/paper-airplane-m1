"""Pygame shell: playback, phugoid, Monte Carlo, the heatmap, and export."""

from __future__ import annotations

import math
import os
import time
from pathlib import Path
from dataclasses import replace

import pygame

from paper_airplane.app.about import ABOUT_LINES, CAPTION, CREDIT, FOOTER, HINT
from paper_airplane.app.actors import draw_pose, draw_preview_path, load_flight_art
from paper_airplane.app.background import draw_world, load_scenery, project_root
from paper_airplane.app.camera import follow_camera, prelaunch_camera
from paper_airplane.app.dock import draw_buckle_banner, draw_dock, hit_test, value_from_pointer
from paper_airplane.app.hud import (
    draw_assumption,
    draw_heatmap_view,
    draw_hybrid,
    draw_legend,
    draw_progress,
    draw_reference_ground,
    draw_results,
    draw_scatter,
    draw_telemetry,
    draw_trails,
    legend_scroll_hit,
    result_hits,
)
from paper_airplane.app.prelaunch import (
    LaunchInputs,
    apply_preset,
    default_inputs,
    linear_model_outside,
    solver_mode,
    step_launch,
    toggle_mode,
)
from paper_airplane.app.theme import (
    ACCENT,
    DIM,
    PANEL,
    PANEL_ALPHA,
    TEXT,
    WARNING,
    label_font,
    label_font_fitting,
)
from paper_airplane.analysis import HeatmapCache, Overlays, ensure_heatmap
from paper_airplane.config import DEFAULT_CONFIG, Config
from paper_airplane.equilibrium import gamma_star_rad, v_star
from paper_airplane.export import write_run_table
from paper_airplane.linearize import hybrid_path
from paper_airplane.playback import advance_time, cycle_speed, launch_sample, points_until, sample_at
from paper_airplane.plots import (
    write_energy,
    write_heatmap,
    write_monte_histogram,
    write_phugoid_compare,
    write_reference_plots,
    write_run_path,
)
from paper_airplane.simulation import HeatmapResult, Trajectory, cases_abcd, monte_carlo, preview
from paper_airplane.trails import (
    Session,
    add_finished_reference,
    begin_trail,
    cleared,
    mc_legend_line,
    paint_active,
    returned,
    scroll_legend,
    shows_reference_ground,
)

_TARGET_FPS = 60


def run_app(
    config: Config | None = None,
    *,
    frame_limit: int | None = None,
    splash_s: float = 2.0,
) -> int:
    """Open the 1280x720 window and run until the user quits.

    ``frame_limit`` closes the window after that many frames. The environment
    variable ``PAPER_AIRPLANE_FRAME_LIMIT`` does the same, so a check can open
    the window and return.
    """
    config = DEFAULT_CONFIG if config is None else config
    if frame_limit is None:
        raw_limit = os.environ.get("PAPER_AIRPLANE_FRAME_LIMIT")
        if raw_limit:
            frame_limit = int(raw_limit)
    raw_splash = os.environ.get("PAPER_AIRPLANE_SPLASH_S")
    if raw_splash:
        splash_s = float(raw_splash)

    pygame.display.init()
    pygame.font.init()
    try:
        return _loop(config, frame_limit=frame_limit, splash_s=splash_s)
    finally:
        pygame.quit()


def _loop(config: Config, *, frame_limit: int | None, splash_s: float) -> int:
    width = config.window_width_px
    height = config.window_height_px
    try:
        screen = pygame.display.set_mode((width, height))
    except pygame.error as exc:
        print(f"Could not open the flight-lab window: {exc}")
        return 1
    pygame.display.set_caption(CAPTION)
    pygame.key.set_repeat(180, 40)
    scenery = load_scenery()
    art = load_flight_art(scenery.launcher, project_root(), config)
    for message in scenery.warnings + art.warnings:
        print(message)
    camera = prelaunch_camera(config)
    inputs = default_inputs(config)
    preview_path, cache_key = _refresh_preview(None, None, inputs, config)
    session = Session()
    overlays = Overlays()
    heatmap_cache = HeatmapCache()
    dragging: str | None = None
    clock = pygame.time.Clock()
    showing_splash = splash_s > 0.0
    splash_deadline = time.perf_counter() + splash_s
    about_open = False
    quit_prompt = False
    show_minimap = False
    frames = 0

    while True:
        dt = min(clock.tick(_TARGET_FPS) / 1000.0, 0.05)
        if showing_splash and time.perf_counter() >= splash_deadline:
            showing_splash = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return 0
            if showing_splash and event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                showing_splash = False
                continue
            if event.type == pygame.MOUSEWHEEL and legend_scroll_hit(pygame.mouse.get_pos()):
                session.book = scroll_legend(session.book, -event.y, config)
                continue
            locked = about_open or quit_prompt
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and not locked:
                inputs, session, dragging, finished = _on_click(
                    inputs,
                    session,
                    event.pos,
                    config,
                    screen.get_width(),
                    screen.get_height(),
                    overlays,
                    heatmap_cache,
                    screen,
                )
                if finished:
                    return 0
            elif event.type == pygame.MOUSEMOTION and dragging is not None and not locked:
                if session.phase != "playing":
                    inputs = _set_slider(inputs, dragging, event.pos[0], config, screen.get_height())
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                dragging = None
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_m and not about_open and not quit_prompt:
                    show_minimap = not show_minimap
                    continue
                inputs, session, about_open, quit_prompt, finished = _on_flight_key(
                    event.key,
                    inputs,
                    session,
                    config,
                    about_open,
                    quit_prompt,
                    overlays,
                    heatmap_cache,
                    screen,
                )
                if finished:
                    return 0
        if inputs.mode == "heatmap" and not showing_splash and (heatmap_cache.grid is None or heatmap_cache.force):
            def _heatmap_progress(done: int, total: int) -> None:
                draw_progress(screen, "Landing-range grid", 0.0 if total == 0 else done / total)
                pygame.display.flip()
                pygame.event.pump()

            ensure_heatmap(heatmap_cache, config, _heatmap_progress)
        if session.phase != "playing":
            preview_path, cache_key = _refresh_preview(preview_path, cache_key, inputs, config)
        session = _advance(session, dt, overlays)
        if session.phase == "prelaunch":
            camera = prelaunch_camera(config)
        elif session.flight is not None:
            played = sample_at(session.flight, session.t_sim)
            camera = follow_camera(camera, played.r, played.h, dt, config)
        _draw_frame(
            screen,
            camera,
            config,
            scenery,
            art,
            inputs,
            preview_path,
            session,
            showing_splash=showing_splash,
            about_open=about_open,
            quit_prompt=quit_prompt,
            overlays=overlays,
            heatmap=heatmap_cache.grid,
            show_minimap=show_minimap,
        )
        pygame.display.flip()
        frames += 1
        if frame_limit is not None and frames >= frame_limit:
            return 0


def _refresh_preview(
    trajectory: Trajectory | None,
    cache_key: tuple[float, float, str] | None,
    inputs: LaunchInputs,
    config: Config,
) -> tuple[Trajectory, tuple[float, float, str]]:
    """Integrate only when V0, gamma0, or the mode changes."""
    fresh = (round(inputs.v0_m_s, 5), round(inputs.gamma0_deg, 5), inputs.mode)
    if trajectory is not None and fresh == cache_key:
        return trajectory, fresh
    path = preview(inputs.v0_m_s, math.radians(inputs.gamma0_deg), solver_mode(inputs.mode), config)
    return path, fresh


def _on_pointer(
    inputs: LaunchInputs,
    pos: tuple[int, int],
    config: Config,
    height: int,
) -> tuple[LaunchInputs, str | None]:
    name = hit_test(pos, mode=inputs.mode, height=height)
    if name == "mode":
        return toggle_mode(inputs), None
    if name is not None and name.startswith("preset-"):
        return apply_preset(inputs, name[-1], config), None
    if name is not None and (name.startswith("slider-") or name.startswith("scatter-")):
        return _set_slider(inputs, name, pos[0], config, height), name
    return inputs, None


def _set_slider(inputs: LaunchInputs, name: str, x: int, config: Config, height: int) -> LaunchInputs:
    value = value_from_pointer(name, x, config, height)
    if name == "slider-v0":
        return replace(inputs, v0_m_s=value)
    if name == "scatter-n":
        return replace(inputs, n_throws=int(value))
    if name == "scatter-sv":
        return replace(inputs, sigma_v_m_s=value)
    if name == "scatter-sg":
        return replace(inputs, sigma_gamma_deg=value)
    return replace(inputs, gamma0_deg=value)


def _apply_launch_key(key: int, inputs: LaunchInputs, config: Config) -> LaunchInputs:
    if key == pygame.K_LEFT:
        return step_launch(inputs, config, gamma_steps=-1)
    if key == pygame.K_RIGHT:
        return step_launch(inputs, config, gamma_steps=1)
    if key in (pygame.K_UP, pygame.K_w):
        return step_launch(inputs, config, v_steps=1)
    if key in (pygame.K_DOWN, pygame.K_s):
        return step_launch(inputs, config, v_steps=-1)
    preset = {
        pygame.K_1: "a",
        pygame.K_KP_1: "a",
        pygame.K_2: "b",
        pygame.K_KP_2: "b",
        pygame.K_3: "c",
        pygame.K_KP_3: "c",
        pygame.K_4: "d",
        pygame.K_KP_4: "d",
    }.get(key)
    if preset is not None:
        return apply_preset(inputs, preset, config)
    if key == pygame.K_TAB:
        return toggle_mode(inputs)
    return inputs


def _advance(session: Session, dt_s: float, overlays: Overlays) -> Session:
    """Move simulation time and grow the active trail. A finished clip freezes."""
    if session.phase != "playing" or session.flight is None:
        return session
    t_final = float(session.flight.t[-1])
    session.t_sim = advance_time(session.t_sim, dt_s, session.speed, t_final)
    done = session.t_sim >= t_final - 1e-9
    played = sample_at(session.flight, session.t_sim)
    caption = None
    if done and session.flight_mode == "montecarlo" and overlays.scatter is not None:
        caption = mc_legend_line(
            overlays.v0,
            overlays.gamma_deg,
            overlays.sigma_v,
            overlays.sigma_g,
            overlays.n,
            overlays.scatter.mean_range_m,
            overlays.scatter.std_range_m,
        )
    session.book = paint_active(
        session.book,
        points_until(session.flight, session.t_sim, (played.r, played.h)),
        float(session.flight.r[-1]) if done else None,
        done,
        caption,
    )
    if done:
        session.phase = "frozen"
    return session


def _launch(
    session: Session,
    inputs: LaunchInputs,
    config: Config,
    overlays: Overlays,
    screen: pygame.Surface | None = None,
) -> Session:
    if inputs.mode == "heatmap":
        return session
    overlays.clear()
    if inputs.mode == "montecarlo":
        def _monte_progress(done: int, total: int) -> None:
            if screen is None:
                return
            draw_progress(screen, "Monte Carlo", 0.0 if total == 0 else done / total)
            pygame.display.flip()
            pygame.event.pump()

        overlays.scatter = monte_carlo(
            inputs.v0_m_s,
            math.radians(inputs.gamma0_deg),
            n=inputs.n_throws,
            sigma_v=inputs.sigma_v_m_s,
            sigma_gamma_deg=inputs.sigma_gamma_deg,
            config=config,
            progress=_monte_progress,
            n_samples=48,
        )
        overlays.n = inputs.n_throws
        overlays.sigma_v = inputs.sigma_v_m_s
        overlays.sigma_g = inputs.sigma_gamma_deg
        overlays.v0 = inputs.v0_m_s
        overlays.gamma_deg = inputs.gamma0_deg
    elif inputs.mode == "phugoid":
        overlays.hybrid = hybrid_path(
            inputs.v0_m_s - v_star(config),
            math.radians(inputs.gamma0_deg) - gamma_star_rad(config),
            config=config,
        )
    path = preview(inputs.v0_m_s, math.radians(inputs.gamma0_deg), solver_mode(inputs.mode), config)
    session.book = begin_trail(session.book, inputs.v0_m_s, inputs.gamma0_deg, inputs.mode, config)
    session.phase = "playing"
    session.t_sim = 0.0
    session.flight = path
    session.flight_v0 = inputs.v0_m_s
    session.flight_gamma_deg = inputs.gamma0_deg
    session.flight_mode = inputs.mode
    session.note = ""
    return session


def _abort(session: Session) -> Session:
    if session.phase != "playing" or session.flight is None:
        return session
    played = sample_at(session.flight, session.t_sim)
    session.book = paint_active(
        session.book,
        points_until(session.flight, session.t_sim, (played.r, played.h)),
        played.r,
        False,
    )
    session.phase = "frozen"
    return session


def _drop_cases(session: Session, config: Config) -> Session:
    flights = cases_abcd(config)
    speeds = {
        "a": (flights["a"].v[0], math.degrees(flights["a"].gamma[0])),
        "b": (flights["b"].v[0], math.degrees(flights["b"].gamma[0])),
        "c": (flights["c"].v[0], math.degrees(flights["c"].gamma[0])),
        "d": (flights["d"].v[0], math.degrees(flights["d"].gamma[0])),
    }
    book = session.book
    for tag in ("a", "b", "c", "d"):
        speed, glide = speeds[tag]
        book = add_finished_reference(book, tag.upper(), float(speed), float(glide), flights[tag], config)
    session.book = book
    return session


def _write_bundle(
    session: Session,
    inputs: LaunchInputs,
    overlays: Overlays,
    heatmap: HeatmapResult | None,
    *,
    csv: bool,
) -> Path:
    """Figures for the run. CSV and meta are written only for Export."""
    folder = write_reference_plots()
    paths = [folder / "figure1_path.png", folder / "figure2_histories.png"]
    if session.flight is not None:
        write_run_path(session.flight, folder)
        write_energy(session.flight, folder)
        paths.extend((folder / "last_run_path.png", folder / "energy.png"))
    if overlays.hybrid is not None and session.flight is not None:
        write_phugoid_compare(session.flight, overlays.hybrid, folder)
        paths.append(folder / "phugoid.png")
    if overlays.scatter is not None:
        write_monte_histogram(overlays.scatter, folder)
        paths.append(folder / "monte_carlo_hist.png")
    if heatmap is not None:
        write_heatmap(folder, heatmap)
        paths.append(folder / "heatmap.png")
    if csv:
        range_m = float(session.flight.r[-1]) if session.flight is not None else None
        t_final = float(session.flight.t[-1]) if session.flight is not None else None
        write_run_table(
            session.flight,
            folder,
            v0_m_s=inputs.v0_m_s,
            gamma0_deg=inputs.gamma0_deg,
            mode=inputs.mode,
            range_m=range_m,
            t_final=t_final,
        )
    session.note = str(folder)
    return folder


def _open_path(path: Path) -> None:
    if hasattr(os, "startfile"):
        os.startfile(path)  # type: ignore[attr-defined]
    else:
        print(path)


def _show_plots(
    session: Session,
    inputs: LaunchInputs,
    overlays: Overlays,
    heatmap: HeatmapResult | None,
) -> None:
    folder = _write_bundle(session, inputs, overlays, heatmap, csv=False)
    for path in folder.glob("*.png"):
        _open_path(path)


def _export(
    session: Session,
    inputs: LaunchInputs,
    overlays: Overlays,
    heatmap: HeatmapResult | None,
) -> None:
    folder = _write_bundle(session, inputs, overlays, heatmap, csv=True)
    _open_path(folder)


def _on_click(
    inputs: LaunchInputs,
    session: Session,
    pos: tuple[int, int],
    config: Config,
    width: int,
    height: int,
    overlays: Overlays,
    heatmap_cache: HeatmapCache,
    screen: pygame.Surface,
) -> tuple[LaunchInputs, Session, str | None, bool]:
    if session.phase == "frozen":
        for name, rect in result_hits(width, height):
            if rect.collidepoint(pos):
                return _on_result(name, inputs, session, config, overlays, heatmap_cache)
    name = hit_test(pos, mode=inputs.mode, height=height)
    if name == "recompute":
        heatmap_cache.force = True
        return inputs, session, None, False
    if name == "launch" and session.phase != "playing":
        return inputs, _launch(session, inputs, config, overlays, screen), None, False
    if name == "reset":
        overlays.clear()
        return inputs, cleared(session), None, False
    if name == "restart":
        overlays.clear()
        return inputs, returned(session), None, False
    if session.phase == "playing":
        return inputs, session, None, False
    changed, dragging = _on_pointer(inputs, pos, config, height)
    return changed, session, dragging, False


def _on_result(
    name: str,
    inputs: LaunchInputs,
    session: Session,
    config: Config,
    overlays: Overlays,
    heatmap_cache: HeatmapCache,
) -> tuple[LaunchInputs, Session, str | None, bool]:
    del config
    if name == "plots":
        _show_plots(session, inputs, overlays, heatmap_cache.grid)
        return inputs, session, None, False
    if name == "export":
        _export(session, inputs, overlays, heatmap_cache.grid)
        return inputs, session, None, False
    if name == "reset":
        overlays.clear()
        return inputs, cleared(session), None, False
    if name == "restart":
        overlays.clear()
        return inputs, returned(session), None, False
    return inputs, session, None, False


def _on_flight_key(
    key: int,
    inputs: LaunchInputs,
    session: Session,
    config: Config,
    about_open: bool,
    quit_prompt: bool,
    overlays: Overlays,
    heatmap_cache: HeatmapCache,
    screen: pygame.Surface,
) -> tuple[LaunchInputs, Session, bool, bool, bool]:
    if key == pygame.K_ESCAPE and session.phase == "playing" and not about_open and not quit_prompt:
        return inputs, _abort(session), about_open, quit_prompt, False
    about_open, quit_prompt, finished = _on_key(key, about_open, quit_prompt)
    if finished or about_open or quit_prompt:
        return inputs, session, about_open, quit_prompt, finished
    if key in (pygame.K_MINUS, pygame.K_LEFTBRACKET):
        session.speed = cycle_speed(session.speed, -1)
        return inputs, session, about_open, quit_prompt, False
    if key in (pygame.K_EQUALS, pygame.K_RIGHTBRACKET):
        session.speed = cycle_speed(session.speed, 1)
        return inputs, session, about_open, quit_prompt, False
    if key == pygame.K_p:
        _show_plots(session, inputs, overlays, heatmap_cache.grid)
        return inputs, session, about_open, quit_prompt, False
    if key == pygame.K_e:
        _export(session, inputs, overlays, heatmap_cache.grid)
        return inputs, session, about_open, quit_prompt, False
    if key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER) and session.phase != "playing":
        return inputs, _launch(session, inputs, config, overlays, screen), about_open, quit_prompt, False
    if key == pygame.K_r:
        overlays.clear()
        return inputs, cleared(session), about_open, quit_prompt, False
    if key == pygame.K_t:
        overlays.clear()
        return inputs, returned(session), about_open, quit_prompt, False
    if key == pygame.K_h and session.phase != "playing":
        return inputs, _drop_cases(session, config), about_open, quit_prompt, False
    if session.phase != "playing":
        inputs = _apply_launch_key(key, inputs, config)
    return inputs, session, about_open, quit_prompt, False


def _draw_frame(
    screen: pygame.Surface,
    camera: object,
    config: Config,
    scenery: object,
    art: object,
    inputs: LaunchInputs,
    trajectory: Trajectory,
    session: Session,
    *,
    showing_splash: bool,
    about_open: bool,
    quit_prompt: bool,
    overlays: Overlays,
    heatmap: HeatmapResult | None,
    show_minimap: bool = False,
) -> None:
    heatmap_on = inputs.mode == "heatmap" and heatmap is not None and not showing_splash
    if heatmap_on:
        screen.fill((8, 12, 22))
        draw_heatmap_view(screen, heatmap, config, v0_m_s=inputs.v0_m_s, gamma0_deg=inputs.gamma0_deg)
    else:
        draw_world(screen, camera, config, scenery)
        draw_reference_ground(screen, camera, inputs.mode, session.book)
        if session.phase == "prelaunch" and inputs.mode != "heatmap":
            draw_preview_path(screen, camera, config, trajectory)
        if overlays.scatter is not None:
            draw_scatter(screen, camera, config, overlays.scatter)
        draw_trails(screen, camera, config, session.book)
        if overlays.hybrid is not None:
            draw_hybrid(screen, camera, config, overlays.hybrid)
    ramp_inputs = inputs
    dart_world = None
    dart_theta = None
    show_arc = session.phase == "prelaunch"
    if session.phase != "prelaunch" and session.flight is not None:
        ramp_inputs = LaunchInputs(
            session.flight_v0,
            session.flight_gamma_deg,
            "physical" if session.flight_mode == "physical" else "reference",
        )
        played = sample_at(session.flight, session.t_sim)
        dart_world = (played.r, played.h)
        dart_theta = math.degrees(played.theta)
        seat_gamma = math.degrees(played.gamma)
    else:
        seat_gamma = inputs.gamma0_deg
    if not heatmap_on:
        draw_pose(
            screen,
            camera,
            config,
            art,
            ramp_inputs,
            dart_world=dart_world,
            dart_theta_deg=dart_theta,
            seat_gamma_deg=seat_gamma,
            show_arc=show_arc,
        )
    if showing_splash:
        _draw_splash(screen)
    else:
        landing = float(trajectory.r[-1]) if inputs.mode == "physical" and session.phase == "prelaunch" else None
        duration = float(trajectory.t[-1]) if landing is not None else None
        draw_dock(
            screen,
            inputs,
            config,
            landing_range_m=landing,
            flight_time_s=duration,
            speed=session.speed,
            show_readouts=session.phase == "prelaunch",
            show_reference=shows_reference_ground(inputs.mode, session.book),
        )
        draw_legend(screen, session.book, config)
        draw_buckle_banner(screen, inputs)
        sample = (
            sample_at(session.flight, session.t_sim)
            if session.flight is not None and session.phase != "prelaunch"
            else launch_sample(inputs.v0_m_s, math.radians(inputs.gamma0_deg), config)
        )
        landed = (
            session.phase == "frozen"
            and session.flight_mode == "physical"
            and session.flight is not None
            and session.t_sim >= float(session.flight.t[-1]) - 1e-6
        )
        phugoid = inputs.mode == "phugoid" or session.flight_mode == "phugoid"
        warned = phugoid and linear_model_outside(
            session.flight_v0 if session.phase != "prelaunch" else inputs.v0_m_s,
            session.flight_gamma_deg if session.phase != "prelaunch" else inputs.gamma0_deg,
            config,
        )
        draw_telemetry(
            screen,
            camera,
            config,
            sample,
            session.book,
            landed=bool(landed),
            show_minimap=show_minimap,
            phugoid=phugoid,
            outside=warned,
        )
        if overlays.scatter is not None:
            draw_assumption(screen, overlays.scatter)
        elif inputs.mode == "montecarlo":
            screen.blit(
                label_font(14).render("Assumption: illustrative hand-throw scatter", True, DIM),
                (16, 668),
            )
        if session.phase == "frozen" and session.flight is not None:
            draw_results(screen, session.flight, session.t_sim, session.flight_mode, sample)
        if session.note:
            note = label_font(13).render(session.note, True, WARNING)
            screen.blit(note, (16, 668))
        _draw_header(screen)
        if scenery.warnings or art.warnings:
            _draw_warnings(screen, scenery.warnings + art.warnings)
    _draw_footer(screen)
    if about_open:
        _draw_about(screen)
    if quit_prompt:
        _draw_quit(screen)


def _on_key(key: int, about_open: bool, quit_prompt: bool) -> tuple[bool, bool, bool]:
    """Apply one key. The third value is true when the user confirmed quit."""
    if key == pygame.K_a and not quit_prompt:
        return (not about_open, quit_prompt, False)
    if key == pygame.K_ESCAPE:
        if about_open:
            return (False, quit_prompt, False)
        if quit_prompt:
            return (about_open, False, False)
        return (about_open, True, False)
    if quit_prompt and key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_y):
        return (about_open, quit_prompt, True)
    return (about_open, quit_prompt, False)


def _draw_header(screen: pygame.Surface) -> None:
    font = label_font_fitting(CREDIT, screen.get_width() - 250, 13)
    line = font.render(CREDIT, True, TEXT)
    screen.blit(line, (12, 6))


def _draw_footer(screen: pygame.Surface) -> None:
    font = label_font(12)
    footer = font.render(FOOTER, True, TEXT)
    footer.set_alpha(190)
    screen.blit(
        footer,
        (screen.get_width() - footer.get_width() - 12, 694),
    )
    hint = font.render(HINT, True, DIM)
    screen.blit(hint, (12, 28))


def _draw_warnings(screen: pygame.Surface, warnings: tuple[str, ...]) -> None:
    font = label_font(13)
    y = 48
    for message in warnings:
        line = font.render(message, True, WARNING)
        screen.blit(line, (12, y))
        y += line.get_height() + 4


def _draw_splash(screen: pygame.Surface) -> None:
    shade = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    shade.fill((8, 12, 24, 150))
    screen.blit(shade, (0, 0))
    title = label_font(42).render(CAPTION, True, TEXT)
    credit_font = label_font_fitting(CREDIT, screen.get_width() - 80, 18)
    credit = credit_font.render(CREDIT, True, DIM)
    hint = label_font(16).render("any key continues", True, DIM)
    cx = screen.get_width() // 2
    cy = screen.get_height() // 2
    screen.blit(title, (cx - title.get_width() // 2, cy - 78))
    screen.blit(credit, (cx - credit.get_width() // 2, cy - 8))
    screen.blit(hint, (cx - hint.get_width() // 2, cy + 36))


def _draw_about(screen: pygame.Surface) -> None:
    title_font = label_font(26)
    body_font = label_font(20)
    fonts = [title_font, *([body_font] * (len(ABOUT_LINES) - 1))]
    rendered = [font.render(text, True, TEXT) for font, text in zip(fonts, ABOUT_LINES)]
    _blit_panel(screen, rendered, gap=8)


def _draw_quit(screen: pygame.Surface) -> None:
    font = label_font(22)
    rendered = [
        font.render("Quit the flight lab?", True, TEXT),
        label_font(18).render("Enter quits. Esc stays.", True, DIM),
    ]
    _blit_panel(screen, rendered, gap=14)


def _blit_panel(screen: pygame.Surface, lines: list[pygame.Surface], *, gap: int) -> None:
    width = max(line.get_width() for line in lines) + 64
    height = sum(line.get_height() for line in lines) + gap * (len(lines) - 1) + 56
    panel = pygame.Surface((width, height), pygame.SRCALPHA)
    panel.fill((*PANEL, PANEL_ALPHA))
    pygame.draw.rect(panel, ACCENT, panel.get_rect(), 1)
    y = 28
    for line in lines:
        panel.blit(line, ((width - line.get_width()) // 2, y))
        y += line.get_height() + gap
    screen.blit(panel, ((screen.get_width() - width) // 2, (screen.get_height() - height) // 2))
