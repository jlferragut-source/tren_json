from fastapi import FastAPI, HTTPException
import json
from datetime import datetime
from typing import List, Dict, Optional

app = FastAPI()

# Cargar el JSON con los horarios
with open("tren_lunes_viernes_ida.json", encoding="utf-8") as f:
    DATA = json.load(f)

@app.get("/")
def home():
    return {"status": "ok", "message": "Train API online"}

@app.get("/get_available_timeslots")
def get_available_timeslots(origen: str, destino: str, hora_consulta: Optional[str] = None):
    """
    Devuelve los horarios disponibles desde 'origen' hacia 'destino'.
    Si se proporciona hora_consulta, devuelve el próximo tren después de esa hora.
    Si no, devuelve todos los horarios disponibles.
    """
    viajes_validos = []
    
    for viaje in DATA["Viajes"]:
        ruta = viaje["Ruta"]
        estaciones = [r["Estacion"] for r in ruta]

        if origen in estaciones and destino in estaciones:
            idx_origen = estaciones.index(origen)
            idx_destino = estaciones.index(destino)
            if idx_origen < idx_destino:
                hora_salida = ruta[idx_origen]["Hora"]
                
                viaje_info = {
                    "parada": viaje["Parada"],
                    "salida": hora_salida,
                    "origen": origen,
                    "destino": destino
                }
                
                # Si hay hora de consulta, verificar si es después
                if hora_consulta:
                    try:
                        hora_consulta_dt = datetime.strptime(hora_consulta, "%H:%M").time()
                        hora_salida_dt = datetime.strptime(hora_salida, "%H:%M").time()
                        if hora_salida_dt >= hora_consulta_dt:
                            viajes_validos.append(viaje_info)
                    except ValueError:
                        continue
                else:
                    viajes_validos.append(viaje_info)
    
    if viajes_validos:
        # Ordenar por hora
        viajes_validos.sort(key=lambda x: x["salida"])
        
        if hora_consulta:
            # Devolver solo el próximo tren
            return viajes_validos[0]
        else:
            # Devolver todos los horarios
            return {
                "todos_los_horarios": viajes_validos,
                "total_trenes": len(viajes_validos)
            }
    
    raise HTTPException(status_code=404, detail="No se encontró viaje válido")

# Endpoint específico para el próximo tren
@app.get("/proximo_tren")
def proximo_tren(origen: str, destino: str, hora_actual: str):
    """Endpoint específico para obtener el próximo tren después de una hora dada"""
    return get_available_timeslots(origen, destino, hora_actual)

# Endpoint para todos los horarios
@app.get("/todos_horarios")
def todos_horarios(origen: str, destino: str):
    """Endpoint para obtener todos los horarios disponibles"""
    return get_available_timeslots(origen, destino)
