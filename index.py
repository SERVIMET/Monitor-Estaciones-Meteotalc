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
                return False, "SIN DATOS VÁLIDOS", "N/D", temp, pres, viento, dir_viento, racha, precipitacion

            fecha_str = match_fecha.group(1)
            partes_f = fecha_str.split()
            if len(partes_f) == 2:
                fecha_p, hora_p = partes_f
                sub_hora = hora_p.split(":")
                if len(sub_hora[0]) == 1:
                    sub_hora[0] = "0" + sub_hora[0]
                    fecha_str = f"{fecha_p} {':'.join(sub_hora)}"

            formato_fecha = "%d-%m-%Y %H:%M:%S" if fecha_str.count(":") == 2 else "%d-%m-%Y %H:%M"
            fecha_estacion = datetime.strptime(fecha_str, formato_fecha).replace(tzinfo=ZONA_CHILE)
            dif_min = abs((obtener_hora_chile() - fecha_estacion).total_seconds() / 60)

            congelada = verificar_estacion_congelada(est["nombre"], temp, viento, racha)
            if congelada:
                return False, f"CONGELADA ({LIMITE_LECTURAS_REPETIDAS} lect. iguales)", fecha_str, temp, pres, viento, dir_viento, racha, precipitacion

            if dif_min <= TOLERANCIA_MINUTOS or (170 <= dif_min <= 200):
                return True, "OPERATIVA", fecha_str, temp, pres, viento, dir_viento, racha, precipitacion
            else:
                return False, f"DESACTUALIZADA ({int(dif_min)} min)", fecha_str, temp, pres, viento, dir_viento, racha, precipitacion

    except Exception as e:
        print(f"Error Directemar {est['nombre']}: {e}")
        return False, "SIN CONEXIÓN", "Error de red", "--", "--", "--", "", "--", "--"

def consultar_wunderground_web(est):
    try:
        api_url = f"https://api.weather.com/v2/pws/observations/current?stationId={est['id']}&format=json&units=e&apiKey=e1f10a1e78da46f5b10a1e78da96f525"
        req = urllib.request.Request(api_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
            data = json.loads(response.read().decode("utf-8"))
            obs = data["observations"][0]
            imperial = obs["imperial"]

            temp_f = imperial.get("temp")
            temp = f"{(temp_f - 32.0) * 5.0 / 9.0:.1f}°C" if temp_f is not None else "--"

            pres_inHg = imperial.get("pressure")
            pres = "--"
            if pres_inHg is not None:
                pres_val = pres_inHg * 33.86389
                tendencia = gestionar_historial_presion(est["nombre"], pres_val)
                pres = f"{pres_val:.1f} hPa{tendencia}"

            viento_mph = imperial.get("windSpeed")
            viento = f"{viento_mph / 1.15077945:.1f} kt" if viento_mph is not None else "--"

            gust_mph = imperial.get("windGust")
            racha = f"{gust_mph / 1.15077945:.1f} kt" if gust_mph is not None else "--"

            wind_dir_deg = obs.get("winddir")
            dir_viento = grados_a_cardinal(wind_dir_deg)

            precip_in = imperial.get("precipTotal", 0.0)
            if precip_in is not None:
                precip_mm = precip_in * 25.4
                precipitacion = f"{precip_mm:.1f} mm"
            else:
                precipitacion = "0.0 mm"

            obs_time = obs.get("obsTimeLocal", "Reciente")

            congelada = verificar_estacion_congelada(est["nombre"], temp, viento, racha)
            if congelada:
                return False, f"CONGELADA ({LIMITE_LECTURAS_REPETIDAS} lect. iguales)", temp, pres, viento, dir_viento, racha, precipitacion, str(obs_time)

            return True, "OPERATIVA", temp, pres, viento, dir_viento, racha, precipitacion, str(obs_time)
    except Exception as e:
        print(f"Error WU [{est['nombre']}]: {e}")
        
    return False, "SIN CONEXIÓN", "--", "--", "--", "", "--", "--", "Error de red"

def consultar_ifop(est):
    try:
        req = urllib.request.Request(est["api_url"], headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
            texto_raw = response.read().decode("utf-8")
            data = json.loads(texto_raw)

            if isinstance(data, dict):
                def extraer_datos_serie():
                    val_t, fecha_t, val_p