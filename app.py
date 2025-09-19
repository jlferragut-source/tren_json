from fastapi import FastAPI, HTTPException
import json
import os

app = FastAPI()

# Cargar el JSON desde el mismo directorio
with open("tren_lunes_viernes_ida.json", encoding="utf-8") as f:
    DATA = json.load(f)

@app.get("/")
def home():
    return {"status": "ok", "message": "Train API online"}

@app.post("/get_available_timeslots")
def get_available_timeslots(origen: str, destino: str):
    """
    Devuelve la hora de salida desde 'origen' hacia 'destino'
    si existe un viaje que pase por ambas estaciones en orden.
    """
    for viaje in DATA["Viajes"]:
        ruta = viaje["Ruta"]
        estaciones = [r["Estacion"] for r in ruta]
        if origen in estaciones and destino in estaciones:
            idx_origen = estaciones.index(origen)
            idx_destino = estaciones.index(destino)
            if idx_origen < idx_destino:
                return {
                    "parada": viaje["Parada"],
                    "salida": ruta[idx_origen]["Hora"],
                    "origen": origen,
                    "destino": destino
                }
    raise HTTPException(status_code=404, detail="No se encontró viaje válido")
