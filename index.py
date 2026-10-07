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
# CONFIGURACION GENERAL
# ==========================================
TOLERANCIA_MINUTOS = 12
LIMITE_LECTURAS_REPETIDAS = 10
ZONA_CHILE = ZoneInfo("America/Santiago")
ZONA_PASCUA = ZoneInfo("Pacific/Easter")
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
        "nombre": "Capitania de Puerto Chanaral",
        "url": "http://web.directemar.cl/met/jturno/estaciones/chanaral/index.htm",
        "lat": -26.347,
        "lon": -70.621,
    },
    {
        "nombre": "Capitania de Puerto Caldera",
        "url": "http://web.directemar.cl/met/jturno/estaciones/caldera/index.htm",
        "lat": -27.068,
        "lon": -70.819,
    },
    {
        "nombre": "Capitania de Puerto Hanga Roa",
        "url": "http://web.directemar.cl/met/jturno/estaciones/pascua/index.htm",
        "lat": -27.150,
        "lon": -109.429,
        "es_insular": True,
    },
    {
        "nombre": "Capitania de Puerto Huasco",
        "url": "http://web.directemar.cl/met/jturno/estaciones/huasco/index.htm",
        "lat": -28.468,
        "lon": -71.226,
    },
    {
        "nombre": "Faro Punta Tortuga Coquimbo",
        "url": "http://web.directemar.cl/met/jturno/estaciones/tortuga/index.htm",
        "lat": -29.939,
        "lon": -71.352,
    },
    {
        "nombre": "Capitania de Puerto Los Vilos",
        "url": "http://web.directemar.cl/met/jturno/estaciones/losvilos/index.htm",
        "lat": -31.916,
        "lon": -71.516,
    },
    {
        "nombre": "Capitania de Puerto Quintero",
        "url": "http://web.directemar.cl/met/jturno/estaciones/quintero/index.htm",
        "lat": -32.778,
        "lon": -71.531,
    },
    {
        "nombre": "Colegio Capellan Pascal (Las Salinas)",
        "url": "http://web.directemar.cl/met/jturno/estaciones/lassalinas/index.htm",
        "lat": -33.015,
        "lon": -71.550,
    },
    {
        "nombre": "Faro Extremo Molo de Abrigo Valparaiso",
        "url": "http://web.directemar.cl/met/jturno/estaciones/valparaiso/index.htm",
        "lat": -33.036,
        "lon": -71.631,
    },
    {
        "nombre": "Faro Punta Panul San Antonio",
        "url": "http://web.directemar.cl/met/jturno/estaciones/panul/index.htm",
        "lat": -33.578,
        "lon": -71.616,
    },
    {
        "nombre": "Capitania de Puerto Juan Fernandez",
        "url": "http://web.directemar.cl/met/jturno/estaciones/cumberland/index.htm",
        "lat": -33.635,
        "lon": -78.841,
        "es_insular": True,
    },
    {
        "nombre": "Capitania de Puerto Pichilemu",
        "url": "http://web.directemar.cl/met/jturno/estaciones/pichilemu/index.htm",
        "lat": -34.391,
        "lon": -72.001,
    },
]

# ==========================================
# ESTACIONES WEATHERLINK
# ==========================================
ESTACIONES_WEATHERLINK = [
    {
        "nombre": "Universidad de Valparaiso (sede Montemar)",
        "url": "https://weatherlink.com/embeddablePage/show/a1debe35d26b4e2dbcf82122501f5fa6/fullscreen",
        "lat": -32.952,
        "lon": -71.553,
    },
    {
        "nombre": "Club de Yates Recreo (Vina del Mar)",
        "url": "https://weatherlink.com/embeddablePage/show/0c66339eed4f47d4a9240ed0b66c992/fullscreen",
        "lat": -33.027,
        "lon": -71.554,
    },
    {
        "nombre": "WL Chilquinta Muelle Baron (Valparaiso)",
        "url": "https://weatherlink.com/embeddablePage/show/6342b5802c854216a359487f335f3718/fullscreen",
        "lat": -33.042,
        "lon": -71.603,
    },
    {
        "nombre": "Dique Flotante Valparaiso III",
        "url": "https://weatherlink.com/embeddablePage/show/1e4869cc59824e6893fc56b963304664/fullscreen",
        "lat": -33.038,
        "lon": -71.621,
    },
    {
        "nombre": "Cofradia Nautica del Pacifico (Algarrobo)",
        "url": "https://weatherlink.com/embeddablePage/show/9fa531d050e648a9a8aa6bb7026c3902/fullscreen",
        "lat": -33.367,
        "lon": -71.666,
    },
]

ORDEN_ESTACIONES = [
    "Capitania de Puerto Chanaral",
    "Capitania de Puerto Caldera",
    "Capitania de Puerto Hanga Roa",
    "Capitania de Puerto Huasco",
    "Faro Punta Tortuga Coquimbo",
    "Capitania de Puerto Los Vilos",
    "Capitania de Puerto Quintero",
    "Universidad de Valparaiso (sede Montemar)",
    "Colegio Capellan Pascal (Las Salinas)",
    "Club de Yates Recreo (Vina del Mar)",
    "WL Chilquinta Muelle Baron (Valparaiso)",
    "Dique Flotante Valparaiso III",
    "Faro Extremo Molo de Abrigo Valparaiso",
    "Cofradia Nautica del Pacifico (Algarrobo)",
    "Faro Punta Panul San Antonio",
    "Capitania de Puerto Juan Fernandez",
    "Capitania de Puerto Pichilemu",
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

            temp, pres, viento, dir_viento, racha, precipitacion = "--", "--", "--", "", "--", "--"
            pres_val = None

            temp_match = re.search(r'(?:Temperatura|Temperature)\s*[:]?\s*([\-]?\d+(?:[.,]\d+)?)', texto_plano, re.IGNORECASE)
            if temp_match:
                val = convertir_numero(temp_match.group(1))
                if val is not None:
                    temp = f"{val:.1f}°C"

            pres_match = re.search(r'(?:Barometer|Presi[oó]n)[^\d]*([\-]?\d+(?:[.,]\d+)?)\s*(?:hPa|mb)?', texto_plano, re.IGNORECASE)
            if pres_match:
                pres_val = convertir_numero(pres_match.group(1))
                if pres_val is not None:
                    tendencia = gestionar_historial_presion(est["nombre"], pres_val)
                    pres = f"{pres_val:.1f} hPa{tendencia}"

            bearing_match = re.search(r'Wind\s*Bearing[^\d]*\d+(?:[.,]\d+)?\s*°?\s*([N,S,E,W]{1,3})', texto_plano, re.IGNORECASE)
            if not bearing_match:
                bearing_match = re.search(r'(?:Direcci[oó]n\s*Viento|Wind\s*Direction)[^\w]*([N,S,E,W]{1,3})', texto_plano, re.IGNORECASE)
            if not bearing_match:
                bearing_match = re.search(r'(?:Direcci[oó]n|Dir)[^\w]*(?:del\s*)?(?:Viento)?[^\w]*([N,S,E,W]{1,3})', texto_plano, re.IGNORECASE)
            if not bearing_match:
                deg_match = re.search(r'(?:Direcci[oó]n|Dir|Wind\s*Direction|Bearing)[^\d]*(\d+(?:[.,]\d+)?)\s*°', texto_plano, re.IGNORECASE)
                if deg_match:
                    grados_val = convertir_numero(deg_match.group(1))
                    if grados_val is not None:
                        dir_viento = grados_a_cardinal(grados_val)

            if bearing_match and not dir_viento:
                dir_viento = formatear_direccion(bearing_match.group(1))

            viento_match = re.search(r'Wind\s*Speed\s*\(avg\)[^\d]*(\d+(?:[.,]\d+)?)\s*(?:kts|kt|knots|nudos)?', texto_plano, re.IGNORECASE)
            if not viento_match:
                viento_match = re.search(r'Wind\s*Speed[^\d]*(\d+(?:[.,]\d+)?)\s*(?:kts|kt|knots|nudos)?', texto_plano, re.IGNORECASE)
            if not viento_match:
                viento_match = re.search(r'Viento[^\d]*(\d+(?:[.,]\d+)?)\s*(?:kts|kt|knots|nudos)?', texto_plano, re.IGNORECASE)
            
            if viento_match:
                val = convertir_numero(viento_match.group(1))
                if val is not None:
                    viento = f"{val:.1f} kt"

            racha_match = re.search(r'(?:Wind\s*Speed\s*\(gust\)|Gust|Racha|Ráfaga|Rafaga)[^\d]*(\d+(?:[.,]\d+)?)\s*(?:kts|kt|knots|nudos)?', texto_plano, re.IGNORECASE)
            if racha_match:
                val = convertir_numero(racha_match.group(1))
                if val is not None:
                    racha = f"{val:.1f} kt"

            pp_match = re.search(r'Rainfall[\s\-_]+today[^\d]*(\d+(?:[.,]\d+)?)', texto_plano, re.IGNORECASE)
            if not pp_match:
                pp_match = re.search(r'(?:Precipitaci[oó]n|Lluvia|Rain|Precip)[^\d]*(\d+(?:[.,]\d+)?)', texto_plano, re.IGNORECASE)
            if pp_match:
                val = convertir_numero(pp_match.group(1))
                if val is not None:
                    precipitacion = f"{val:.1f} mm"

            match_fecha = re.search(r'(?:Page\s+updated|Actualizado)\s+(\d{1,2}-\d{1,2}-\d{4}\s+\d{1,2}:\d{2}(?::\d{2})?)', texto_plano, re.IGNORECASE)
            if not match_fecha:
                return False, "SIN FECHA", "N/D", temp, pres, viento, dir_viento, racha, precipitacion

            fecha_str = match_fecha.group(1)
            partes_f = fecha_str.split()
            if len(partes_f) == 2:
                fecha_p, hora_p = partes_f
                sub_hora = hora_p.split(":")
                if len(sub_hora[0]) == 1:
                    sub_hora[0] = "0" + sub_hora[0]
                    fecha_str = f"{fecha_p} {':'.join(sub_hora)}"

            formato_fecha = "%d-%m-%Y %H:%M:%S" if fecha_str.count(":") == 2 else "%d-%m-%Y %H:%M"
            
            try:
                if est.get("es_insular"):
                    fecha_estacion = datetime.strptime(fecha_str, formato_fecha).replace(tzinfo=ZONA_PASCUA)
                    ahora_local = datetime.now(ZONA_PASCUA)
                else:
                    fecha_estacion = datetime.strptime(fecha_str, formato_fecha).replace(tzinfo=ZONA_CHILE)
                    ahora_local = obtener_hora_chile()

                dif_min = abs((ahora_local - fecha_estacion).total_seconds() / 60)
                limite_actual = TOLERANCIA_MINUTOS
            except Exception:
                dif_min = 0 

            congelada = verificar_estacion_congelada(est["nombre"], temp, viento, racha)
            if congelada:
                return False, f"CONGELADA ({LIMITE_LECTURAS_REPETIDAS} lect. iguales)", fecha_str, temp, pres, viento, dir_viento, racha, precipitacion

            if dif_min <= limite_actual:
                return True, "OPERATIVA", fecha_str, temp, pres, viento, dir_viento, racha, precipitacion
            else:
                return False, f"DESACTUALIZADA ({int(dif_min)} min)", fecha_str, temp, pres, viento, dir_viento, racha, precipitacion

    except Exception as e:
        print(f"Error Directemar {est['nombre']}: {e}")
        return False, "SIN CONEXION", "Error de red", "--", "--", "--", "", "--", "--"

def consultar_weatherlink(est):
    try:
        req = urllib.request.Request(est["url"], headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
            html = response.read().decode("utf-8", errors="ignore")
            
            texto_plano = re.sub(r'<[^>]+>', ' ', html)
            texto_plano = texto_plano.replace('\xa5', ' ').replace('\xa0', ' ').replace('&nbsp;', ' ').replace('&deg;', '°').replace('&#176;', '°')
            texto_plano = re.sub(r'\s+', ' ', texto_plano).strip()

            temp, pres, viento, dir_viento, racha, precipitacion = "--", "--", "--", "", "--", "--"
            pres_val = None

            temp_match = re.search(r'([\-]?\d+(?:[.,]\d+)?)\s*°\s*C\s+currently', texto_plano, re.IGNORECASE)
            if temp_match:
                val = convertir_numero(temp_match.group(1))
                if val is not None:
                    temp = f"{val:.1f}°C"

            viento_match = re.search