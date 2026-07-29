# Criterios de limpieza — ejemplo de formato para un proyecto nuevo

Este skill no trae un glosario propio a propósito — cada proyecto (una serie de entrevistas de
un mismo tema, un mismo cliente, una misma región) tiene sus propios nombres, organizaciones y
términos recurrentes. Este archivo es una plantilla de cómo documentarlos, no contenido a usar
tal cual. Copiarlo a `references/criterios-limpieza-<proyecto>.md` dentro del proyecto que use
este skill y llenarlo a medida que se calibra con las primeras grabaciones.

## Diferencias de este proyecto frente al flujo general del skill

Ejemplos de cosas que varían por proyecto y vale la pena anotar apenas se detecten:

- ¿El audio es de un solo micrófono con varios hablantes cerca (favorece reconstruir por
  palabra, ver SKILL.md Paso 1) o llamadas con buena separación de canal?
- ¿Hay un keyterm cargado en Deepgram que esté sesgando el reconocimiento de otra palabra
  parecida? (pasó en un proyecto: un keyterm de nombre propio sesgó una palabra común de uso
  local hacia una variante del keyterm — verificar antes de aceptar una palabra rara que
  contenga la raíz de un keyterm cargado).
- ¿Se tokenizan nombres de personas, o se dejan en claro porque el documento es insumo interno
  y se necesitan para otro análisis? ¿Qué datos SÍ se dejan en claro siempre (nombre de la
  organización/institución, topónimos) aunque el audio los distorsione?

## Glosario confirmado

Términos que ya se verificaron (por repetición interna consistente, o porque quien encargó el
trabajo los confirmó) y por lo tanto **no** van marcados `[dudoso]` ni como pendiente:

- **Término real** — cómo lo distorsiona el ASR (variantes vistas). Contexto de por qué se
  confirmó.

## Garbles típicos vistos

| En el audio (ASR) | Limpio | Nota |
|---|---|---|
| ejemplo garble | término real | por qué se decidió así (repetición, contexto, confirmación externa) |

## Pendientes típicos de este proyecto

Patrones que se repiten entre grabaciones y vale la pena tener presentes de antemano (ej.
nombres de lugares mencionados de forma fonética y no verificable, cargos/roles con
terminología específica del cliente, etc.).
