# Plan experimental — Finite-Shot Operating Windows for VD/SV
### Pre-Analysis Plan (PAP) para la sección experimental, alineado con el núcleo teórico
#### Versión 2 — revisión de robustez ante referee hostil de QIP
#### Versión 3 — metodología de selección de valores y criterios de inclusión (§5.5)
#### Versión 4 — cierre operativo 10/10: checklist de congelado, protocolo de fallo, presupuesto, readout y narrativa paper-ready

> **Propósito.** La sección experimental no debe demostrar el resultado genérico "VD le gana a SV en el régimen X". Debe **ejercitar el aparato**: medir directamente los objetos que el paper define (`b_m`, `c_m`, `v_m`, `s_m`, `C_m`, los cruces certificados, la escala log de copias, la cota de Le Cam) y contrastarlos con sus predicciones cerradas. Cada experimento aquí está anclado a una ecuación/teorema concreto del manuscrito. El criterio de éxito de la sección no es "la mitigación funciona", sino "la **forma** y, donde es posible, los **coeficientes** de las leyes certificadas se observan en datos".

---

## 0.0 Registro de correcciones (v1 → v2)

Convención de etiquetas usada en todo el documento:

- **`[CORREGIDO]`** — defecto de diseño o de redacción resuelto en el texto. Ninguna ejecución lo arregla; lo arregla escribirlo bien.
- **`[PRE-CONGELADO]`** — trabajo computacional, pero **precondición del hash del PAP**. La corrida es ejecución; haberla hecho *antes* de congelar es requisito de validez del diseño. Diferirlo invalida el estatus confirmatorio.
- **`[EJECUCIÓN]`** — legítimamente diferido a la corrida; no puede cerrarse en el congelado (típicamente por depender de acceso a hardware o de los propios datos de registro).

| # | Punto | Tipo | Secciones tocadas |
|---|-------|------|-------------------|
| 1 | `β₂ ↔ C`: P1 sobre-reclamaba "validar el coeficiente del remainder" | `[CORREGIDO]` | §2 (P1), §7.1, §8 (E1), §15 (Fig E1), §17 |
| 2 | Error de lectura × postselección SV (confound device-level no tratado) | `[CORREGIDO]` | §3, §4.1, §4.3, §10, §14 |
| 3 | Análisis de potencia prometido pero no ejecutado antes de fijar umbrales | `[PRE-CONGELADO]` | §11, §16 (Fase 0) |
| 4 | Colinealidad `β₀–β₁` propagada a la recuperación de `δ` | `[CORREGIDO]` (procedimiento) + `[PRE-CONGELADO]` (chequeo numérico) | §7.1, §7.3 |
| 5 | Sin control de error familiar entre 13 predicciones | `[CORREGIDO]` | §9.3, §9.5 (nuevo) |
| 6 | Gap de `λ₂` para E6 no pre-computado sobre instancias congeladas | `[PRE-CONGELADO]` | §4.1, §8 (E6), §16 (Fase 0) |
| 7 | Nivel 3 (hardware) sin argumento de factibilidad ni spec | `[PRE-CONGELADO]` (argumento de factibilidad) + `[EJECUCIÓN]` (spec con cola real) | §3, §16 (Fase 4) |
| 8 | Presupuesto de cómputo cualitativo | `[PRE-CONGELADO]` (estimado) + `[EJECUCIÓN]` (corrida) | §12 |
| m1 | Peso evidencial de E11 (Le Cam) sobrestimado | `[CORREGIDO]` | §8 (E11), §17 |
| m2 | Normalización de `O` no entraba en la batería de sensibilidad | `[CORREGIDO]` | §10 |

**Lectura crucial.** De estos diez ítems, solo dos partes (el *spec* de hardware del punto 7 y la *corrida* del punto 8) son ejecución pura. El resto o son defectos de diseño/redacción, o son cómputo que el PAP exige **terminado antes del hash**. Reclasificar un `[PRE-CONGELADO]` como "ya es ejecución, no cuenta contra el plan" es exactamente el movimiento que un referee castiga: congelar umbrales (`τ_δ=0.15`, pendientes objetivo) sin demostrar que el diseño los resuelve equivale a pre-registrar un diseño posiblemente subpotenciado, y entonces un nulo es indistinguible de baja potencia.

### Adiciones v2 → v3 (metodología de selección de valores)

| # | Punto | Tipo | Secciones |
|---|-------|------|-----------|
| 9 | Selección de instancias sin ensemble/semilla/criterios; riesgo de cherry-picking destapado por el cribado de `λ₂` | `[CORREGIDO]` (criterios + firewall) + `[PRE-CONGELADO]` (cómputo de la lista) | §5.5.1, §4.1, §9.1, §16 |
| 10 | Tolerancias `τ`, `τ_δ`, `δ_c` como placeholders "p. ej."; `δ_c` circular (ataba a un dato de salida) | `[CORREGIDO]` (principio + corrección de `δ_c`) + `[PRE-CONGELADO]` (números del pilot) | §5.5.2, §9.2 |
| 11 | Tasas del canal `c_AD`, `c_PD` sin regla de selección | `[CORREGIDO]` (regla) + `[PRE-CONGELADO]` (calibración) | §5.5.3, §5 |
| 12 | Ángulos QAOA `(γ,β)` sin regla (`ρ⋆` depende de ellos) | `[CORREGIDO]` (regla) + `[PRE-CONGELADO]` (optimización) | §5.5.1, §4.1 |

La nueva §5.5 centraliza la metodología de selección de **todas** las variables (tabla consolidada en §5.5.4), reclasifica cada una en derivada (D) / calibrada-por-pilot (P) / convención (C), y fija la regla anti-circularidad: ningún umbral confirmatorio ni criterio de inclusión depende de un estadístico de salida.


### Adiciones v3 → v4 (cierre operativo 10/10)

| # | Punto | Tipo | Secciones |
|---|-------|------|-----------|
| 13 | Error de consistencia `E13` en Nivel 2 | `[CORREGIDO]` | §12 |
| 14 | Falta de una tabla maestra de congelado verificable | `[CORREGIDO]` + `[PRE-CONGELADO]` | §0.1, §9.1, §13 |
| 15 | Pilot de potencia definido pero sin outputs obligatorios explícitos | `[CORREGIDO]` + `[PRE-CONGELADO]` | §0.1, §11 |
| 16 | Readout mitigation de SV todavía demasiado abstracta | `[CORREGIDO]` + `[EJECUCIÓN]` | §3, §4.3, §10, §11.1 |
| 17 | Presupuesto de cómputo sin tabla numérica obligatoria | `[CORREGIDO]` + `[PRE-CONGELADO]` | §0.1, §12 |
| 18 | Falta de plantilla de adjudicación predefinida | `[CORREGIDO]` | §9.3 |
| 19 | Falta de protocolo formal de fallo/refutación | `[CORREGIDO]` | §9.6 |
| 20 | Falta de separación explícita entre PAP completo y cuerpo del paper | `[CORREGIDO]` | §15.1 |
| 21 | Reproducibilidad textual, pero no suficientemente "scriptable" | `[CORREGIDO]` | §13 |
| 22 | Lenguaje residual de valores "provisionales" en umbrales confirmatorios | `[CORREGIDO]` | §9.2 |

**Criterio v4.** El PAP solo puede hashearse cuando todos los campos marcados como `[PRE-CONGELADO]` existan como archivos, tablas o configuraciones versionadas. Si un valor depende del pilot, no queda como "provisional": queda como **campo bloqueante de congelado** hasta que el pilot lo fije numéricamente. El plan no exige añadir más teoría ni más experimentos; exige convertir el diseño en un artefacto reproducible y auditable.

---

## 0.1 Design Freeze Checklist — artefactos obligatorios antes del hash `[PRE-CONGELADO]`

La siguiente tabla es el control maestro del PAP. Ningún análisis confirmatorio puede comenzar si falta uno de estos artefactos. Todos los archivos se versionan y se incluyen en el `freeze_manifest.json`.

| Bloque | Artefacto | Archivo esperado | Criterio de completitud antes del hash |
|---|---|---|---|
| PAP | Documento PAP final | `EXPERIMENTAL_PLAN.md` | Sin campos confirmatorios abiertos; numeración P/E/Fig consistente |
| Instancias | Lista incluida y rechazada con razón | `results/frozen/frozen_instances.csv` | Incluye candidatas, estado I1–I4, razón de rechazo, semilla maestra |
| Ángulos QAOA | `(γ, β)` por instancia | `results/frozen/frozen_qaoa_angles.csv` | Optimizador, tolerancia, reinicios y semilla documentados |
| Canal de ruido | `c_AD`, `c_PD`, infidelidad objetivo y snapshot | `config/noise_channel_spec.json` | Ratio anclado al backend/snapshot y magnitud resuelta |
| Rejillas | `p`, `B`, `M`, `T`, métodos, niveles | `config/grids.yaml` | Bracketing de `B_den`, décadas de `p`, `M` y endpoints cerrados |
| Potencia | Pilot de potencia | `results/pilot/pilot_power_report.md` + `.csv` | Fija `τ`, `τ_δ`, semianchos de exponentes, potencia P3/P4 |
| Espectro | Gap `λ₂(p)` por instancia | `results/frozen/lambda2_gap_table.csv` | Identifica instancia confirmatoria para E6 y rechazos por gap |
| WLS | Condición del diseño `[1,1/B,1/B²]` | `results/frozen/wls_condition_report.csv` | Si excede umbral, rejilla `B` corregida antes del hash |
| Recursos | Presupuesto computacional | `results/frozen/compute_budget_table.csv` | Celdas, shots efectivos, memoria, wall-time y decisión por nivel |
| Readout | Spec de mitigación de lectura | `config/readout_mitigation_spec.yaml` | Método primario, positividad, bootstrap de calibración, fuga inter-sector |
| Hardware | Nota de factibilidad Nivel 3 | `results/frozen/hardware_feasibility_note.md` | Decide si Nivel 3 queda cualitativo mínimo o se omite del confirmatorio |
| Adjudicación | Plantilla de tabla de decisión | `analysis/adjudication_template.csv` | P1–P13 con familia, nivel, estimador, CI, criterio y estado vacío |
| Fallos | Protocolo de fallo | `pap/failure_protocol.md` | Acciones predefinidas para fallos primarios/secundarios |
| Reproducibilidad | Manifest de congelado | `freeze_manifest.json` | SHA-256 de PAP, configs, scripts, outputs pre-congelados y commit |

**Regla de bloqueo.** Si cualquiera de estos artefactos falta, el estado del proyecto es `NO_FREEZE`. Si existe pero contiene campos `TBD`, `provisional`, `to be decided`, `p.ej.`, `example`, o valores confirmatorios no numéricos, el estado sigue siendo `NO_FREEZE`.

## 0.2 Frontera entre diseño, pilot y corrida final

- El **pilot pre-congelado** puede ajustar `T`, rejilla de `B`, número de puntos de `p`, tolerancias y decisión de degradar endpoints. Eso no contamina el análisis confirmatorio porque ocurre antes del hash y sin datos de registro.
- La **corrida confirmatoria** no puede cambiar instancias, canales, rejillas, clipping, normalización primaria, criterios de adjudicación, tolerancias ni familia primaria/secundaria.
- Cualquier análisis no listado en §2 o cualquier cambio posterior al hash se etiqueta como **exploratorio** y se separa de la tabla confirmatoria.

---

## 0. Reconciliación de notación (hacer ANTES de escribir nada)

Hay una colisión que un referee de QIP detectará en la primera página:

- El paper usa **`p`** = escala física de ruido (`ρ_p = ρ⋆ + pΔ + O(p²)`).
- La convención estándar de QAOA usa **`p`** = número de capas.

**Decisión a pre-registrar:** la profundidad de QAOA se denota **`L`** (layers) en todo el material experimental; `p` queda reservado exclusivamente para la escala de ruido. Añadir una nota explícita en el "Notation map" del paper. Otros símbolos a fijar de antemano: `B` (muestras estadísticas por método), `R` (presupuesto físico tras normalización de recurso), `M` (número de copias VD), `T` (réplicas independientes del estimador para estimar la MSE), `S` (operador de simetría).

---

## 1. Objetivos: cada experimento ↔ un resultado del paper

El plan valida, en orden de prioridad para la aceptación:

| # | Objeto teórico | Ancla en el paper | Tipo de validación |
|---|----------------|-------------------|--------------------|
| O1 | Descomposición MSE del cociente VD: `b² + (v+2bc)/B + ρ`, `|ρ|≤C/B²` | Thm `vd_quotient_certified_v4`, eq. `vd_mse_certified_v4` | **Forma** + coeficiente líder `v+2bc`; el coeficiente del remainder NO (ver §7.1) |
| O2 | `c_SV = 0` exacto vs `c_VD ≠ 0` | Thm `sv_quotient_law_v2`, eq. `sv_quotient_bias_zero_v14`; eq. `vd_c_v4` | Test discriminante de cero |
| O3 | `δ_VD = 2 Re⟨ψ⋆\|O Q⋆ L(ρ⋆)\|ψ⋆⟩` | Prop. `vd_delta_generator`, eq. `delta_vd_explicit` | Coeficiente (white-box) |
| O4 | `δ_SV = Tr(OPΔP) − μ⋆ Tr(PΔP)`, `c_SV=0` | Prop. `sv_delta_precise`, eq. `delta_sv_precise` | Coeficiente (white-box) |
| O5 | Concentración del denominador / umbral `B_den` | Lem. `denom_bernstein_v4`, eqs. `bernstein_denominator_v4`, `denom_sample_threshold_v4` | Régimen de validez |
| O6 | Escala logarítmica de copias `M_B = log B / (2\|log λ₂\|)` | Thm `mstar_log_scale_v4`, eq. `mstar_log_lambda2_v4` | Escalamiento |
| O7 | Cruce certificado + certificado `η = 4C/(gR₀²) < 1/2` | Thm `certified_crossing`, eqs. `eta_crossing_condition`, `crossing_interval` | Localización + certificado |
| O8 | Localización de ventana: `1/p` vs `1/p²` | Cor. `window_location_v10` | Escalamiento |
| O9 | Tricotomía de selección (dominancia uniforme vs cruce) | Thm `selection_trichotomy_v10` | Clasificación |
| O10 | Ruido de implementación multiplicativo (cancela en la razón; infla `v`) | Prop. `impl_noise_shift_v11`, eq. `impl_noise_vd_variance_v11` | Baseline falsable |
| O11 | Cota inferior de Le Cam `≥ 1/(8 R I_p)` y eficiencia del transcript aceptado | Thm `two_point_lower_bound`; Props. `explicit_ip_bernoulli_v5`, `accepted_transcript_efficiency_v10` | **Consistencia** del bound (no test empírico independiente; ver §8 E11) |
| O12 | Dominancia operacional Efron–Stein en ruido físico | Lem. `efron_stein_vd_v11`, Prop. `sector_es_operational_certificate_v12` | Certificado operativo |

O1–O4 son el **corazón** y constituyen la familia confirmatoria primaria (§9.5): validan que la maquinaria no es sobre-ingeniería. O5–O8 dan las predicciones estructurales discriminantes (familia secundaria). O9–O12 cierran el lazo con el resto del manuscrito (familia secundaria/descriptiva). O11, en particular, se degrada a **chequeo de consistencia** (ver §8 E11 y §17).

---

## 2. Registro de predicciones falsables (artefacto central)

Esta tabla es el contrato pre-registrado. Cada fila: predicción → estimador → valor/escala esperada → criterio de adjudicación. Se congela (hash + timestamp) **antes** de ejecutar.

| ID | Predicción cuantitativa | Estimador empírico | Criterio de CONFIRMACIÓN |
|----|-------------------------|--------------------|--------------------------|
| P1 | **Forma** MSE_VD(B) = b² + W₁/B + (curvatura), con W₁ = v+2bc | Ajuste WLS de MSE vs (1/B, 1/B²) | (i) intercepto `b²>0` recuperado; (ii) W₁ recupera `v+2bc` dentro del CI; (iii) el modelo con término `1/B²` gana al lineal puro (ΔAIC>2) para VD pero **no** para unmitigated. **No** se afirma que `β₂` iguale el coeficiente certificado `C` (ver §7.1) |
| P2 | b̂²_VD = b²_VD(p) (sesgo poblacional) | Plateau a B→∞ / cálculo white-box | `b²_pred ∈` CI bootstrap del intercepto |
| P3 | ĉ_VD = (μ_VD σ²_D − σ_ND)/D² ≠ 0 | Pendiente de (E[μ̂]−μ_pop) vs 1/B | Pendiente ≠ 0 (CI excluye 0) y dentro de τ del valor predicho |
| P4 | ĉ_SV = 0 | Igual, lado SV | TOST de equivalencia a 0 con margen pre-fijado |
| P5 | δ̂_VD recupera la fórmula del generador | Regresión de b_VD,∞(p) vs p, pendiente | δ_pred ∈ CI; error relativo < τ_δ. **CI propaga la incertidumbre de `β₀` del ajuste de P1** (ver §7.3) |
| P6 | δ̂_SV recupera Tr(OPΔP)−μ⋆Tr(PΔP) | Regresión de b_SV(p) vs p | δ_pred ∈ CI; error relativo < τ_δ. **Solo Nivel 1**; en Nivel 2 sujeta a calibración de lectura (ver §4.3) |
| P7 | Por debajo de B_den la cola del cociente explota; por encima la ley se sostiene | Curtosis/colas de μ̂ y desviación de P1 a ambos lados de B_den | Cambio de régimen detectable en ±factor 2 alrededor de B_den |
| P8 | M*(B) lineal en log B, pendiente 1/(2\|log λ₂\|) | argmin_M MSE(p,B,M); regresión M* vs log B | Pendiente_pred ∈ CI. **Requiere gap de `λ₂` pre-verificado** (§4.1, `[PRE-CONGELADO]`) |
| P9 | R̂_{VD↔SV} cae en [R₀(1−η), R₀(1+η)] | Raíz empírica de MSE_VD(R)−MSE_SV(R) | R̂* dentro del intervalo certificado |
| P10 | Escala de ventana: exponente de R₀ vs p es −2 (genérico) / −1 (costos líder iguales) | log R̂₀ vs log p, pendiente | Exponente_pred ∈ CI |
| P11 | Contracción común η_N=η_D no cambia b; infla v según eq. `impl_noise_vd_variance_v11` | b̂ y v̂ con/sin contracción inyectada | b invariante (CI overlap) y v̂ recupera fórmula |
| P12 | MSE_sel / L_LeCam ∈ rango predicho (≤64 conservador, ≤32 local); satura el Fisher del transcript | Cociente MSE observado / cota | Cociente dentro de cotas; saturación dentro de τ. **Chequeo de consistencia, no test independiente** (§8 E11) |
| P13 | Certificado Efron–Stein domina a SV en MSE total a `R ≥ R_ES` | MSE_VD,ES total vs MSE_SV en instancia física | Dominancia observada en el R certificado |

`τ`, `τ_δ`, márgenes TOST, y umbrales ΔAIC se fijan en §9.

---

## 3. Arquitectura en tres niveles (white-box → device-sim → hardware)

La validación de **coeficientes** exige conocer la verdad de base; la validación de **robustez** exige ruido realista. Tres niveles, con propósitos distintos y no intercambiables:

### Nivel 1 — White-box (density-matrix exacto)
- Canal de ruido de un parámetro **especificado analíticamente** ⇒ `ρ_p`, `Δ = L(ρ⋆)`, `δ_VD`, `δ_SV`, `D_M(p)`, `λ_j(p)`, `a(p)`, `σ²_N`, `σ²_D`, `μ_VD,M`, `μ_SV` **se calculan en forma cerrada** (simulación de matriz densidad, n ≤ 8).
- **Sin ruido de medición:** la postselección por peso de Hamming implementa `P` de forma exacta. Es el único nivel donde las afirmaciones de coeficiente de SV (`δ_SV`, `c_SV=0`) son limpias.
- Propósito: ground-truth para P2–P6, P10, P11; aquí se valida que los estimadores apuntan a los coeficientes correctos.
- Sin esto, no se puede afirmar "δ_VD coincide con el generador" — solo "hay un cruce".

### Nivel 2 — Device-simulation (Aer + noise model calibrado)
- Modelo de ruido extraído de un backend real (Aer `NoiseModel` de un `ibm_*` / FakeBackend). `ρ_p` **ya no es afín en p**; `p` se realiza por amplificación de ruido (gate folding / pulse stretch).
- **El modelo de ruido incluye error de lectura.** `[CORREGIDO]` Esto NO es benigno para SV: un bit-flip en la medición Z mueve un bitstring entre sectores de peso de Hamming y **contamina el conjunto aceptado** que define `P`, sesgando `μ_SV` y pudiendo imitar o enmascarar `δ_SV`. El pipeline aplica **calibración/mitigación de lectura** (matriz de asignación + unfolding tipo M3 o inversión regularizada) **antes** de la postselección (ver §4.3), y se reporta la fracción de fuga residual entre sectores. Para VD el error de lectura entra como una contracción multiplicativa en los tests de Hadamard — exactamente el caso de E10/P11 — y cancela a orden líder en la razón si `η_N=η_D`; esta **asimetría VD-robusto / SV-vulnerable** es un resultado del propio manuscrito, no un artefacto, y se enmarca como tal.
- Propósito: validar que las **leyes se sostienen en forma** (P1, P7, P8, P9, P13) cuando se rompe la afinidad exacta. Las afirmaciones de coeficiente de `δ_SV` aquí son, a lo sumo, *forma/robustez con lectura calibrada*, no validación de constante.

### Nivel 3 — Hardware (IBM, alcance acotado)
- Una o dos instancias, una rejilla de p reducida, presupuesto limitado. Es demostración de factibilidad, no de coeficientes.
- Propósito: mostrar que el cruce existe y que la concentración del denominador es operativamente relevante en un dispositivo real (P7, P9 cualitativos). Bootstrap por épocas de calibración.
- **Argumento de factibilidad obligatorio `[PRE-CONGELADO]`:** antes del hash se documenta (i) si `B_max` es alcanzable dada la deriva de calibración y la cola, (ii) si el cruce P9 es resoluble cualitativamente con el presupuesto de shots disponible, (iii) la estrategia de mitigación de lectura (que interactúa con la postselección SV, §4.3). Si este argumento no se puede sostener pre-congelado, **Nivel 3 se degrada a una única figura cualitativa** y se declara explícitamente como tal.
- **El spec concreto (device, cola, budget de shots por época) es `[EJECUCIÓN]`:** depende de acceso a la cola real y no puede cerrarse en el congelado.

> **Honestidad metodológica:** los coeficientes solo se "validan" en Nivel 1. Niveles 2–3 validan estructura y robustez. Esta distinción debe estar explícita en el paper; un referee castiga el reclamar validación de constantes en hardware ruidoso no controlado. En particular, `δ_SV` y `c_SV=0` se reclaman como coeficientes **únicamente en Nivel 1**; en Niveles 2–3 son cantidades de forma con lectura calibrada.

---

## 4. Sistema bajo prueba

### 4.1 Familia de instancias (una sola, para que VD y SV sean comparables sobre el mismo `(O, ρ⋆, ρ_p)`)

**QAOA con mixer XY (conservador de peso de Hamming)** sobre un problema con restricción de cardinalidad (p. ej. Max-κ-Cut con cardinalidad fija, o un modelo de anillo XY / "ring of disagrees" con magnetización fija). Razón técnica decisiva:

- La simetría verificable es `S = Σ_i Z_i` (magnetización total / peso de Hamming). El mixer XY **preserva** el sector; el estado QAOA ideal vive en un sector de peso fijo; el costo `H_C` es Z-diagonal y **conmuta** con `S`.
- Esto hace que `O` sea **simetría-compatible** (`PO = OP`), que es exactamente la hipótesis del paper (`sec. Symmetry verification`, "for a symmetry-compatible observable"). MaxCut estándar con `S = X^⊗n` **no** cumple esto (`H_C` Z-diagonal no conmuta con `X^⊗n`), y un referee lo notará. Usar XY-mixer evita el problema de raíz.
- SV se implementa **shot-level** sin ancilla ni perturbación: medir todos los qubits en base Z, calcular el peso de Hamming, postseleccionar (`A_s ∈ {0,1}` = peso correcto), evaluar `H_C` sobre bitstrings aceptados. Encaja término a término con `μ_SV = Tr(OPρ_pP)/Tr(Pρ_p)` (eq. `sv_population_v2`). Errores que cambian peso → detectables; errores en-sector → `δ_SV` residual. Mecanismo idéntico al del paper y a Kakkar et al. 2022 (que el paper ya cita). **Nota de validez:** esta correspondencia término-a-término es exacta solo bajo medición ideal (Nivel 1); con error de lectura (Niveles 2–3) requiere la calibración de §4.3.

**Tamaños:** n ∈ {4, 6, 8} qubits. Sector de peso fijo (p. ej. peso n/2).
**Profundidad:** L = 1 (principal); L = 2 como sensibilidad.
**Observable:** `O = H_C` normalizado a `‖O‖_∞ ≤ 1`.
**Estado ideal:** `ρ⋆ = |ψ_QAOA⟩⟨ψ_QAOA|` (puro ⇒ `Q⋆ = I − |ψ⋆⟩⟨ψ⋆|` bien definido para P5).
**Diversidad:** ≥ 5 instancias por tamaño (grafos/pesos distintos) para evitar conclusiones dependientes de un caso. Pre-seleccionadas y congeladas. **Ensemble, semilla, ángulos QAOA `(γ,β)` y criterios de inclusión a priori (I1–I4) con firewall anti-cherry-picking: ver §5.5.1.**

**Gap espectral `λ₂` `[PRE-CONGELADO]`.** El teorema de escala log de copias (O6/P8) exige `λ₂` (autovalor subdominante que gobierna la fuga de copias) **bien separado**. Para `n=4,6` el espectro de la derangement puede tener `λ₂` casi degenerado, volviendo la pendiente de M*(B) inestable. Por tanto, **antes del hash** se computa `λ₂(p)` para cada instancia congelada y cada `p` de la rejilla, y se reporta el gap. Se pre-registra un gap mínimo requerido; si `n=4,6` no lo cumplen, la instancia confirmatoria de E6 se fija en `n=8` con gap verificado. Sin este cómputo previo, E6 fija un objetivo de pendiente sin saber si es resoluble.

### 4.2 Implementación VD (controlled-derangement / Hadamard test)

- `M = 2` principal; `M ∈ {3,4,5}` para P8 (escala log de copias).
- M=2: `D_2 = Tr(ρ_p²)` vía SWAP test; `N_2 = Tr(O ρ_p²)` vía controlled-SWAP con medición de `O`. **Streams independientes** ⇒ `σ_ND = 0`, `σ²_N = 1−N²`, `σ²_D = 1−D²` (eqs. `hadamard_variances_v4`). Salidas en `{±1}`.
- Estimador clippeado `μ̂_VD,M^clip = N̂_M / max{D̂_M, D_M/2}` (eq. `clipped_quotient_v4`) — usar el clippeado como estimador primario, reportar también el ordinario (Remark "Ordinary versus clipped quotient").
- `K_{N,M} = 1`, `K_{D,M} = 2` (consistente con §sector del paper y con la cota de Bernstein de Hadamard).

### 4.3 Implementación SV

- Postselección por peso de Hamming en base Z (§4.1). `K_W = ‖O‖_∞ ≤ 1`.
- Estimador `μ̂_SV^clip = Z̄ / max{Ā, a/2}`.
- **Calibración de lectura (Niveles 2–3) `[CORREGIDO]`.** Antes de la postselección se estima la matriz de asignación (confusión) del dispositivo/modelo y se aplica mitigación de lectura (M3 / unfolding bayesiano iterativo, o inversión regularizada) sobre las cuentas por bitstring. La postselección de sector se aplica **sobre las cuentas corregidas**. Se reporta la **fracción de fuga inter-sector** estimada como diagnóstico, y se trata cualquier residual como confound conocido y cuantificado (no como `δ_SV` físico). En Nivel 1 este paso es identidad (sin ruido de medición).


#### 4.3.1 Protocolo operativo de readout mitigation para SV `[CORREGIDO]`

El método primario para Niveles 2–3 se fija en `config/readout_mitigation_spec.yaml` antes del hash. La especificación mínima obligatoria es:

| Elemento | Decisión pre-registrada |
|---|---|
| Método primario | M3 / matriz local de asignación con corrección de cuentas por bitstring o por marginales, según soporte del backend |
| Método de sensibilidad | inversión regularizada o Bayes iterativo, ejecutado solo como robustez |
| Positividad | si el método produce quasiprobabilidades negativas, se reportan; si se proyecta al simplex, la proyección se declara antes del hash |
| Postselección | se aplica sobre probabilidades/cuentas corregidas agregadas por sector de Hamming, no sobre bitstrings crudos |
| Incertidumbre | el bootstrap re-muestrea conjuntamente counts experimentales y matriz de calibración |
| Diagnóstico principal | fuga inter-sector antes y después de mitigación: `leakage_pre`, `leakage_post`, `Δμ_SV`, `ΔR_cross` |
| Regla de reporte | cualquier desplazamiento material de `μ_SV` o del cruce se reporta como sensibilidad, no se oculta |

**Definición del estimador en Niveles 2–3.** La mitigación de lectura es parte del estimador `μ̂_SV`, no una corrección post-hoc. Por tanto, toda incertidumbre asociada al calibrador de lectura entra al CI final de SV y a la comparación VD↔SV.

### 4.4 Baseline sin mitigar

- Media muestral directa de `O` en base Z (variable acotada). `c_0 = 0`, remainder exacto `C_0 = 0` (sirve de control: P1 debe dar W₂ ≈ 0 aquí).

---

## 5. El parámetro `p` y el canal de ruido

### Nivel 1 (afín exacto)
Canal de un parámetro `E_p` con `E_p(ρ⋆) = ρ⋆ + pΔ + O(p²)`, `Δ = L(ρ⋆)`. Opciones a fijar:
- **(a) Depolarizante por qubit** con tasa `∝ p` tras cada capa. `Δ` calculable.
- **(b) Amplitude damping + dephasing** con `γ = c_AD·p`, `λ = c_PD·p` (más realista, rompe la simetría de forma controlada ⇒ `δ_SV ≠ 0` genuino). Tasas `c_AD`, `c_PD` seleccionadas por la regla de §5.5.3: magnitud anclada a infidelidad objetivo en `p_max`, ratio anclado al `T1/T2` del backend de Nivel 2.

Recomendado: **(b)** como canal primario (da `δ_SV ≠ 0` y `δ_VD ≠ 0` simultáneos, el caso genérico de la Prop. `generic_toy_v10`), **(a)** como sensibilidad.

Para cada `p` en la rejilla, simulación de matriz densidad exacta ⇒ se extraen todos los coeficientes de base. `Δ` por diferencias finitas centradas en p (verificado contra forma analítica del canal).

**Rejilla de p:** ≥ 12 puntos log-espaciados en `(0, p_max]` con `p_max ≤ min{1/(4ε), 1/(4|θ|)}` análogo (mantener el espectro ordenado y las expansiones controladas, cf. eq. `pmax_toy_v4`). Cubrir al menos 1.5 décadas para resolver exponentes en P10.

### Nivel 2 (amplificación)
`p` = factor de amplificación de ruido (folding entero + interpolación, o stretch de pulso). `ρ_p` no afín; reportar `b_m(p)`, `s_m(p)` medidos, no asumidos.

---

## 5.5 Metodología de selección de valores y criterios de inclusión `[CORREGIDO]` + `[PRE-CONGELADO]`

Hasta v3 la lógica de selección de valores estaba **implícita y dispersa**, con calidad despareja: desde derivación real (`T`, `p_max`) hasta placeholders "p. ej." (tolerancias) y gaps sin regla (instancias, tasas de canal, ángulos QAOA). Esta sección la centraliza.

### 5.5.0 Principio de clasificación

Ningún valor congelado queda como "p. ej." tras el hash. Cada variable cae en una de tres clases de derivación, con su estado:

- **(D) Derivada** — sale de teoría/forma cerrada o de una cota; no es libre. *Estado: diseño.*
- **(P) Calibrada por pilot** — el número se fija con el pilot de §11 sobre la rejilla congelada, con margen. *Estado: `[PRE-CONGELADO]`.*
- **(C) Convención** — elección de normalización/representación; obligatoriamente sometida a sensibilidad (§10). *Estado: `[CORREGIDO]` + sensibilidad.*

**Regla transversal anti-circularidad.** Ningún umbral confirmatorio (§9.2) ni criterio de inclusión puede depender de un **estadístico de salida** (`b̂`, `ĉ`, `R̂₀`, ubicación del cruce, resultado de adjudicación). Los anclajes admisibles son solo: (i) la precisión alcanzable que reporte el pilot, (ii) una escala de relevancia física, o (iii) el ground-truth white-box (conocido exactamente en Nivel 1, por tanto independiente de los datos de registro).

### 5.5.1 Ensemble de instancias y criterios de inclusión

Es el gap más grave de v2 ("≥5 distintas, congeladas" sin ensemble, semilla ni criterios) y lo agrava el cribado de `λ₂` que introdujo la v2: cribar instancias abre la puerta a selección-sobre-resultado si no se separa explícitamente del cribado por precondición.

**Generador del ensemble (a fijar y hashear).** Familia de grafos (p. ej. `d`-regulares aleatorios o grafos ponderados con pesos de una distribución fija sobre `n` nodos), distribución de pesos, sector de peso fijo (`n/2`). Semilla maestra → generación determinista de instancias candidatas.

**Ángulos QAOA `(γ, β)`.** `ρ⋆` depende de ellos, así que su selección es parte del spec, no un detalle. Regla: optimizar `(γ,β)` sobre el costo **sin ruido** con un optimizador fijo (método + tolerancia + nº de reinicios) y **semilla fija**, por instancia; congelar los ángulos resultantes. Alternativa pre-registrable: ángulos transferidos de literatura para la familia, fijos. La regla elegida se declara antes de muestrear.

**Criterios de inclusión, aplicados a priori y en orden fijo, ANTES de cualquier pipeline de estimación:**
- **(I1)** Simetría-compatibilidad `PO=OP` — automática por construcción (XY-mixer, §4.1).
- **(I2)** No-trivialidad del estado ideal: `ρ⋆` genuinamente entrelazado / no-producto (umbral sobre una medida calculada en el estado **ideal**, p. ej. entropía de entrelazamiento de una bipartición > umbral). Excluye instancias degeneradas.
- **(I3)** Gap de `λ₂` ≥ umbral sobre el espectro de `ρ_p` en la rejilla de `p` (precondición del Thm de escala log, O6/P8). En Fase 0 Level-1 el umbral congelable es `relative_gap = (λ₁-λ₂)/λ₁ ≥ 0.1`, declarado en `config/grids.yaml`.
- **(I4)** Admisibilidad de `p_max`: la condición de espectro ordenado / control de expansión se sostiene sobre la rejilla.

**Firewall anti-cherry-picking (lo que mi arreglo de `λ₂` destapó).** Un criterio de inclusión es admisible **si y solo si** es evaluable desde el ground-truth white-box `(O, ρ⋆, ρ_p, canal)` **sin correr ningún muestreo/estimación**. I1–I4 lo son: son propiedades espectrales/estructurales del montaje físico. Cribar por `λ₂` (propiedad de `ρ_p`) **es legítimo** — es precondición de una hipótesis del teorema, no selección sobre resultado. Cribar por "el cruce cae en la banda predicha", "`ĉ_VD` salió grande", o cualquier salida de estimador **es inadmisible** y queda prohibido. La distinción se pre-registra explícitamente.

**Procedimiento.** Generar candidatas desde la semilla; aplicar I1–I4 en orden; tomar las primeras 5 por tamaño que pasen. **Congelar la lista incluida Y la lista rechazada con su razón de rechazo**, y reportar ambas en el artefacto — la transparencia sobre rechazos es lo que neutraliza la objeción de cherry-picking ante el referee.

**Instancia confirmatoria de E6.** Entre las incluidas, la de mayor gap de `λ₂` verificado (o `n=8` si los `n` menores degeneran). Elección sobre el gap espectral (precondición), declarada, nunca sobre la ubicación de `M*(B)`.

*Estado: ensemble, ángulos, I1–I4 y firewall son diseño (`[CORREGIDO]`); el cómputo de I2–I4 sobre las candidatas, que produce la lista congelada, es `[PRE-CONGELADO]`.*

### 5.5.2 Tolerancias `τ`, `τ_δ`, `δ_c`, semiancho de exponentes

Cada tolerancia se **deriva** de un anclaje declarado; no se elige:

- **`τ_δ`, `τ`, semiancho de exponentes — anclaje (i) precisión-pilot.** Se fijan al semiancho de CI que el pilot (§11) demuestre alcanzable con el diseño congelado, **más un margen pre-registrado**. No se elige 0.15 a priori: el pilot reporta el alcanzable y se congela `τ_δ` como ese valor + margen. Si el alcanzable no bate el target de relevancia física, se ajusta `T`/rejilla antes del hash o se degrada la predicción a inconclusa-por-diseño (declarándolo). *(P, `[PRE-CONGELADO]`.)*
- **`δ_c` (margen TOST para `c_SV=0`) — anclaje (iii) ground-truth, con corrección de circularidad.** La v2 lo ataba a `|c_VD|` **observado**, que es un estadístico de salida → circular. Corregido: `δ_c = f·|c_VD^white-box|` con `f` pre-registrado (con interpretación documentada, por ejemplo una década de separación estructural), usando el `c_VD` **exacto de Nivel 1**, independiente de los datos de registro. *(D, `[CORREGIDO]`.)*
- **ΔAIC > 2:** convención estándar de selección de modelo. *(C.)*

### 5.5.3 Tasas del canal de ruido `c_AD`, `c_PD`

El canal (b) (amplitude damping + dephasing, §5) estaba justificado en estructura pero sin regla para las tasas; sin criterio, dos referees verían dos físicas distintas. Regla:

- **Magnitud — anclaje a infidelidad objetivo en `p_max`.** Elegir `c_AD`, `c_PD` tal que a `p = p_max` la infidelidad efectiva por capa corresponda a un valor de dispositivo realista (p. ej. error de puerta 2q `~10⁻²–10⁻³`), de modo que la rejilla de `p` barra un rango físicamente interpretable, no arbitrario.
- **Estructura — ratio `c_AD : c_PD` anclado al backend de Nivel 2.** Fijar el cociente a la razón `T1/T2` (relajación vs decoherencia) de la calibración del `FakeBackend`/`ibm_*` usado en Nivel 2. Esto hace que el canal analítico de Nivel 1 y el modelo calibrado de Nivel 2 describan **la misma física**, dando continuidad a la validación white-box → device-sim.
- Pre-registrar la infidelidad objetivo y el snapshot de backend cuyo `T1/T2` ancla el ratio.

*Estado: la regla es diseño (`[CORREGIDO]`); leer el `T1/T2` del snapshot y resolver las constantes es `[PRE-CONGELADO]`; el snapshot del FakeBackend se congela con el PAP.*

### 5.5.4 Tabla consolidada de selección

| Variable | Regla de selección | Clase | Estado | Sección |
|----------|--------------------|-------|--------|---------|
| `T` | fórmula precisión→T; curtosis empírica; confirmada por pilot | P | `[PRE-CONGELADO]` (confirmación) | §6.1, §11 |
| `p_max` | cota de espectro ordenado / control de expansión | D | derivado | §5 |
| Rejilla `p` (#puntos, décadas) | log-espaciado, ≥12, ≥1.5 décadas para resolver exponentes; nº final por pilot | P | `[PRE-CONGELADO]` | §5, §11 |
| Rejilla `B` (endpoints, #) | log, ≥10 puntos, bracketing de `B_den`, nº de condición WLS < umbral | P | `[PRE-CONGELADO]` | §6.1, §7.3 |
| `M` | M=2 canónico + rango {2..5} para la pendiente de P8 | D/C | diseño | §4.2 |
| `n` | acotado por density-matrix exacta + chequeo de artefacto de tamaño | D | diseño | §4.1 |
| `κ` (3 defs) | enumeradas + justificadas + sensibilidad | C | `[CORREGIDO]` + sens. | §6.2, §10 |
| Clipping `D_M/2` | heredado de teoría (`clipped_quotient_v4`) + sensibilidad | D | diseño + sens. | §4.2, §10 |
| Norm. de `O` | convención + sensibilidad sobre `R₀` | C | `[CORREGIDO]` + sens. | §4.1, §10 |
| Instancias (ensemble, semilla, I1–I4) | ensemble + criterios a priori + firewall outcome | D+P | `[CORREGIDO]` + `[PRE-CONGELADO]` | §5.5.1 |
| Ángulos QAOA `(γ,β)` | optimizador fijo + semilla, sobre costo sin ruido | D+P | `[CORREGIDO]` + `[PRE-CONGELADO]` | §5.5.1 |
| `τ`, `τ_δ`, semiancho exp. | precisión-pilot + margen | P | `[CORREGIDO]` (principio) + `[PRE-CONGELADO]` (número) | §5.5.2, §9.2 |
| `δ_c` (TOST) | `f·|c_VD^white-box|`, `f` pre-registrado | D | `[CORREGIDO]` | §5.5.2, §7.2, §9.2 |
| `c_AD`, `c_PD` | infidelidad objetivo @ `p_max`; ratio ← `T1/T2` backend | D+P | `[CORREGIDO]` (regla) + `[PRE-CONGELADO]` (calibración) | §5.5.3 |
| ΔAIC > 2 | convención estándar | C | diseño | §9.2 |

---

## 6. Diseño de muestreo y normalización de recurso

### 6.1 Rejillas
- `B` (muestras por método): ≥ 10 puntos log-espaciados, `B ∈ [B_min, B_max]` con `B_max ~ 10⁵`. Asegurar puntos **por debajo y por encima** de `B_den` para P7.
- `T` (réplicas independientes del estimador completo por celda): `T = 2000` (Nivel 1–2) **como valor inicial, sujeto a confirmación por el pilot de potencia (§11, `[PRE-CONGELADO]`)**; suficiente para CI de MSE con error relativo objetivo < 5% bajo colas moderadas (ver §12). `T` reducido en Nivel 3.
- Celdas = (instancia × n × p × B × M × método).

### 6.2 Normalización de recurso `R` (punto crítico de equidad)
El cruce se compara en `R` físico, **no** en `B`. Pre-registrar:
- VD usa stream de numerador + denominador ⇒ `R_VD,M = 2 κ_M B` (Remark `resource_normalization_v13`).
- `κ_M` = costo físico por Hadamard test (definición pre-fijada: nº de puertas de dos qubits × factor de profundidad, o ejecuciones ponderadas). Para M copias, `κ_M` crece con el tamaño de la derangement.
- SV y unmitigated: `R = κ_0 B` (una corriente). SV además "gasta" shots rechazados ⇒ contabilizar todos los shots tomados, no solo aceptados.
- **Sensibilidad obligatoria (§10):** repetir todas las conclusiones de cruce bajo ≥ 3 definiciones de `κ` (conteo de circuitos, conteo de puertas 2q, wall-clock-equivalente). Un cruce que cambia de lado según la normalización es un resultado **honesto que hay que reportar**, no esconder.

---

## 7. Estimación e inferencia (cómo se extraen b, c, v, s, C de los datos)

Para cada celda se guarda el vector de `T` estimaciones `{μ̂_t}`. De ahí:

### 7.1 MSE y su descomposición (P1, P2) `[CORREGIDO]`
- `MŜE(p,B) = (1/T) Σ_t (μ̂_t − μ⋆)²` (μ⋆ exacto, conocido).
- A `p` fijo, ajuste por mínimos cuadrados ponderados (WLS) de `MŜE` sobre `{1/B, 1/B²}`:
  `MŜE = β₀ + β₁/B + β₂/B²`.
  Pesos = inverso de la varianza bootstrap de `MŜE` por punto.
- Mapeo a teoría: `β₀ ↔ b²`, `β₁ ↔ v + 2bc = ṽ`.
- **Qué valida P1 y qué NO.** `β₂` es un **coeficiente efectivo de curvatura**, no el coeficiente certificado del remainder `C`. Un término de orden superior (`C'/B³`) dentro del rango finito de `B` se disfraza de curvatura en `β₂`; y como la cota certificada es conservadora y unilateral, "`|β₂| ≲ C`" es un sanity check que casi cualquier cosa pasa. Por tanto P1 valida:
  1. **forma**: existe intercepto `b²>0` y la curvatura es *necesaria* para VD (modelo con `1/B²` gana al lineal puro, ΔAIC>2) pero **no** para unmitigated (control negativo, `β₂≈0`);
  2. **coeficiente líder**: `β₁` recupera `v+2bc` dentro del CI.
  **No** se afirma recuperar el coeficiente del remainder. El chequeo `|β₂|≲C` se reporta como **condición necesaria unilateral**, etiquetado como tal, no como confirmación de constante. §17 y la Fig E1 se redactan en consecuencia.
- **Diagnóstico opcional de estructura del remainder.** Para distinguir "verdadero `C/B²`" de "contaminación `B³`", ajustar sobre sub-rangos anidados de `B` y verificar estabilidad de `β₂`, o incluir un término `1/B³` y verificar que no absorbe la curvatura. Es análisis exploratorio (no confirmatorio), declarado en §9.4.

### 7.2 Coeficiente de sesgo del cociente `c_m` (P3, P4 — el test discriminante)
- Medir `E[μ̂_m](B) ≈ (1/T) Σ_t μ̂_t` en la rejilla de B.
- `μ_pop,m` = valor poblacional (white-box exacto en Nivel 1).
- Regresión de `(Ê[μ̂_m] − μ_pop,m)` sobre `1/B`: pendiente = `ĉ_m`.
- **VD:** predecir `c_VD = (μ_VD σ²_D − σ_ND)/D²` (eq. `vd_c_v4`); con streams independientes `= μ_VD(1−D²)/D²` (eq. `hadamard_c_v4`). Test: pendiente ≠ 0.
- **SV:** predecir `c_SV = 0` (eq. `sv_quotient_bias_zero_v14`). Test de **equivalencia** (TOST) contra margen `δ_c`. Esta asimetría (VD≠0, SV=0) es la firma estructural más limpia y barata de exhibir.

### 7.3 Coeficientes de primer orden `δ_VD`, `δ_SV` (P5, P6) `[CORREGIDO]`
- `b_VD,∞(p)` (piso de copia infinita) y `b_SV(p)` extraídos como `β₀^{1/2}` (signo desde la dirección del sesgo poblacional) en la rejilla de p.
- Regresión de `b_m(p)` sobre `p` (orden 1 + 2): pendiente líder = `δ̂_m`.
- Contraste contra las fórmulas cerradas (white-box): `δ_VD = 2 Re⟨ψ⋆|O Q⋆ L(ρ⋆)|ψ⋆⟩`, `δ_SV = Tr(OPΔP) − μ⋆ Tr(PΔP)`. Esta es la validación que convierte el aparato en "no-libre": el coeficiente sale del **generador de ruido**, no es un símbolo ajustado.
- **Colinealidad `β₀–β₁` y propagación a `δ` `[CORREGIDO]` + `[PRE-CONGELADO]`.** Extraer `b_∞(p)=√β₀` exige separación limpia de `β₀` frente a los términos `1/B` y `1/B²`; cerca de `B_den` o a `p` alto, `β₀` y `β₁` se correlacionan y el signo de `b` se vuelve frágil. Procedimiento pre-especificado (diseño, `[CORREGIDO]`):
  - calcular el **número de condición** del design matrix `[1, 1/B, 1/B²]` sobre la rejilla de `B`; como la rejilla está congelada, este número es **computable antes del hash** `[PRE-CONGELADO]` y se pre-registra un umbral. Si lo excede, la rejilla de `B` se densifica/extiende *antes* de congelar.
  - donde la colinealidad sea inevitable (alto `p`), usar **ajuste con restricción** (fijar el signo de la curvatura) o **profile-likelihood** para `β₀` con `β₁,β₂` como nuisance.
  - **propagar la incertidumbre de `β₀` (vía bootstrap conjunto) al CI de `δ̂`**, de modo que el presupuesto `τ_δ` refleje el error heredado de P1/P2, no solo el de la regresión `b(p)~p`. P5/P6 no se adjudican con `τ_δ` sin esta propagación.

### 7.4 Coeficiente de muestreo `v_m`, `s_m`
- `v̂_m = β₁ − 2 b̂_m ĉ_m` (despeje de ṽ). Contraste contra `v_VD = (σ²_N + μ² σ²_D − 2μ σ_ND)/D²` y `v_SV = σ²_acc/a`.
- `ŝ_m = κ_m v̂_m` (resource-normalized).

### 7.5 Constante de remainder `C_m` y el certificado
- Cota empírica de `C_m` desde `|β₂|` y desde el certificado teórico (Def. `quotient_constants_v4` / Efron–Stein `efron_stein_vd_v11`). Reportar **ambas**: la constante certificada (grande, conservadora) y la operativa (Efron–Stein / segundo orden directo, orden 1–10³). El paper ya distingue esto (Remark `constant_tightness_v7`); el experimento lo cuantifica. **Reiterar (coherente con §7.1): esto es una cota/consistencia, no recuperación del coeficiente del remainder.**

### 7.6 Bootstrap y design effects
- CI por **bootstrap BCa** sobre las `T` réplicas para todo coeficiente.
- **Design effect** `deff`: en Nivel 3 las réplicas comparten época de calibración ⇒ **cluster bootstrap** por época; inflar CI por `deff = Var_cluster/Var_iid`. En Nivel 1–2 las réplicas son iid (semillas independientes) ⇒ `deff = 1`, verificado.
- Propagación de incertidumbre a `R̂_{VD↔SV}` (cociente de cantidades estimadas) por bootstrap conjunto, no por delta-method ingenuo.

---

## 8. Experimentos específicos (E1–E12) y su mapeo

> Cada Ek produce las filas Pk del registro §2 y se reporta con su figura dedicada (§16).

- **E1 — Descomposición del cociente VD.** Nivel 1, n=6, p medio. Rejilla densa de B. Ajuste §7.1. **Valida** la *forma* de Thm `vd_quotient_certified_v4` y el coeficiente líder `v+2bc`; **no** el coeficiente del remainder. Salida: P1, P2. Control negativo: unmitigated (β₂≈0).
- **E2 — `c_SV=0` vs `c_VD≠0`.** Nivel 1, barrido de p. §7.2. **Valida** eq. `sv_quotient_bias_zero_v14` y `vd_c_v4`. Salida: P3, P4. *Test estructural discriminante — prioritario.*
- **E3 — `δ_VD` desde el generador.** Nivel 1, barrido de p, M grande (piso). §7.3. **Valida** Prop. `vd_delta_generator`. Salida: P5.
- **E4 — `δ_SV` de primer orden.** Nivel 1, barrido de p. §7.3. **Valida** Prop. `sv_delta_precise`. Salida: P6. *Afirmación de coeficiente solo en Nivel 1; cualquier réplica en Nivel 2 exige calibración de lectura (§4.3) y se reporta como forma, no como constante.*
- **E5 — Concentración del denominador.** Nivel 1–2, fijar p con `D_M` pequeño (M alto o p alto). Comparar comportamiento de `μ̂_VD` y validez de P1 a ambos lados de `B_den` (eq. `denom_sample_threshold_v4`). **Valida** Lem. `denom_bernstein_v4`. Salida: P7.
- **E6 — Escala log de copias.** Nivel 1–2, p fijo, M∈{2..5}, barrido de B. `M*(B)=argmin MSE`; regresión vs log B. **Valida** Thm `mstar_log_scale_v4`. Salida: P8. **Pre-requisito `[PRE-CONGELADO]`:** gap de `λ₂` verificado sobre la instancia congelada (§4.1); además verificar que `b_VD,M − b_VD,∞ ∼ q^M` y `v ∼ λ₁^{−2M}` se sostienen (hipótesis del teorema). Instancia confirmatoria con `λ₂` separado (n=8 si n=4,6 degeneran).
- **E7 — Cruce certificado.** Nivel 1–2, p fijo. Raíz empírica de `MSE_VD(R) − MSE_SV(R)`; cómputo de `η = 4C/(gR₀²)`. **Valida** Thm `certified_crossing`. Salida: P9. Reportar con la constante certificada (intervalo ancho) y con Efron–Stein (intervalo estrecho).
- **E8 — Localización de ventana 1/p vs 1/p².** Nivel 1, barrido de p, dos pares de métodos: (i) costos líder distintos ⇒ esperar `R₀∼p⁻²`; (ii) costos líder igualados ⇒ `R₀∼p⁻¹`. log R̂₀ vs log p. **Valida** Cor. `window_location_v10`. Salida: P10.
- **E9 — Tricotomía de selección.** Recorrer (p, instancia) y clasificar cada par de métodos en {tie / dominancia I / dominancia II / cruce genuino} según `g`, `Δs`. Verificar que la clasificación observada coincide con la predicha por los signos de `g·Δs`. **Valida** Thm `selection_trichotomy_v10`.
- **E10 — Ruido de implementación multiplicativo.** Inyectar contracciones `η_N, η_D` (sesgo de signo en los tests de Hadamard). Caso común `η_N=η_D`: verificar `b` invariante y `v` inflada según eq. `impl_noise_vd_variance_v11`. Caso asimétrico: verificar sesgo de primer orden adicional. **Valida** Prop. `impl_noise_shift_v11`. Salida: P11. *Es el baseline falsable que conecta con la futura sección de ruido de circuito compilado, y el marco bajo el cual el error de lectura de VD (Nivel 2) se trata como contracción multiplicativa.*
- **E11 — Brecha de Le Cam / eficiencia del transcript `[CORREGIDO]`.** En el modelo de un qubit (transcript Bernoulli, Prop. `explicit_ip_bernoulli_v5`): medir `MSE_sel` y comparar con `1/(32R(1−p)²)` (conservador) y `1/(16R(1−p)²)` (local). **Naturaleza evidencial:** dado que el bound se *deriva* sobre este mismo toy, E11 es un **chequeo de consistencia aritmética del bound y de su saturación por el transcript aceptado**, no un test empírico independiente del alcance de la teoría sobre el sistema QAOA. Se reporta como tal y **no** se lista con el peso discriminante de E2. **Valida (consistencia)** Thm `two_point_lower_bound`, Prop. `accepted_transcript_efficiency_v10`. Salida: P12.
- **E12 — Dominancia Efron–Stein en ruido físico.** Nivel 2, instancia y p realistas (no extremos). Certificar `Var(μ̂_VD^clip) ≤ [8K_N²(D+2K_D)²/D⁴]/B` y mostrar dominancia de MSE total sobre SV a `R ≥ R_ES`. **Valida** Lem. `efron_stein_vd_v11`, Prop. `sector_es_operational_certificate_v12`. Salida: P13. *Demuestra que las constantes extremas del certificado formal no son umbrales físicos.*

---

## 9. Pre-registro y protocolo de adjudicación

### 9.1 Congelar antes de ejecutar
- Instancias seleccionadas (grafos/pesos), canales de ruido, rejillas (p, B, M), T, modelos de ajuste, definiciones de κ, semillas maestras.
- **Artefactos pre-congelado obligatorios `[PRE-CONGELADO]`** que deben existir y estar hasheados junto al PAP: (i) pilot de potencia (§11); (ii) tabla de `λ₂(p)` por instancia (§4.1); (iii) número de condición del design matrix WLS sobre la rejilla de B (§7.3); (iv) estimado de cómputo (§12); (v) argumento de factibilidad de Nivel 3 (§3); (vi) lista de instancias incluidas + rechazadas con razón, y ángulos QAOA congelados (§5.5.1); (vii) tolerancias derivadas del pilot (§5.5.2); (viii) constantes `c_AD`, `c_PD` calibradas + snapshot de backend (§5.5.3).
- Hash SHA-256 del PAP + commit congelado + timestamp. Cualquier desviación posterior se reporta como análisis exploratorio, no confirmatorio.

### 9.2 Umbrales (fijar valores numéricos antes de ver datos)
**Metodología completa de derivación de cada umbral en §5.5.2.** Resumen:
- `τ` (error relativo en coeficientes de muestreo/sesgo): se fija numéricamente desde el semiancho alcanzable en el pilot (§11), más margen pre-registrado. Campo bloqueante: `tau_value` en `results/pilot/pilot_power_report.csv`.
- `τ_δ` (en δ): se congela solo si el pilot demuestra potencia ≥ 0.9 y semiancho compatible con el target de relevancia física. Campo bloqueante: `tau_delta_value`.
- Margen TOST para `c_SV=0`: `δ_c = f·|c_VD^white-box|`, con `f` fijado antes del hash y documentado en `config/grids.yaml`; usa `c_VD` exacto de Nivel 1, no el observado.
- ΔAIC para preferir el modelo con curvatura: > 2.
- Exponentes (P8, P10): la predicción debe caer en CI 95%; el semiancho máximo se fija desde el pilot como campo bloqueante `exponent_halfwidth_target`.
- Ningún umbral confirmatorio puede quedar expresado como ejemplo, rango informal o valor provisional al momento del hash.

### 9.3 Tabla de decisión por predicción
Para cada Pk: **CONFIRMA / REFUTA / INCONCLUSO** según (a) inclusión del valor predicho en el CI bootstrap **y** (b) cumplimiento del umbral relativo. Se reportan **todas**, incluidas refutaciones. Una refutación de coeficiente en Nivel 1 (white-box) sería un fallo real de la teoría, código o estimador y debe corregirse antes de continuar; una refutación solo en Nivel 2–3 indica ruptura de hipótesis (afinidad en p, correlaciones N–D, fuga de lectura no corregida), no error teórico primario.

**Plantilla congelada de adjudicación.** Antes de la corrida confirmatoria se crea `analysis/adjudication_template.csv` con las columnas:

| Predicción | Familia | Nivel | Experimento | Valor predicho | Estimador | CI | Criterio | Estado |
|---|---|---|---|---:|---:|---:|---|---|
| P1 | primaria | Nivel 1 | E1 | `v+2bc` | `β₁` | 95% BCa | dentro CI + ΔAIC>2 para VD y no para unmitigated | vacío |
| P2 | primaria | Nivel 1 | E1 | `b²` | `β₀` | 95% BCa | `b²_pred ∈ CI` | vacío |
| P3 | primaria | Nivel 1 | E2 | `c_VD` | pendiente vs `1/B` | 95% BCa | excluye 0 + error relativo ≤ `τ` | vacío |
| P4 | primaria | Nivel 1 | E2 | 0 | TOST `c_SV` | margen `δ_c` | equivalencia dentro del margen | vacío |
| P5 | primaria | Nivel 1 | E3 | `δ_VD` | pendiente `b(p)` | 95% BCa | dentro CI + error relativo ≤ `τ_δ` | vacío |
| P6 | primaria | Nivel 1 | E4 | `δ_SV` | pendiente `b(p)` | 95% BCa | dentro CI + error relativo ≤ `τ_δ` | vacío |
| P7–P13 | secundaria/descriptiva | según §8 | E5–E12 | según §2 | según §7 | 95% BCa/cluster | criterio específico de cada Pk | vacío |

El campo `Estado` solo puede tomar `CONFIRMA`, `REFUTA`, `INCONCLUSO` o `EXPLORATORIO`. No se permite crear nuevos estados después de ver datos.

### 9.4 Distinción confirmatorio vs exploratorio
Análisis no listados en §2 se marcan exploratorios — incluido el diagnóstico de estructura del remainder de §7.1 (ajuste anidado / término `1/B³`). Cualquier "tuning" de p_max, umbral de clipping o M tras ver datos invalida el estatus confirmatorio de esa celda.

### 9.5 Jerarquía de error familiar (FWER) `[CORREGIDO]`
Con 13 predicciones y subtests, adjudicar cada una independiente al 95% infla la probabilidad de al menos una confirmación/refutación espuria bajo el nulo. Se pre-registra una estructura jerárquica:

- **Familia confirmatoria primaria:** P1–P6 (objetos O1–O4, el núcleo de coeficientes/estructura). Controla FWER a `α=0.05` mediante **procedimiento de secuencia fija (gatekeeping)**: el orden de prueba es P1 → P2 → P3 → P4 → P5 → P6, y un fallo detiene la cadena (coherente con el hito de parada de §16 Fase 2). Alternativa equivalente pre-registrable: Holm–Bonferroni sobre la familia primaria.
- **Familia secundaria:** P7–P13. Se reportan **descriptivamente** con CI por predicción; **no** contribuyen a la afirmación de FWER. Una refutación aquí es informativa (típicamente ruptura de hipótesis en Nivel 2–3), no un fallo primario de la teoría.
- El TOST de `c_SV=0` (P4) es un endpoint de **equivalencia** dentro de la familia primaria; su error tipo I se controla por el propio margen TOST.


### 9.6 Protocolo formal de fallo/refutación `[CORREGIDO]`

El protocolo evita reinterpretar fallos después de ver datos.

| Fallo | Interpretación primaria | Acción obligatoria |
|---|---|---|
| P1 falla en Nivel 1 | teoría/código/estimador del cociente mal especificado | detener cadena primaria; auditar fórmula, simulador y WLS; no continuar como confirmatorio |
| P2 falla | sesgo poblacional o extracción de `β₀` inconsistente | auditar ground-truth, clipping y rango de `B` |
| P3 falla | fórmula de `c_VD` o independencia/covarianza N–D mal implementada | auditar streams, `σ_ND`, varianzas y construcción Hadamard |
| P4 falla | SV no es equivalente a cero bajo el estimador declarado | auditar postselección, clipping, definición de `μ_pop,SV`; en Niveles 2–3 revisar lectura |
| P5/P6 fallan | problema en extracción de `β₀`, generador `Δ`, diferencias finitas o colinealidad | auditar condición WLS, profile likelihood, signos del sesgo y propagación bootstrap |
| P7–P13 fallan | ruptura de hipótesis, baja potencia o límite operativo | reportar como secundario; no afecta la cadena primaria salvo que revele error de implementación |
| Nivel 3 no resuelve cruce | hardware insuficiente o deriva/calibración dominante | degradar a figura cualitativa o mover a suplemento |
| Sensibilidad de `κ`/normalización invierte el cruce | dependencia operacional real | reportar todas las normalizaciones; no elegir una post-hoc |

**Regla de parada.** En la familia primaria P1–P6, un fallo bajo la secuencia fija detiene el reclamo confirmatorio. El manuscrito puede continuar solo como análisis corregido o exploratorio, no como validación pre-registrada.

---

## 10. Sensibilidad y robustez (obligatorias)

1. **Normalización de recurso κ:** ≥ 3 definiciones (§6.2). Reportar si algún cruce cambia de lado.
2. **Umbral de clipping:** `D_M/2` vs `{D_M/3, 2D_M/3}`. La ley líder no debe cambiar (Remark ordinary-vs-clipped).
3. **Canal de ruido:** depolarizante vs amplitude+dephasing; verificar que δ_VD, δ_SV siguen al generador en cada caso.
4. **p_max:** estrechar/ampliar el intervalo; verificar estabilidad de exponentes.
5. **Copias M:** {2,3} para los cruces; confirmar que la conclusión de dominancia es robusta a M.
6. **Tamaño n:** {4,6,8}; verificar que escalas (log B, 1/p) no son artefactos de n pequeño.
7. **Instancia:** ≥ 5 por tamaño; reportar dispersión inter-instancia, no solo la media.
8. **Estimador ordinario vs clippeado:** coincidencia salvo evento exponencialmente raro una vez `B ≥ B_den`.
9. **Normalización del observable `[CORREGIDO]`:** la elección `‖O‖_∞ ≤ 1` también puede mover `R₀` (igual que κ). Repetir la localización del cruce (E7) bajo ≥ 2 normalizaciones de `O` (p. ej. `‖O‖_∞=1` vs traza-cero/normalización espectral) y reportar cualquier desplazamiento de `R₀`; tratarlo como dependencia de convención, no como resultado oculto.
10. **Mitigación de lectura (Niveles 2–3) `[CORREGIDO]`:** repetir E4/E5/E12 con y sin calibración de lectura; reportar la fracción de fuga inter-sector y su efecto sobre `μ_SV` y sobre la localización del cruce.

---

## 11. Potencia estadística y dimensionamiento `[PRE-CONGELADO]`

El pilot no es una corrida informal: es un artefacto que fija decisiones bloqueantes del PAP. Debe producir una tabla `pilot_power_report.csv` con, como mínimo:

| Output del pilot | Campo en archivo | Decisión que fija |
|---|---|---|
| Semiancho CI de `δ̂_VD` y `δ̂_SV` | `delta_halfwidth_vd`, `delta_halfwidth_sv` | `τ_δ` |
| Potencia para `c_VD ≠ 0` | `power_c_vd` | viabilidad de P3 |
| Potencia TOST para `c_SV=0` | `power_tost_c_sv` | viabilidad de P4 |
| Curtosis cerca de `B_den` | `kurtosis_near_bden` | si `T` debe subir |
| Condición WLS | `wls_condition_number` | si extender/densificar `B` |
| Semiancho de exponentes P8/P10 | `halfwidth_exp_p8`, `halfwidth_exp_p10` | si E6/E8 son confirmatorios o secundarios |
| Costo estimado | `estimated_shots`, `estimated_walltime` | si se recorta antes del hash |

Si el pilot muestra potencia insuficiente para P3–P6, se ajusta el diseño antes del hash o se degrada el endpoint correspondiente. No se permite mantener un endpoint primario si el pilot ya muestra que no puede adjudicarse con potencia suficiente.

El dimensionamiento debe **demostrarse alcanzable mediante un pilot simulado ejecutado antes del hash**, no solo argumentarse por fórmula asintótica. El pilot y su regla de decisión se pre-registran.

- **Pilot de potencia (precondición del congelado).** Sobre Nivel 1, 1–2 instancias y una rejilla de `p` gruesa, estimar empíricamente: (i) la curtosis por celda; (ii) el semiancho de CI alcanzable para `δ̂` (P5/P6) **incluyendo la propagación de `β₀`** (§7.3); (iii) la potencia del test de pendiente `c_VD≠0` y del TOST `c_SV` (P3/P4); (iv) el semiancho de CI de los exponentes (P8/P10). **Regla de decisión pre-registrada:** si el pilot muestra el diseño subpotenciado para `τ_δ=0.15` o para potencia ≥ 0.9 en los tests discriminantes, ajustar `T`, el rango de `B`, o el nº de puntos de `p` **antes** de congelar. Este ajuste es legítimo porque es pre-data-de-registro.
- **MSE:** error relativo de `MŜE` con T réplicas `≈ √(2/T)·(1+exceso de curtosis/2)^{1/2}`. Para 5% relativo con colas moderadas ⇒ `T ≳ 1500–2000` (cifra a confirmar por el pilot). Subir T donde el cociente tenga colas pesadas (cerca/por debajo de B_den).
- **Pendiente `c_m` (P3/P4):** calcular el `B`-rango mínimo y `T` para que el CI de la pendiente excluya 0 (VD) y caiga dentro de `δ_c` (SV) con potencia ≥ 0.9. Pre-registrar el resultado del pilot.
- **Exponentes (P8, P10):** nº de puntos de p / B y rango (≥1.5 décadas) para CI de exponente con semiancho < 0.15, confirmado por el pilot.

---

## 12. Presupuesto de cómputo y factibilidad (estilo Phase C)

El presupuesto se trata como un artefacto pre-congelado, no como una estimación verbal. Antes del hash debe existir `results/frozen/compute_budget_table.csv` con números cerrados para cada nivel y cada bloque experimental.

**Plantilla mínima del presupuesto.**

| Nivel | Experimentos | Instancias | `n` | #p | #B | #M | Métodos | `T` | Streams | Shots efectivos | RAM pico | Wall-time estimado | Decisión |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Nivel 1 core | E1–E4 | — | — | — | — | — | — | — | — | — | — | — | confirmatorio |
| Nivel 1 estructural | E5–E8 | — | — | — | — | — | — | — | — | — | — | — | secundario |
| Nivel 2 | E5/E7/E8/E12 | — | — | — | — | — | — | — | — | — | — | — | robustez |
| Nivel 3 | E5/E7 | — | — | — | — | — | — | — | — | — | — | cola real | cualitativo |

Los guiones se reemplazan por números antes del hash. La columna `Decisión` solo puede ser `confirmatorio`, `secundario`, `robustez`, `cualitativo` u `omitido`. Si el costo de un bloque excede el presupuesto disponible, se degrada antes del hash; no se reduce después de ver datos.

Estructurar como barrido en rejilla con checkpointing por celda.

- **Estimado pre-congelado `[PRE-CONGELADO]`.** Antes del hash se reporta el orden de magnitud de shots y wall-time por nivel, computado sobre el conteo real de celdas = instancia(5) × n(3) × p(12) × B(10) × M × método(3) × T(2000) **más** el sobrecoste de bootstrap. No basta con "trivial"; el costo dominante es el muestreo shot-level, no la construcción de `ρ_p`.
- **Nivel 1 (density-matrix, n≤8):** density-matrix de 8 qubits = 2¹⁶ amplitudes complejas → la construcción de `ρ_p` es barata (una vez por (instancia,p)); el costo real es el muestreo shot-level × T × B. Pre-computar `ρ_p` y muestrear de las distribuciones de salida (no resimular el circuito por shot). `total_shots ≈ Σ_celdas T·B·(streams)`.
- **Paralelización:** celdas embarazosamente paralelas (instancia × p × B × M × método). Chunking + checkpoint por chunk + reanudación idempotente.
- **Nivel 2 (Aer noise model):** más caro por shot; reducir T y B_max; priorizar E5, E7, E8, E12/P13.
- **Nivel 3 (hardware) `[EJECUCIÓN]`:** el presupuesto de shots por época y el spec del device dependen de la cola real y se cierran en ejecución; el *argumento* de factibilidad (alcanzabilidad de `B_max`, resolubilidad del cruce) sí es pre-congelado (§3). Mitigar deriva con intercalado de métodos dentro de la misma época de calibración.
- **La corrida completa es `[EJECUCIÓN]`;** el estimado de feasibility es `[PRE-CONGELADO]`.

---

## 13. Reproducibilidad y artefacto (estándar ≥ 8/10)

- Repo con separación estricta: `ground_truth/` (Nivel 1, cálculos cerrados) vs `estimation/` (pipeline de muestreo y ajustes) vs `analysis/` (adjudicación, figuras). El pipeline de estimación **no** debe poder leer el ground-truth salvo en el paso final de contraste.
- Semillas maestras versionadas; cada celda con semilla derivada determinista.
- Lockfile de entorno (Qiskit/Aer versión pinned), contenedor.
- Hash del PAP en el repo; tabla de adjudicación generada automáticamente.
- **Estructura scriptable obligatoria `[CORREGIDO]`:**
  - `pap/hash_pap.py` genera `freeze_manifest.json`.
  - `ground_truth/compute_frozen_model_specs.py` genera `frozen_instances.csv` y `frozen_qaoa_angles.csv`.
  - `ground_truth/compute_lambda2_gaps.py` genera `lambda2_gap_table.csv`.
  - `ground_truth/compute_wls_condition.py` genera `wls_condition_report.csv`.
  - `pilot/run_power_pilot.py` genera `pilot_power_report.csv`.
  - `readout/sector_leakage_diagnostics.py` genera fuga inter-sector pre/post mitigación.
  - `analysis/adjudication_table.py` llena la tabla P1–P13 sin intervención manual.
  - `analysis/make_figures.py` reproduce todas las figuras desde datos crudos.
- **Artefactos pre-congelado versionados junto al PAP (§9.1):** pilot de potencia, tabla de `λ₂(p)`, número de condición WLS, estimado de cómputo, argumento de factibilidad de Nivel 3, lista de instancias incluidas/rechazadas + ángulos QAOA, tolerancias derivadas, constantes de canal + snapshot de backend.
- Datos crudos (`{μ̂_t}` por celda) + scripts de figura → Zenodo con DOI.

---

## 14. Registro de riesgos y contingencias

| Riesgo | Síntoma | Contingencia |
|--------|---------|--------------|
| Afinidad en p se rompe en Nivel 2 | δ̂ no sigue al generador fuera de Nivel 1 | Reportar como límite de validez; restringir reclamos de coeficiente a Nivel 1 |
| Correlación N–D en circuito compilado | `σ_ND ≠ 0`, `v_VD` no encaja con fórmula independiente | Medir `σ_ND` y usar `v_VD` general (eq. `vd_v_v4`), no la de streams independientes |
| Cruce sensible a κ | R̂* cambia de lado entre normalizaciones | Reportar todas; enmarcar como dependencia de normalización, no como resultado nulo oculto |
| Colas pesadas bajo B_den | MŜE inestable, curtosis alta | Subir T; usar estimador clippeado; mostrar el cambio de régimen como **confirmación** de P7 |
| Sobre-ingeniería percibida | Referee cuestiona el peso del certificado | Liderar con ley operativa + Efron–Stein en cuerpo; constantes pesadas a apéndice |
| n pequeño no resuelve λ₂ | Escala log de copias ruidosa | Elegir canal con λ₂ separado; usar n=8 para E6; **gap de λ₂ pre-computado (§4.1)** |
| Error de lectura contamina postselección SV `[CORREGIDO]` | `μ_SV` sesgado en Nivel 2–3; fuga inter-sector; `δ_SV` aparente espurio | Calibración/mitigación de lectura antes de postseleccionar (§4.3); restringir reclamos de coeficiente de SV a Nivel 1; reportar fracción de fuga |
| `β₀–β₁` colineales | `δ̂` con CI inflado o signo inestable | Número de condición pre-computado (§7.3); ajuste con restricción / profile-likelihood; propagar `β₀` al CI de `δ̂` |
| Diseño subpotenciado para `τ_δ` | Pilot muestra potencia < 0.9 | Ajustar T/rejilla **antes** del hash (§11); no congelar el umbral hasta que el pilot lo respalde |
| `β₂` mal interpretado como `C` | Reclamo de "validación del remainder" | P1 valida forma + `β₁`, no el coeficiente del remainder (§7.1); `|β₂|≲C` solo como condición necesaria |

---

## 15. Reporte: figuras ancladas a predicciones

Cada figura corresponde a una predicción del §2 y lleva el ancla de ecuación en el caption:

1. **Fig E1:** MŜE_VD vs 1/B con ajuste b²+ṽ/B+β₂/B²; residuos del modelo lineal puro (muestra que la curvatura es necesaria). Caption explícito: valida *forma* + coeficiente líder, no el coeficiente del remainder. ↔ Thm `vd_quotient_certified_v4`.
2. **Fig E2:** `(Ê[μ̂]−μ_pop)` vs 1/B para VD y SV en un solo panel; pendiente SV ≈ 0. ↔ `c_SV=0` vs `c_VD`.
3. **Fig E3–E4:** `b_VD,∞(p)` y `b_SV(p)` vs p con la recta del generador superpuesta; bandas de CI que incluyen la propagación de `β₀`. ↔ δ_VD, δ_SV.
4. **Fig E5:** validez de la ley a ambos lados de B_den. ↔ Bernstein del denominador.
5. **Fig E6:** M*(B) vs log B con pendiente predicha 1/(2|log λ₂|); anotar el gap de `λ₂` verificado. ↔ escala log de copias.
6. **Fig E7:** MSE_VD(R) y MSE_SV(R); cruce empírico y banda certificada [R₀(1−η), R₀(1+η)] (dos bandas: certificada vs Efron–Stein). ↔ cruce certificado.
7. **Fig E8:** log R̂₀ vs log p para los dos regímenes (−2 y −1). ↔ localización de ventana.
8. **Fig E11:** cociente MSE_sel / cota Le Cam vs p con líneas en 64 y 32; caption la marca como chequeo de consistencia del bound. ↔ Le Cam / eficiencia.
9. **Fig E12:** dominancia MSE total VD vs SV en instancia física a R_ES; con y sin mitigación de lectura. ↔ Efron–Stein operacional.
10. **Tabla de adjudicación:** las 13 predicciones con CONFIRMA/REFUTA/INCONCLUSO, CI y valor predicho, con la familia (primaria/secundaria) indicada.


### 15.1 Separación paper body vs suplemento `[CORREGIDO]`

El PAP completo puede ser amplio; el paper no debe presentar todo con el mismo peso. La narrativa principal se congela así:

| Ubicación | Contenido | Función retórica |
|---|---|---|
| Cuerpo principal | P1–P6 vía E1–E4 | demostrar que los coeficientes y la estructura del aparato son reales |
| Cuerpo principal o apéndice corto | E5 denominador y E7 cruce certificado | conectar la teoría con régimen operacional |
| Apéndice técnico | E8 ventana `1/p` vs `1/p²` | predicción estructural adicional |
| Suplemento | E6, E9, E10, E11, E12 | robustez, extensiones y chequeos secundarios |
| Repositorio | PAP completo, pilots, hashes, scripts, tablas completas | reproducibilidad/auditoría |
| Hardware | figura cualitativa o sanity check | factibilidad, no validación de constantes |

**Regla narrativa.** El manuscrito no debe vender "VD gana a SV". Debe vender: (i) la ley MSE del cociente aparece con el coeficiente líder correcto; (ii) `c_VD≠0` mientras `c_SV=0`; (iii) los sesgos de primer orden salen del generador; (iv) el denominador explica el régimen peligroso; (v) el cruce se localiza donde la teoría lo certifica.

---

## 16. Fases de ejecución

1. **Fase 0 — Congelado del PAP.** Selección de instancias, canales, rejillas, umbrales; hash + timestamp. Incluye los artefactos pre-congelado `[PRE-CONGELADO]`: **(a)** pilot de potencia (§11) y ajuste de T/rejilla si procede; **(b)** tabla de `λ₂(p)` por instancia (§4.1) y elección de la instancia confirmatoria de E6; **(c)** número de condición del design matrix WLS sobre la rejilla de B (§7.3); **(d)** estimado de cómputo (§12); **(e)** argumento de factibilidad de Nivel 3 (§3); **(f)** generación del ensemble, aplicación de I1–I4, congelado de las listas incluida/rechazada y de los ángulos QAOA (§5.5.1); **(g)** derivación de tolerancias desde el pilot (§5.5.2); **(h)** calibración de `c_AD`, `c_PD` contra el snapshot de backend (§5.5.3). Sin datos de registro.
2. **Fase 1 — Ground-truth white-box.** Cálculo cerrado de todos los coeficientes (Nivel 1) para cada (instancia, p, M). Verificación de consistencia interna (Tr=1, espectro ordenado, identidades δ).
3. **Fase 2 — Estimación Nivel 1.** E1–E4 ejecutan la familia primaria P1–P6; E5–E8 se ejecutan como familia estructural secundaria. La adjudicación sigue §9.5 (secuencia fija sobre P1–P6). *Hito: si un endpoint primario se refuta aquí, se detiene la cadena y se corrige el manuscrito antes de seguir.*
4. **Fase 3 — Robustez Nivel 2.** E5, E6, E7, E8, E12 sobre noise model calibrado (con calibración de lectura, §4.3); sensibilidad §10.
5. **Fase 4 — Factibilidad Nivel 3 `[EJECUCIÓN]`.** Hardware acotado (E7, E5 cualitativos), según el argumento de factibilidad pre-congelado. Si no se sostuvo, degradado a una figura cualitativa única.
6. **Fase 5 — Síntesis.** Tabla de adjudicación, figuras, sección experimental redactada con anclas; depósito Zenodo.

---

## 17. Cómo esto resuelve las tres objeciones de QIP

- **"El aparato es sobre-ingeniería desconectada":** E1–E4 miden directamente `b, c, v, δ` y los contrastan con las fórmulas cerradas; el certificado no queda decorativo, se usa para emitir y verificar los cruces (E7) y para la regla de validez η<1/2. **Calibración honesta (`[CORREGIDO]`):** E1 valida la *forma* de la ley del cociente y el coeficiente líder `v+2bc`, no el coeficiente del remainder; este se reporta solo como cota/consistencia (§7.1, §7.5). El incremento medible verdaderamente discriminante es la asimetría `c_VD≠0` vs `c_SV=0` (E2) y la banda certificada del cruce (E7).
- **"Novedad frente a Huggins/Koczor/Cai/Vikstal":** el incremento medible es la **ley de MSE del cociente con concentración del denominador** (forma de E1 + E5) y la **regla de cruce certificada** (E7) — ningún trabajo previo mide `c_VD≠0` vs `c_SV=0` ni la banda certificada del cruce. Declararlo explícito en intro y en E2.
- **"¿Es justa la comparación?":** la normalización de recurso `R = κB` se pre-registra y se somete a sensibilidad (§6.2, §10) con reporte de cualquier inversión de cruce, incluyendo la dependencia de la normalización de `O` (§10.9).

> **Nota sobre E11 (`[CORREGIDO]`):** la brecha de Le Cam se valida como chequeo de consistencia aritmética del bound sobre el toy donde se deriva, no como test empírico independiente del alcance de la teoría. Su peso evidencial es menor que el de E2/E7 y se reporta en ese registro.

---

### Nota de alcance

Este plan está deliberadamente diseñado para que **lo que decide la aceptación sea la fidelidad experimento↔teoría**, no la potencia de la mitigación. Los puntos extremos del paper (constantes 10⁷–10⁸, ratios ℓ/u=10⁶) **no** se reproducen experimentalmente: se sustituyen por el certificado Efron–Stein / segundo-orden directo a parámetros físicos (E12), exactamente como el manuscrito anticipa en sus remarks de tightness. Mantener esa honestidad explícita en el texto es parte del diseño, no una concesión.
