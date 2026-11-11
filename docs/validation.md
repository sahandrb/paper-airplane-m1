# Validation

Numbers below are the ones the tests check. They are not re-tuned in the window.

## Reference and Physical, case a

Reference case a, launched at \(V_*\) and \(\gamma_*\), ends at \(t = 6\,\mathrm{s}\) with

- \(r(6\,\mathrm{s}) \approx 20.954\,\mathrm{m}\)
- \(h(6\,\mathrm{s}) \approx -1.801\,\mathrm{m}\)

Physical case a stops at the ground:

- landing range \(\approx 11.026\,\mathrm{m}\)
- flight time \(\approx 3.157\,\mathrm{s}\)

The landing range matches \(h_0 \times (L/D)\).

## Linear phugoid

At equilibrium the Jacobian eigenvalues are about \(-0.739 \pm 3.834\,i\). The linear period is about \(1.639\,\mathrm{s}\) and the damping ratio about \(0.189\). Lanchester's period is about \(1.609\,\mathrm{s}\). The case-b hybrid altitude stays within \(0.02\,\mathrm{m}\) of the nonlinear altitude. The linear state for case d does not loop.

## Picture geometry

The dart's measured centre of gravity on the source image is `(387.78, 119.31)` pixels. The program keeps the nearby pivot `(388, 119)`.

The catapult crop is the pillar `(130, 124, 140, 155)` and the ramp `(0, 0, 330, 128)`, with the painted pivot at `(199, 124)`. The pillar art is 155 pixels tall and represents \(2\,\mathrm{m}\), so the drawn pillar is 167 pixels:

\[
167\,\mathrm{px} / 2\,\mathrm{m} = 83.5\,\mathrm{px/m}.
\]

That scale is fixed. Screen \(y\) grows downward, and one scale is used on both axes.

## Heatmap

The landing-range grid is 31 angles by 41 speeds. Its peak is computed. It lands near \(16\,\mathrm{m}\), near \(9.4\,\mathrm{m/s}\) and \(-8^\circ\). The value \(16\,\mathrm{m}\) is not stored as a constant.

## Manual checklist

- The slider rotates the ramp to \(\gamma_0\) and the dart to \(\alpha_* + \gamma_0\).
- Presets A–D snap to the professor's launches.
- Playback runs at \(0.25\times\), \(1\times\), and \(4\times\).
- Trails persist. RESTART keeps them. RESET clears them and leaves the sliders.
- Reference samples below \(h = 0\) are dashed, with the below-ground caption.
- Before launch the launcher is near 8 percent of the width and the ground is near 76 percent of the height (\(548/720\)).
- The world fills the window. Controls sit in one bar on the dark ground, and the numbers sit in a small card at the top-right.
- The dart is about 110 pixels long, with its CG on the launch point. The launcher is about 170 pixels tall and stands on the ground. Zoom stays at \(83.5\,\mathrm{px/m}\).
- A 1 m scale bar and the "not to scale" label sit in the ground bar. The airplane picture does not cross the horizon.
- The footer is visible. A opens About.
- A missing art file still runs, using the drawn fallback.
- Phugoid shows the dashed linear path, \(\lambda\), \(T\), \(\zeta\), and the energy strip. Preset D shows the small-perturbation sentence. Preset A does not.
- Monte Carlo draws faint samples and one legend row, and says the scatter is an assumption.
- Heatmap replaces the world after the progress bar and rebuilds only from Recompute.
- Export writes `run.csv`, `meta.txt`, and the figures under `outputs/`.
