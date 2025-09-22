from fastapi import FastAPI, HTTPException
import json
from datetime import datetime
import zoneinfo

app = FastAPI()

# Cargar JSON de horarios
with open("tren_lunes_viernes_ida.json", encoding="utf-8") as f:
    DATA = json.load(f)


def hora_actual_madrid() -> str:
    """
    Devuelve la hora actual en Madrid (Europe/Madrid) en formato HH:MM
    """
    tz = zoneinfo.ZoneInfo("Europe/Madrid")
    return datetime.now(tz).strftime("%H:%M")


def buscar_estacion(nombre: str, estaciones: list[str]) -> str | None:
    """
    Busca coincidencia parcial de palabra clave en nombre de estación.
    """
    nombre = nombre.strip().lower()
    for est in estaciones:
        if nombre in est.strip().lower():
            return est
    return None


@app.get("/")
def home():
    return {"status": "ok", "message": "Train API online"}


@app.get("/get_available_timeslots")
def get_available_timeslots(origen: str = None, destino: str = None):
    if not origen or not destino:
        raise HTTPException(status_code=400, detail="Parámetros 'origen' y 'destino' son obligatorios")

    resultados = []
    hora_actual = hora_actual_madrid()

    for viaje in DATA["Viajes"]:
        ruta = viaje["Ruta"]
        estaciones_originales = [r["Estacion"] for r in ruta]

        est_origen = buscar_estacion(origen, estaciones_originales)
        est_destino = buscar_estacion(destino, estaciones_originales)

        if est_origen and est_destino:
            idx_origen = estaciones_originales.index(est_origen)
            idx_destino = estaciones_originales.index(est_destino)

            if idx_origen < idx_destino:
                hora_salida = ruta[idx_origen]["Hora"]
                # Solo incluir viajes que no han salido todavía
                if hora_salida >= hora_actual:
                    resultados.append({
                        "parada": viaje["Parada"],
                        "salida": hora_salida,
                        "origen": est_origen,
                        "destino": est_destino,
                        "hora_actual": hora_actual
                    })

    if not resultados:
        raise HTTPException(status_code=404, detail=f"No se encontró viaje válido después de {hora_actual}")

    return {"viajes": resultados}
