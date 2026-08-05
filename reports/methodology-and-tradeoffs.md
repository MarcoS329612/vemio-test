# Metodología, supuestos y trade-offs

Supuestos, metodología por reto y trade-offs. Cada número sale de un script en `scripts/` y se
reimprime en un reporte de etapa; se reproduce con `uv sync && uv run scripts/run_all.py`.
**El razonamiento completo — cómo funciona cada método y por qué se eligió — está en
[`technical-walkthrough.md`](technical-walkthrough.md).**

**Procedencia.** La base de este repositorio se importó de una solución previa e independiente
al mismo caso de VEMIO (acreditada en el commit inicial). El descuento de equilibrio, la banda
de precio, el uplift a nivel combo (H-007), el EDA de contexto comercial y el reparto por
bodega se portaron desde una **segunda** solución al mismo dataset, de autoría distinta — la
declaración completa está en la entrada del 2026-08-04 de
[`docs/WORKLOG.md`](../docs/WORKLOG.md). Cada número portado se volvió a derivar sobre los
datos limpios de este repositorio antes de reportarse, y dos se corrigieron en vez de
adoptarse tal cual (el arreglo de precio de DR-0007 y la reestimación de H-007 controlada por
concurrencia).

---

## Supuestos, comunes a los tres retos

**La columna de costo está invertida (F-003).** `product_cost / bruto` es *exactamente*
constante dentro de cada SKU — desviación estándar 0.0 a nueve decimales — entre 1.22 y 1.30,
así que leída al pie de la letra el cliente pierde 22–30% del ingreso bruto en cada
transacción. El archivo trae `costo = precio × (1 + margen)` cuando un markup implica
`costo = precio ÷ (1 + margen)`: el mismo factor, al revés. Eso también recupera
`product_margin`, que el archivo omite (F-001) y el Reto B necesita. **Supuesto**:
`margen = product_cost/bruto − 1`, `costo unitario = precio de lista ÷ (1 + margen)`, aislado
en `src/analysis/economics.py` para que una sola edición lo revierta. Las tasas recuperadas
son markup **sobre costo**, como documenta el diccionario; todo *resultado* en dinero se
expresa **sobre ingreso**, `(precio − costo)/precio` — las mismas tasas, como 18.0%–23.1%.
Toda cifra en dinero hereda esto; **ninguna cifra de volumen.**

**`discount` es una fracción y solo cuadra a nivel combo (F-004).** En las 128,977 filas
promocionadas con diferencia entre bruto y neto, leerlo como monto en dinero cuadra con
**cero** filas y como fracción cuadra con 48% — nunca exacto, tal como anticipa la nota del
diccionario de que "se calcula a nivel de combo". Por eso el precio efectivo siempre es
`sell_in_amount ÷ sell_in_quantity`; aplicar `discount` sobre `bruto` sería incorrecto en más
de la mitad de esas filas, justo en la variable sobre la que descansa el Reto B.

**La limpieza marca, nunca borra.** Seis columnas booleanas cargan los motivos y cada etapa
elige su propio filtro: 99.86% de las filas sirven para demanda, 96.9% para precio. Las filas
con monto cero conservan sus unidades — el producto regalado es demanda real — pero salen del
panel de precios.

## Reto A — proyección de demanda

Unidades semanales, horizonte de 12 semanas, tres SKUs que cubren los modos de falla: **1857**
(grande, casi sin promoción), **1283** (oscilación estacional de 26 veces) y **1665**
(promocionado en ~95% de las semanas). Validación sobre cinco orígenes rodantes separados tres
semanas, con ventana expansiva; ninguna variable es calculable desde el periodo sobre el que
se evalúa. Métrica: **WAPE**. El MAPE divide entre el real de cada semana y por construcción
premia quedarse corto, el incentivo equivocado cuando faltar cuesta tanto como sobrar.

De siete modelos, **nada le ganó a los baselines ingenuos en dos de tres SKUs**: un promedio
móvil de 4 semanas gana en 1857 (WAPE 0.257) y en 1665 (0.291). Solo 1283 justificó un
candidato: deriva amortiguada con 0.272 contra 0.322 del mejor baseline. Ese es el hallazgo,
no la ausencia de uno.

**Trade-offs.** No se modeló estacionalidad anual: un periodo de 52 semanas necesita dos
ciclos y este histórico tiene ~1.4. La presión promocional no entra como covariable, porque el
plan promocional futuro no está en los datos; la proyección supone *un patrón promocional
parecido al del pasado reciente*. Son proyecciones puntuales, sin intervalos.

## Reto B — elasticidad de precio

El SKU se eligió con un criterio fijado **antes** de estimar — el soporte de precio observado
más amplio, que acota el dominio válido del simulador; 1665 ganó en rango y volumen. Demanda
log-log con tendencia lineal y términos de Fourier anuales, para que el coeficiente de precio
no absorba "marzo es un mes fuerte", con errores Newey-West (HAC) por autocorrelación:
elasticidad **−4.73**, IC 95% **[−5.71, −3.76]**, R² 0.76 sobre 72 semanas.

El simulador está acotado a la banda p5–p95 (**45.32–61.45**) y no al rango crudo
(42.87–64.20), cuyas colas son artefactos contables de combos y no precios que alguien haya
fijado; `predict_units` lanza error en vez de extrapolar. El equilibrio está en **46.41**, y
10% del histórico se vendió por debajo. Con una demanda así de elástica el ingreso no tiene
óptimo interior, de modo que promediarlo en un objetivo "balanceado" solo votaría por el
precio más barato de la malla (**DR-0007**); la recomendación es el precio que maximiza
margen, **58.71**.

## Reto C — uplift promocional

Dos capas, reportadas lado a lado (**DR-0005**). Los *episodios* — rachas contiguas de semanas
en las que más de la mitad de las unidades de un SKU se venden bajo combo — miden la presión
promocional total y son inmunes por construcción al traslape entre combos; se detectaron doce,
nueve con baseline utilizable. La *regresión a nivel combo* mete simultáneamente todos los
combos activos sobre el SKU junto con una tendencia, y devuelve la contribución de cada
mecánica neta de las demás.

Cada episodio carga dos contrafactuales apoyados en supuestos distintos — un baseline de las
seis semanas *tranquilas* previas y un ajuste de diferencias en diferencias — más una
calificación de evidencia sobre limpieza del baseline, controles y observabilidad de la
ventana posterior. Se restan seis semanas posteriores de adelanto de compra. El margen
incremental cuenta solo las unidades creadas, mientras que el descuento se paga sobre cada
unidad vendida: esa asimetría explica que varios episodios con uplift real hayan destruido
margen.

## Reparto por bodega

La proyección nacional se reparte por la participación histórica de cada bodega: auditable, no
opaca. Las participaciones se ajustan estrictamente antes del origen de la proyección, y corre
una prueba de bodega muerta por (SKU, bodega) que excluye a bodega n. 11 (F-013). La
reconciliación cuadra contra el total del SKU; cada línea por bodega suma su propio error de
estimación de participación.

## Limitaciones honestas

- **Los baselines ganaron en dos de tres SKUs** (arriba).
- **Esto es sell-in, no sell-out.** Una elasticidad cercana a −5 absorbe tanto la carga
  anticipada del distribuidor como la respuesta de la demanda: dice cuánto carga el
  distribuidor, no cuántas unidades llegan al comprador.
- **Las tendencias paralelas no se pueden probar.** No existe grupo de control a nivel cliente
  — a todos se les ofreció la promoción — así que los controles son otros SKUs de tres
  categorías.
- **La significancia de H-007 es frágil.** El estimador puntual es estable entre estimadores
  de covarianza; el p-value se mueve de 0.012 a 0.087 según cuál se elija
  (`reports/05_uplift.md` §4.7).
- **La convención de costo es una inferencia**, no un hecho confirmado (F-003, pregunta
  abierta Q5).
- **No se mide la canibalización**, y la profundidad del descuento es la realizada, no la
  ofrecida.

## Qué haría distinto con más tiempo o más datos

1. **Preguntarle a VEMIO las cinco preguntas abiertas primero** ([ROADMAP](../docs/ROADMAP.md)).
   La Q5 — la dirección del costo — mueve todas las cifras de margen de aquí.
2. **Conseguir sell-out, no solo sell-in**: separa la respuesta del consumidor de la carga
   anticipada.
3. **Intervalos de predicción y un nivel de servicio**, para convertir la proyección en
   cantidad de reorden.
4. **Una proyección que conozca el plan promocional**: legítima en producción, fuga de
   información en un backtest.
5. **Canibalización entre SKUs y un modelo de *demanda* a nivel bodega** (F-012).
6. **Un histórico más largo.** Diecisiete meses observan cada ciclo anual apenas una vez.

El uso de IA y las correcciones hechas a lo que produjo están documentados en
[`docs/AI_USAGE_LOG.md`](../docs/AI_USAGE_LOG.md).
