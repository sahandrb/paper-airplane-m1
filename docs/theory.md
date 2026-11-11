# Theory

The flight model is the four-state point mass in Robert F. Stengel, *Flight Dynamics* (2005), Example 1.3-1. Lift and drag coefficients stay at the constant \((L/D)_{\max}\) pair. There is no new force in the window.

## State and path

The state is true airspeed \(V\), flight-path angle \(\gamma\), altitude \(h\), and range \(r\). Dynamic pressure is \(\tfrac{1}{2}\rho V^2\). Drag and the gravity component change \(V\). Lift and the gravity component change \(\gamma\). The kinematics are \(\dot h = V\sin\gamma\) and \(\dot r = V\cos\gamma\).

The drawn pitch is kinematic:

\[
\theta = \alpha_* + \gamma
\]

\(\alpha_* = C_{L*}/C_{L\alpha}\) is fixed. The model has no pitch inertia, so it does not contain \(I_y\), \(C_m\), or a pitching-moment arm.

## Two expressions for \(V*\)

Equilibrium glide uses \(\tan\gamma_* = -C_D/C_L\), so \(\gamma_*\) is negative.

The speed used in the program is the vertical balance: lift and drag together support the weight in the descent,

\[
V_* = \sqrt{\frac{2mg}{\rho S(C_L\cos\gamma_* - C_D\sin\gamma_*)}}.
\]

The same glide also satisfies the lift balance \(L = mg\cos\gamma_*\),

\[
V_* = \sqrt{\frac{2mg\cos\gamma_*}{\rho S C_L}}.
\]

On this equilibrium the two expressions agree. The code takes the vertical-balance value. Computed: \(V_* \approx 3.549\,\mathrm{m/s}\), \(\alpha_* \approx 9.767^\circ\), \(L/D \approx 5.513\).

## Phugoid

The 2×2 Jacobian of \((\dot V, \dot\gamma)\) is evaluated at \((V_*, \gamma_*)\). Its eigenvalues are about \(-0.739 \pm 3.834\,i\). The damped period is \(T = 2\pi/\mathrm{Im}(\lambda) \approx 1.639\,\mathrm{s}\) and the damping ratio is \(\zeta \approx 0.189\). Neither number is typed in; both come from that matrix.

Lanchester's drag-free period is \(\pi\sqrt{2}\,V_*/g \approx 1.609\,\mathrm{s}\).

A nonlinear Reference run at \(V_*\) and \(\gamma_0 = 0\) (case b) has successive airspeed peaks about \(1.64\,\mathrm{s}\) apart, close to the linear period. The hybrid path integrates the exact \(\dot h\) and \(\dot r\) with the linear \(V(t)\) and \(\gamma(t)\). It does not loop. Case d, at \(3V_*\), drives the nonlinear model through a loop; the linear overlay stays a shallow wave. When \(|V_0-V_*|/V_* > 0.3\) or \(|\gamma_0-\gamma_*| > 15^\circ\), the window says the linear model is outside its small-perturbation region. Preset D meets the speed test. Preset A does not.

Total mechanical energy falls along a flight because drag removes energy. Kinetic and potential trade as the phugoid exchanges height and speed.

## Book rounding

Stengel's rounded figures are \(\alpha \approx 9.3^\circ\), \(L/D \approx 5.2\), \(V \approx 3.7\,\mathrm{m/s}\), and a period \(\approx 1.7\,\mathrm{s}\). The values above are the ones this program computes from the homework constants (\(S = 0.017\,\mathrm{m}^2\), \(AR = 0.86\), \(e = 0.9\), \(m = 0.003\,\mathrm{kg}\), \(g = 9.8\,\mathrm{m/s}^2\), \(\rho = 1.225\,\mathrm{kg/m}^3\), \(C_{D0} = 0.02\)). The professor's MATLAB script is the comparison, not a second set of coefficients.

## What the model leaves out

Reference integration runs to \(t = 6\,\mathrm{s}\) with no ground event, so altitude may be negative. Physical flight stops at the downward crossing of \(h = 0\).

The coefficients are constant. There is no stall model. A real paper wing at low Reynolds number is not this idealisation, and Stengel's note that a paper wing may buckle above about \(5\,\mathrm{m/s}\) is a warning only. Case d remains a numerical demonstration. Monte Carlo speed and angle scatter is an assumption for a hand throw. It is not Stengel data.
