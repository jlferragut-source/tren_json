from fastapi import FastAPI, HTTPException
import json

app = FastAPI()

# Cargar JSON de horarios
with open("tren_lunes_viernes_ida.json", encoding="utf-8") as f:
    DATA = json.load(f)

@app.get("/")
def home():
    return {"status": "ok", "message": "Train API online"}

@app.get("/get_available_timeslots")
def get_available_timeslots(origen: str = None, destino: str = None):
    # Validar parámetros
    if not origen or not destino:
        raise HTTPException(status_code=400, detail="Parámetros 'origen' y 'destino' son obligatorios")

    # Normalizar entradas
    origen = origen.strip().lower()
    destino = destino.strip().lower()

    resultados = []

    for viaje in DATA["Viajes"]:
        ruta = viaje["Ruta"]
        estaciones = [r["Estacion"].strip().lower() for r in ruta]

        if origen in estaciones and destino in estaciones:
            idx_origen = estaciones.index(origen)
            idx_destino = estaciones.index(destino)

            if idx_origen < idx_destino:
                resultados.append({
                    "parada": viaje["Parada"],
                    "salida": ruta[idx_origen]["Hora"],
                    "origen": ruta[idx_origen]["Estacion"],
                    "destino": ruta[idx_destino]["Estacion"]
                })

    if not resultados:
        raise HTTPException(status_code=404, detail="No se encontró viaje válido")

    return {"viajes": resultados}
