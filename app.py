# file: app.py
"""
API rápida para consultar el próximo tren entre estaciones.
Mejoras:
- Normalización (quita tildes, puntuación y espacios extra)
- Búsqueda por palabras / coincidencia parcial y ranking
- Comparación fiable de horas usando minutos
- Hora actual en Europe/Madrid
"""
from fastapi import FastAPI, HTTPException
import json
import unicodedata
import re
from datetime import datetime
from zoneinfo import ZoneInfo
import logging
from typing import List, Optional, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("train_api")

app = FastAPI()

# --- Cargar datos ---
with open("tren_lunes_viernes_ida.json", encoding="utf-8") as f:
    DATA = json.load(f)


# --- Utilidades de texto (normalización) ---
def normalize_text(s: Optional[str]) -> str:
    """Lowercase, remove accents, keep alphanum and spaces, collapse spaces."""
    if not s:
        return ""
    s = s.strip().lower()
    # Normalize unicode and remove diacritics
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    # Replace non-alphanumeric with space (keep numbers too)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def tokenize(s: str) -> List[str]:
    return s.split() if s else []


# --- Matching / scoring ---
def match_score(query_norm: str, station_norm: str) -> int:
    """
    Return a score (higher = better) for how well query matches station.
    Heurística:
      100 = exact match
       90 = station startswith query
       80 = query is substring
       70+ = all query tokens found in station tokens (more tokens -> higher)
       0  = no match
    """
    if not query_norm or not station_norm:
        return 0
    if query_norm == station_norm:
        return 100
    if station_norm.startswith(query_norm):
        return 90
    if query_norm in station_norm:
        return 80

    q_tokens = tokenize(query_norm)
    s_tokens = tokenize(station_norm)
    if not q_tokens:
        return 0

    # check if every token in query appears somewhere in station (substring allowed)
    matched_tokens = 0
    for qt in q_tokens:
        for st in s_tokens:
            if qt in st:
                matched_tokens += 1
                break

    if matched_tokens == len(q_tokens):
        # base 70 + bonus per token matched to prefer more specific matches
        return 70 + min(20, 5 * len(q_tokens))
    return 0


def buscar_estacion(nombre: str, estaciones: List[str]) -> Optional[str]:
    """
    Busca la mejor coincidencia para `nombre` dentro de la lista `estaciones`.
    Devuelve la estación original tal cual aparece en datos, o None.
    """
    q_norm = normalize_text(nombre)
    best_score = 0
    best_station = None
    for est in estaciones:
        est_norm = normalize_text(est)
        score = match_score(q_norm, est_norm)
        if score > best_score:
            best_score = score
            best_station = est
    logger.debug("buscar_estacion | query=%s best=%s score=%s", nombre, best_station, best_score)
    return best_station if best_score > 0 else None


# --- Time utilities ---
def time_to_minutes(t: str) -> Optional[int]:
    """
    Convierte una hora en string (HH:MM, H:MM, HH:MM:SS, etc.) a minutos desde 00:00.
    Devuelve None si no se puede parsear.
    """
    if not t:
        return None
    t = str(t).strip()
    # common formats: "06:30", "6:30", "06:30:00"
    m = re.match(r"^(\d{1,2}):(\d{2})", t)
    if not m:
        return None
    try:
        h = int(m.group(1))
        mm = int(m.group(2))
        return h * 60 + mm
    except ValueError:
        return None


def hora_actual_madrid_minutes() -> Tuple[str, int]:
    """Devuelve (hora_str, minutos_desde_medianoche) para Europe/Madrid."""
    tz = ZoneInfo("Europe/Madrid")
    now = datetime.now(tz)
    hora_str = now.strftime("%H:%M")
    minutos = now.hour * 60 + now.minute
    return hora_str, minutos


# --- Endpoints ---
@app.get("/")
def home():
    return {"status": "ok", "message": "Train API online"}


@app.get("/get_available_timeslots")
def get_available_timeslots(origen: str = None, destino: str = None):
    if not origen or not destino:
        raise HTTPException(status_code=400, detail="Parámetros 'origen' y 'destino' son obligatorios")

    # Preparar hora actual en Madrid
    hora_actual_str, hora_actual_min = hora_actual_madrid_minutes()

    candidatos = []
    # iterar viajes y buscar coincidencias
    for viaje in DATA.get("Viajes", []):
        ruta = viaje.get("Ruta", [])
        estaciones_originales = [r.get("Estacion", "") for r in ruta]

        est_origen = buscar_estacion(origen, estaciones_originales)
        est_destino = buscar_estacion(destino, estaciones_originales)

        if not est_origen or not est_destino:
            continue

        try:
            idx_origen = estaciones_originales.index(est_origen)
            idx_destino = estaciones_originales.index(est_destino)
        except ValueError:
            # seguridad: si index falla, saltar
            continue

        if idx_origen < idx_destino:
            hora_salida_str = ruta[idx_origen].get("Hora", "")
            hora_salida_min = time_to_minutes(hora_salida_str)
            if hora_salida_min is None:
                continue  # no podemos comparar horas inválidas
            if hora_salida_min >= hora_actual_min:
                candidatos.append({
                    "parada": viaje.get("Parada"),
                    "salida": hora_salida_str,
                    "salida_minutos": hora_salida_min,
                    "origen": est_origen,
                    "destino": est_destino
                })

    if not candidatos:
        raise HTTPException(status_code=404, detail=f"No se encontró viaje válido después de {hora_actual_str}")

    # ordenar por minutos y devolver el primero
    candidatos.sort(key=lambda x: x["salida_minutos"])
    proximo = candidatos[0]
    # calcular minutos restantes
    minutos_restantes = proximo["salida_minutos"] - hora_actual_min
    proximo_response = {
        "parada": proximo["parada"],
        "salida": proximo["salida"],
        "origen": proximo["origen"],
        "destino": proximo["destino"],
        "hora_actual": hora_actual_str,
        "minutos_restantes": minutos_restantes
    }
    logger.info("Request origen=%s destino=%s -> next=%s", origen, destino, proximo_response)
    return {"proximo_viaje": proximo_response}


# --- Optional helper: list all stations available (útil para debug) ---
@app.get("/list_stations")
def list_stations():
    """Devuelve una lista única y ordenada de estaciones encontradas en el JSON."""
    s = set()
    for viaje in DATA.get("Viajes", []):
        for r in viaje.get("Ruta", []):
            est = r.get("Estacion")
            if est:
                s.add(est)
    return {"stations": sorted(s)}
