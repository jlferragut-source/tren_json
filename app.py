from fastapi import FastAPI, HTTPException
import json

app = FastAPI()

# Cargar JSON de horarios
with open("tren_lunes_viernes_ida.json", encoding="utf-8") as f:
    DATA = json.load(f)


def buscar_estacion(nombre: str, estaciones: list[str]) -> str | None:
    """
    Busca si alguna palabra clave dada por el usuario
    está contenida dentro del nombre de estación.
    """
    nombre = nombre.strip().lower()
    for est in estaciones:
        if nombre in est.strip().lower():
            return est  # devolver la estación original
    return None


@app.get("/")
def home():
    return {"status": "ok", "message": "Train API online"}


@app.get("/get_available_timeslots")
def get_available_timeslots(origen: str = None, destino: str = None):
    if not origen or not destino:
        raise HTTPException(status_code=400, detail="Parámetros 'origen' y 'destino' son obligatorios")

    resultados = []

    for viaje in DATA["Viajes"]:
        ruta = viaje["Ruta"]
        estaciones_originales = [r["Estacion"] for r in ruta]

        est_origen = buscar_estacion(origen, estaciones_originales)
        est_destino = buscar_estacion(destino, estaciones_originales)

        if est_origen and est_destino:
            idx_origen = estaciones_originales.index(est_origen)
            idx_destino = estaciones_originales.index(est_destino)

            if idx_origen < idx_destino:
                resultados.append({
                    "parada": viaje["Parada"],
                    "salida": ruta[idx_origen]["Hora"],
                    "origen": est_origen,
                    "destino": est_destino
                })

    if not resultados:
        raise HTTPException(status_code=404, detail="No se encontró viaje válido")

    return {"viajes": resultados}
