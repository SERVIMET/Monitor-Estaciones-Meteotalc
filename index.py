from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import json
import os
import re
import ssl
import subprocess
import time
import urllib.request

# ==========================================
# CONFIGURACIÓN GENERAL
# ==========================================
TOLERANCIA_MINUTOS = 12
LIMITE_LECTURAS_REPETIDAS = 10
ZONA_CHILE = ZoneInfo("America/Santiago")
ARCHIVO_HISTORIAL = "historial_presion.json"
ARCHIVO_CONGELADAS = "historial_congeladas.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9",
}

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# ==========================================
# ESTACIONES DIRECTEMAR
# ==========================================
ESTACIONES_DIRECTEMAR = [
    {
        "nombre": "Capitanía de Puerto Constitución",
        "url": "http://web.directemar.cl/met/jturno/estaciones/constitucion/index.htm",
        "lat": -35.3241667,
        "lon": -72.40805555,
    },
    {
        "nombre": "Capitanía de Puerto Lirquén",
        "url": "http://web.directemar.cl/met/jturno/estaciones/lirquen/index.htm",
        "lat": -36.7027778,
        "lon": -72.9775,
    },
    {
        "nombre": "Gobernación Marítima de Talcahuano",
        "url": "http://web.directemar.cl/met/jturno/estaciones/talcahuano/index.htm",
        "lat": -36.712,
        "lon": -73.115,
    },
    {
        "nombre": "Capitanía de Puerto Coronel",
        "url": "http://web.directemar.cl/met/jturno/estaciones/coronel/index.htm",
        "lat": -37.020,
        "lon": -73.150,
    },
    {
        "nombre": "Capitanía de Puerto Lota",
        "url": "http://web.directemar.cl/met/jturno/estaciones/lota/index.htm",
        "lat": -37.090,
        "lon": -73.150,
    },
    {
        "nombre": "Capitanía de Puerto Lebu",
        "url": "http://web.directemar.cl/met/jturno/estaciones/lebu/index.htm",
        "lat": -37.606,
        "lon": -73.650,
    },
    {
        "nombre": "Capitanía de Puerto Carahue",
        "url": "http://web.directemar.cl/met/jturno/estaciones/carahue/index.htm",
        "lat": -38.788,
        "lon": -73.397,
    },
    {
        "nombre": "Capitanía de Puerto Corral",
        "url": "http://web.directemar.cl/met/jturno/estaciones/corral/index.htm",
        "lat": -39.883,
        "lon": -73.433,
    },
]

# ==========================================
# FAROS WEATHER UNDERGROUND
# ==========================================
ESTACIONES_FAROS = [
    {
        "nombre": "Faro Isla Quiriquina",
        "id": "ITALCA20",
        "url": "https://www.wunderground.com/dashboard/pws/ITALCA20",
        "lat": -36.607,
        "lon": -73.049,
    },
    {
        "nombre": "Faro Punta Hualpén",
        "id": "IHUALP1",
        "url": "https://www.wunderground.com/dashboard/pws/IHUALP1",
        "lat": -36.745,
        "lon": -73.185,
    },
]

# ==========================================
# ESTACIONES IFOP / API JSON
# ==========================================
ESTACIONES_IFOP = [
    {
        "nombre": "Faro Cabo Carranza",
        "url": "https://giscc.ifop.cl/doma_met/",
        "api_url": "https://giscc.ifop.cl/siom-enoscc//get_est_met/22",
        "lat": -35.5608333,
        "lon": -72.6177777,
    },
    {
        "nombre": "Faro Isla Mocha",
        "url": "https://giscc.ifop.cl/doma_met/",
        "api_url": "https://giscc.ifop.cl/siom-enoscc//get_est_met/34",
        "lat": -38.3849472,
        "lon": -73.8688523,
    },
]

ORDEN_ESTACIONES = [
    "Capitanía de Puerto Constitución",
    "Faro Cabo Carranza",
    "Capitanía de Puerto Lirquén",
    "Faro Isla Quiriquina",
    "Gobernación Marítima de Talcahuano",
    "Faro Punta Hualpén",
    "Capitanía de Puerto Coronel",
    "Capitanía de Puerto Lota",
    "Capitanía de Puerto Lebu",
    "Faro Isla Mocha",
    "Capitanía de Puerto Carahue",
    "Capitanía de Puerto Corral",
]

def obtener_hora_chile():
    return datetime.now(ZONA_CHILE)

def convertir_numero(valor):
    if valor is None:
        return None
    try:
        val_str = str(valor).strip()
        if any(c in val_str.lower() for c in ["color", "purple", "line", "data", "{", "}"]):
            return None
        return float(val_str.replace(",", "."))
    except (ValueError, TypeError):
        return None

def formatear_direccion(dir_str):
    if not dir_str:
        return ""
    d = str(dir_str).upper().strip()
    if any(c in d.lower() for c in ["color", "purple", "line", "data", "{", "}"]):
        return ""
    if len(d) == 3:
        return f"{d[0]}/{d[1:]}"
    return d

def grados_a_cardinal(grados):
    if grados is None:
        return "N/D"
    direcciones = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    indice = int((grados + 11.25) / 22.5) % 16
    return formatear_direccion(direcciones[indice])

def verificar_estacion_congelada(nombre_estacion, temp, viento, racha):
    estaciones_excluidas = ["faro cabo carranza", "faro isla mocha"]
    if nombre_estacion.lower() in estaciones_excluidas:
        return False

    historial = {}
    if os.path.exists(ARCHIVO_CONGELADAS):
        try:
            with open(ARCHIVO_CONGELADAS, "r", encoding="utf-8") as f:
                historial = json.load(f)
        except Exception:
            historial = {}

    firma_actual = f"{temp}_{viento}_{racha}"
    
    if nombre_estacion not in historial:
        historial[nombre_estacion] = {"firma": firma_actual, "contador": 1}
    else:
        datos_est = historial[nombre_estacion]
        if datos_est.get("firma") == firma_actual:
            datos_est["contador"] = datos_est.get("contador", 1) + 1
        else:
            historial[nombre_estacion] = {"firma": firma_actual, "contador": 1}

    try:
        with open(ARCHIVO_CONGELADAS, "w", encoding="utf-8") as f:
            json.dump(historial, f)
    except Exception:
        pass

    return historial[nombre_estacion]["contador"] >= LIMITE_LECTURAS_REPETIDAS

def gestionar_historial_presion(nombre_estacion, presion_actual):
    ahora = obtener_hora_chile()
    historial = {}
    if os.path.exists(ARCHIVO_HISTORIAL):
        try:
            with open(ARCHIVO_HISTORIAL, "r", encoding="utf-8") as f:
                historial = json.load(f)
        except Exception:
            historial = {}

    if nombre_estacion not in historial:
        historial[nombre_estacion] = []

    registros = historial[nombre_estacion]
    registros.append({"t": ahora.timestamp(), "p": presion_actual})

    limite_tiempo = ahora.timestamp() - (3.5 * 3600)
    registros = [r for r in registros if r["t"] >= limite_tiempo]
    historial[nombre_estacion] = registros

    try:
        with open(ARCHIVO_HISTORIAL, "w", encoding="utf-8") as f:
            json.dump(historial, f)
    except Exception:
        pass

    if presion_actual is None:
        return ""

    objetivo_t = ahora.timestamp() - (3 * 3600)
    candidatos = [r for r in registros if abs(r["t"] - objetivo_t) <= (45 * 60)]

    if not candidatos:
        candidatos_antiguos = [r for r in registros if r["t"] <= objetivo_t + 1800]
        if candidatos_antiguos:
            presion_pasada = candidatos_antiguos[0]["p"]
        else:
            return ""
    else:
        candidatos.sort(key=lambda x: abs(x["t"] - objetivo_t))
        presion_pasada = candidatos[0]["p"]

    if presion_pasada is None:
        return ""

    dif = presion_actual - presion_pasada

    if dif > 0.2:
        return " ↗"
    elif dif < -0.2:
        return " ↘"
    else:
        return " ➔"

def consultar_directemar(est):
    try:
        req = urllib.request.Request(est["url"], headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
            html = response.read().decode("utf-8", errors="ignore")
            
            texto_plano = re.sub(r'<[^>]+>', ' ', html)
            texto_plano = texto_plano.replace('\xa5', ' ').replace('\xa0', ' ').replace('&nbsp;', ' ').replace('&deg;', '°').replace('&#176;', '°')
            texto_plano = re.sub(r'\s+', ' ', texto_plano).strip()

            temp, pres, viento, dir_viento, racha