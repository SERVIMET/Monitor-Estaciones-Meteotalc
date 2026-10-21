from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import json
import os
import re
import ssl
import subprocess
import time
import urllib.request

# Librerías para generación de PDF
try:
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas
    REPORTLAB_DISPONIBLE = True
except ImportError:
    REPORTLAB_DISPONIBLE = False

# ==========================================
# CONFIGURACIÓN GENERAL
# ==========================================
TOLERANCIA_MINUTOS = 12
LIMITE_LECTURAS_REPETIDAS = 10
ZONA_CHILE = ZoneInfo("America/Santiago")
ARCHIVO_HISTORIAL = "historial_presion.json"
ARCHIVO_TEMPERATURA = "historial_temperatura.json"
ARCHIVO_VIENTO = "historial_viento.json"
ARCHIVO_CONGELADAS = "historial_congeladas.json"

DIAS_SEMANA_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

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
        "nombre": "Capitania de Puerto Constitucion",
        "url": "http://web.directemar.cl/met/jturno/estaciones/constitucion/index.htm",
        "lat": -35.3241667,
        "lon": -72.40805555,
        "pdf": "papeleta_constitucion_semanal.pdf"
    },
    {
        "nombre": "Capitania de Puerto Lirquen",
        "url": "http://web.directemar.cl/met/jturno/estaciones/lirquen/index.htm",
        "lat": -36.7027778,
        "lon": -72.9775,
        "pdf": "papeleta_lirquen_semanal.pdf"
    },
    {
        "nombre": "Gobernacion Maritima de Talcahuano",
        "url": "http://web.directemar.cl/met/jturno/estaciones/talcahuano/index.htm",
        "lat": -36.712,
        "lon": -73.115,
        "pdf": "papeleta_talcahuano_semanal.pdf"
    },
    {
        "nombre": "Capitania de Puerto Coronel",
        "url": "http://web.directemar.cl/met/jturno/estaciones/coronel/index.htm",
        "lat": -37.020,
        "lon": -73.150,
        "pdf": "papeleta_coronel_semanal.pdf"
    },
    {
        "nombre": "Capitania de Puerto Lota",
        "url": "http://web.directemar.cl/met/jturno/estaciones/lota/index.htm",
        "lat": -37.090,
        "lon": -73.150,
        "pdf": "papeleta_lota_semanal.pdf"
    },
    {
        "nombre": "Capitania de Puerto Lebu",
        "url": "http://web.directemar.cl/met/jturno/estaciones/lebu/index.htm",
        "lat": -37.606,
        "lon": -73.650,
        "pdf": "papeleta_lebu_semanal.pdf"
    },
    {
        "nombre": "Capitania de Puerto Carahue",
        "url": "http://web.directemar.cl/met/jturno/estaciones/carahue/index.htm",
        "lat": -38.788,
        "lon": -73.397,
        "pdf": "papeleta_carahue_semanal.pdf"
    },
    {
        "nombre": "Capitania de Puerto Corral",
        "url": "http://web.directemar.cl/met/jturno/estaciones/corral/index.htm",
        "lat": -39.883,
        "lon": -73.433,
        "pdf": "papeleta_corral_semanal.pdf"
    },
]

ESTACIONES_FAROS = [
    {
        "nombre": "Faro Isla Quiriquina",
        "id": "ITALCA20",
        "url": "https://www.wunderground.com/dashboard/pws/ITALCA20",
        "lat": -36.607,
        "lon": -73.049,
        "pdf": "papeleta_quiriquina_semanal.pdf"
    },
    {
        "nombre": "Faro Punta Hualpen",
        "id": "IHUALP1",
        "url": "https://www.wunderground.com/dashboard/pws/IHUALP1",
        "lat": -36.745,
        "lon": -73.185,
        "pdf": "papeleta_hualpen_semanal.pdf"
    },
]

ESTACIONES_IFOP = [
    {
        "nombre": "Faro Cabo Carranza",
        "url": "https://giscc.ifop.cl/doma_met/",
        "api_url": "https://giscc.ifop.cl/siom-enoscc//get_est_met/22",
        "lat": -35.5608333,
        "lon": -72.6177777,
        "pdf": "papeleta_carranza_semanal.pdf"
    },
    {
        "nombre": "Faro Isla Mocha",
        "url": "https://giscc.ifop.cl/doma_met/",
        "api_url": "https://giscc.ifop.cl/siom-enoscc//get_est_met/34",
        "lat": -38.3849472,
        "lon": -73.8688523,
        "pdf": "papeleta_mocha_semanal.pdf"
    },
]

ORDEN_ESTACIONES = [
    "Capitania de Puerto Constitucion",
    "Faro Cabo Carranza",
    "Capitania de Puerto Lirquen",
    "Faro Isla Quiriquina",
    "Gobernacion Maritima de Talcahuano",
    "Faro Punta Hualpen",
    "Capitania de Puerto Coronel",
    "Capitania de Puerto Lota",
    "Capitania de Puerto Lebu",
    "Faro Isla Mocha",
    "Capitania de Puerto Carahue",
    "Capitania de Puerto Corral",
]

MAPA_PDFS = {}
for grupo in [ESTACIONES_DIRECTEMAR, ESTACIONES_FAROS, ESTACIONES_IFOP]:
    for e in grupo:
        MAPA_PDFS[e["nombre"]] = e["pdf"]

def obtener_hora_chile():
    return datetime.now(ZONA_CHILE)

def convertir_numero(valor):
    if valor is None:
        return None
    try:
        val_str = str(valor).strip()
        if any(c in val_str.lower() for c in ["color", "purple", "line", "data", "{", "}", "none"]):
            return None
        val_clean = re.sub(r'[^\d.,\-]', '', val_str)
        if not val_clean:
            return None
        return float(val_clean.replace(",", "."))
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

def gestionar_historial_generico(archivo, clave_valor, nombre_estacion, valor, horas_retencion=25):
    if valor is None:
        return
    ahora = obtener_hora_chile()
    historial = {}
    if os.path.exists(archivo):
        try:
            with open(archivo, "r", encoding="utf-8") as f:
                historial = json.load(f)
        except Exception:
            historial = {}

    if nombre_estacion not in historial:
        historial[nombre_estacion] = []

    registros = historial[nombre_estacion]
    registros.append({"t": ahora.timestamp(), clave_valor: valor})

    limite_tiempo = ahora.timestamp() - (horas_retencion * 3600)
    registros = [r for r in registros if r["t"] >= limite_tiempo]
    historial[nombre_estacion] = registros

    try:
        with open(archivo, "w", encoding="utf-8") as f:
            json.dump(historial, f)
    except Exception:
        pass

def gestionar_historial_presion(nombre_estacion, presion_actual):
    gestionar_historial_generico(ARCHIVO_HISTORIAL, "p", nombre_estacion, presion_actual, horas_retencion=336)
    if presion_actual is None:
        return ""

    historial = {}
    if os.path.exists(ARCHIVO_HISTORIAL):
        try:
            with open(ARCHIVO_HISTORIAL, "r", encoding="utf-8") as f:
                historial = json.load(f)
        except Exception:
            return ""

    registros = historial.get(nombre_estacion, [])
    ahora = obtener_hora_chile().timestamp()
    objetivo_t = ahora - (3 * 3600)
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
    if dif > 0.2: return " ↗"
    elif dif < -0.2: return " ↘"
    else: return " ➔"

def gestionar_historial_temperatura(nombre_estacion, temp_str):
    if not temp_str or "--" in str(temp_str):
        return
    val_temp = convertir_numero(str(temp_str))
    if val_temp is not None:
        gestionar_historial_generico(ARCHIVO_TEMPERATURA, "temp", nombre_estacion, val_temp, horas_retencion=25)

def gestionar_historial_viento(nombre_estacion, viento_str):
    if not viento_str or "--" in str(viento_str):
        return
    val_viento = convertir_numero(str(viento_str))
    if val_viento is not None:
        gestionar_historial_viento_val(nombre_estacion, val_viento)

def gestionar_historial_viento_val(nombre_estacion, val_viento):
    gestionar_historial_generico(ARCHIVO_VIENTO, "viento", nombre_estacion, val_viento, horas_retencion=25)

# ==========================================
# GENERADOR DE PAPELETAS MICROBARÓGRAFOS (PDF)
# ==========================================
def generar_papeleta_pdf_estacion(nombre_est, archivo_pdf):
    if not REPORTLAB_DISPONIBLE:
        return

    historial = cargar_json_historial(ARCHIVO_HISTORIAL)
    registros = historial.get(nombre_est, [])

    ahora = obtener_hora_chile()
    inicio_semana = (ahora - timedelta(days=ahora.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    fin_semana = inicio_semana + timedelta(days=7)
    
    timestamp_inicio = inicio_semana.timestamp()
    timestamp_fin = fin_semana.timestamp()

    datos_semana = [r for r in registros if timestamp_inicio <= r["t"] <= timestamp_fin and r.get("p") is not None]

    c = canvas.Canvas(archivo_pdf, pagesize=landscape(letter))
    width, height = landscape(letter)

    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(colors.HexColor("#0f2942"))
    c.drawCentredString(width / 2.0, height - 35, "Centro Zonal de Meteorología Marina de Talcahuano")
    
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(colors.HexColor("#1e40af"))
    c.drawCentredString(width / 2.0, height - 52, f"PAPELETA DE REGISTRO BAROMÉTRICO SEMANAL — {nombre_est.upper()}")

    c.setFont("Helvetica", 9)
    c.setFillColor(colors.HexColor("#475569"))
    f_inicio_str = inicio_semana.strftime("%d-%m-%Y")
    f_fin_str = (fin_semana - timedelta(seconds=1)).strftime("%d-%m-%Y")
    c.drawCentredString(width / 2.0, height - 66, f"Semana del {f_inicio_str} al {f_fin_str}")

    margin_x = 42
    margin_top = 85
    margin_bottom = 48
    chart_w = width - (margin_x * 2)
    chart_h = height - margin_top - margin_bottom

    if datos_semana:
        presiones = [r["p"] for r in datos_semana]
        p_min = int(min(presiones)) - 2
        p_max = int(max(presiones)) + 2
    else:
        p_min, p_max = 1000, 1025

    if p_max - p_min < 10:
        p_max = p_min + 10

    c.setFillColor(colors.HexColor("#fefce8"))
    c.rect(margin_x, margin_bottom, chart_w, chart_h, fill=True, stroke=True)

    rango_p = p_max - p_min
    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#334155"))

    for p in range(p_min, p_max + 1):
        y = margin_bottom + ((p - p_min) / rango_p) * chart_h
        c.setStrokeColor(colors.HexColor("#94a3b8") if p % 5 == 0 else colors.HexColor("#cbd5e1"))
        c.setLineWidth(0.8 if p % 5 == 0 else 0.4)
        c.line(margin_x, y, margin_x + chart_w, y)

        c.drawString(margin_x - 26, y - 3, f"{p}")
        c.drawString(margin_x + chart_w + 4, y - 3, f"{p}")

    total_dias = 7
    ancho_dia = chart_w / total_dias

    for d_idx in range(total_dias):
        dt_dia = inicio_semana + timedelta(days=d_idx)
        x_dia = margin_x + (d_idx * ancho_dia)

        c.setStrokeColor(colors.HexColor("#64748b"))
        c.setLineWidth(0.8)
        c.line(x_dia, margin_bottom, x_dia, margin_bottom + chart_h)

        nombre_dia = DIAS_SEMANA_ES[dt_dia.weekday()]
        etiqueta_dia = f"{nombre_dia} {dt_dia.strftime('%d/%m')}"
        
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.HexColor("#0f172a"))
        c.drawCentredString(x_dia + (ancho_dia / 2.0), margin_bottom + chart_h + 6, etiqueta_dia)

        for h_sec in range(0, 24, 2):
            x_sub = x_dia + (h_sec / 24.0) * ancho_dia
            
            c.setStrokeColor(colors.HexColor("#cbd5e1") if h_sec % 6 == 0 else colors.HexColor("#e2e8f0"))
            c.setLineWidth(0.5 if h_sec % 6 == 0 else 0.3)
            c.line(x_sub, margin_bottom, x_sub, margin_bottom + chart_h)
            
            if h_sec > 0:
                c.setFont("Helvetica", 5.5)
                c.setFillColor(colors.HexColor("#475569"))
                y_offset = -7 if (h_sec % 4 == 2) else -13
                c.drawCentredString(x_sub, margin_bottom + y_offset, f"{h_sec:02d}")

    c.setStrokeColor(colors.HexColor("#64748b"))
    c.setLineWidth(0.8)
    c.line(margin_x + chart_w, margin_bottom, margin_x + chart_w, margin_bottom + chart_h)

    if len(datos_semana) >= 2:
        c.setStrokeColor(colors.HexColor("#1e3a8a"))
        c.setLineWidth(1.5)
        path = c.beginPath()

        total_segundos_semana = 7 * 86400
        primer_punto = True

        for r in datos_semana:
            t_rel = r["t"] - timestamp_inicio
            if t_rel < 0 or t_rel > total_segundos_semana:
                continue

            x = margin_x + (t_rel / total_segundos_semana) * chart_w
            y = margin_bottom + ((r["p"] - p_min) / rango_p) * chart_h

            if primer_punto:
                path.moveTo(x, y)
                primer_punto = False
            else:
                path.lineTo(x, y)

        c.drawPath(path, fill=False, stroke=True)

    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(colors.HexColor("#64748b"))
    c.drawString(margin_x, 15, f"Documento de registro automático generado para {nombre_est}.")
    c.drawRightString(width - margin_x, 15, f"Generado el: {ahora.strftime('%d-%m-%Y %H:%M:%S')}")

    c.save()

def consultar_directemar(est):
    try:
        req = urllib.request.Request(est["url"], headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15, context=ctx) as response:
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
                    gestionar_historial_temperatura(est["nombre"], temp)

            pres_match = re.search(r'(?:Barometer|Presion)[^\d]*([\-]?\d+(?:[.,]\d+)?)\s*(?:hPa|mb)?', texto_plano, re.IGNORECASE)
            if pres_match:
                pres_val = convertir_numero(pres_match.group(1))
                if pres_val is not None:
                    tendencia = gestionar_historial_presion(est["nombre"], pres_val)
                    pres = f"{pres_val:.1f} hPa{tendencia}"

            bearing_match = re.search(r'Wind\s*Bearing[^\d]*\d+(?:[.,]\d+)?\s*°?\s*([N,S,E,W]{1,3})', texto_plano, re.IGNORECASE)
            if not bearing_match:
                bearing_match = re.search(r'(?:Direccion\s*Viento|Wind\s*Direction)[^\w]*([N,S,E,W]{1,3})', texto_plano, re.IGNORECASE)
            if not bearing_match:
                bearing_match = re.search(r'(?:Direccion|Dir)[^\w]*(?:del\s*)?(?:Viento)?[^\w]*([N,S,E,W]{1,3})', texto_plano, re.IGNORECASE)
            if not bearing_match:
                deg_match = re.search(r'(?:Direccion|Dir|Wind\s*Direction|Bearing)[^\d]*(\d+(?:[.,]\d+)?)\s*°', texto_plano, re.IGNORECASE)
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
                    gestionar_historial_viento(est["nombre"], viento)

            racha_match = re.search(r'(?:Wind\s*Speed\s*\(gust\)|Gust|Racha|Rafaga|Rafaga)[^\d]*(\d+(?:[.,]\d+)?)\s*(?:kts|kt|knots|nudos)?', texto_plano, re.IGNORECASE)
            if racha_match:
                val = convertir_numero(racha_match.group(1))
                if val is not None:
                    racha = f"{val:.1f} kt"

            pp_match = re.search(r'Rainfall[\s\-_]+today[^\d]*(\d+(?:[.,]\d+)?)', texto_plano, re.IGNORECASE)
            if not pp_match:
                pp_match = re.search(r'(?:Precipitacion|Lluvia|Rain|Precip)[^\d]*(\d+(?:[.,]\d+)?)', texto_plano, re.IGNORECASE)
            if pp_match:
                val = convertir_numero(pp_match.group(1))
                if val is not None:
                    precipitacion = f"{val:.1f} mm"

            match_fecha = re.search(r'(?:Page\s+updated|Actualizado)\s+(\d{1,2}-\d{1,2}-\d{4}\s+\d{1,2}:\d{2}(?::\d{2})?)', texto_plano, re.IGNORECASE)
            if not match_fecha:
                return False, "SIN DATOS VALIDOS", "N/D", temp, pres, viento, dir_viento, racha, precipitacion

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

            if dif_min > TOLERANCIA_MINUTOS and not (170 <= dif_min <= 200):
                return False, f"DESACTUALIZADA ({int(dif_min)} min)", fecha_str, temp, pres, viento, dir_viento, racha, precipitacion

            congelada = verificar_estacion_congelada(est["nombre"], temp, viento, racha)
            if congelada:
                return False, f"CONGELADA ({LIMITE_LECTURAS_REPETIDAS} lect. iguales)", fecha_str, temp, pres, viento, dir_viento, racha, precipitacion

            return True, "OPERATIVA", fecha_str, temp, pres, viento, dir_viento, racha, precipitacion

    except Exception as e:
        print(f"Error Directemar {est['nombre']}: {e}")
        return False, "SIN CONEXION", "Error de red", "--", "--", "--", "", "--", "--"

def consultar_wunderground_web(est):
    try:
        api_url = f"https://api.weather.com/v2/pws/observations/current?stationId={est['id']}&format=json&units=e&apiKey=e1f10a1e78da46f5b10a1e78da96f525"
        req = urllib.request.Request(api_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15, context=ctx) as response:
            data = json.loads(response.read().decode("utf-8"))
            obs = data["observations"][0]
            imperial = obs["imperial"]

            temp_f = imperial.get("temp")
            temp = f"{(temp_f - 32.0) * 5.0 / 9.0:.1f}°C" if temp_f is not None else "--"
            gestionar_historial_temperatura(est["nombre"], temp)

            pres_inHg = imperial.get("pressure")
            pres = "--"
            if pres_inHg is not None:
                pres_val = pres_inHg * 33.86389
                tendencia = gestionar_historial_presion(est["nombre"], pres_val)
                pres = f"{pres_val:.1f} hPa{tendencia}"

            viento_mph = imperial.get("windSpeed")
            v_val = viento_mph / 1.15077945 if viento_mph is not None else None
            viento = f"{v_val:.1f} kt" if v_val is not None else "--"
            if v_val is not None:
                gestionar_historial_viento_val(est["nombre"], v_val)

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
        
    return False, "SIN CONEXION", "--", "--", "--", "", "--", "--", "Error de red"

def consultar_ifop(est):
    try:
        req = urllib.request.Request(est["api_url"], headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15, context=ctx) as response:
            texto_raw = response.read().decode("utf-8")
            data = json.loads(texto_raw)

            if isinstance(data, dict):
                def extraer_datos_serie():
                    val_t, fecha_t, val_p, p_pasado, val_v, val_r, val_d, val_pp = None, None, None, None, None, None, None, None
                    hoy_chile = obtener_hora_chile().date()
                    
                    for k, serie in data.items():
                        if isinstance(serie, dict):
                            k_lower = k.lower().strip()
                            lista_data = serie.get("data", [])
                            
                            if isinstance(lista_data, list) and len(lista_data) > 0:
                                item_data = lista_data[0]
                                if isinstance(item_data, dict) and "y" in item_data:
                                    y_vals = item_data["y"]
                                    x_vals = item_data.get("x", [])
                                    if isinstance(y_vals, list) and len(y_vals) > 0:
                                        actual = y_vals[-1]
                                        f_act = x_vals[-1] if x_vals and len(x_vals) > 0 else None
                                        
                                        if any(sub in k_lower for sub in ["temp", "temperatura", "ta", "t_aire"]):
                                            val_t, fecha_t = actual, f_act
                                        elif any(sub in k_lower for sub in ["pres", "presion", "barom", "qfe", "qff"]):
                                            val_p = actual
                                            if len(y_vals) >= 180:
                                                p_pasado = y_vals[-180]
                                            elif len(y_vals) > 1:
                                                p_pasado = y_vals[0]
                                        elif any(sub in k_lower for sub in ["dir_viento", "dd", "dir", "direccion"]):
                                            val_d = actual
                                        elif any(sub in k_lower for sub in ["ff", "viento", "speed", "vel", "intensidad"]):
                                            val_v = actual
                                        elif any(sub in k_lower for sub in ["racha", "rafaga", "gust", "max", "fx", "vmax", "vel_max"]):
                                            val_r = actual
                                        elif any(sub in k_lower for sub in ["lluvia", "pp", "precip", "precipitacion", "agua", "acum", "mm", "rain"]):
                                            valores_hoy = []
                                            if isinstance(x_vals, list) and len(x_vals) == len(y_vals):
                                                for xv, yv in zip(x_vals, y_vals):
                                                    if yv is not None and isinstance(yv, (int, float)):
                                                        try:
                                                            if isinstance(xv, (int, float)):
                                                                dt = datetime.fromtimestamp(xv / 1000.0 if xv > 1e11 else xv, tz=ZONA_CHILE)
                                                            elif isinstance(xv, str):
                                                                dt = datetime.fromisoformat(xv.replace('Z', '+00:00')).astimezone(ZONA_CHILE)
                                                            else:
                                                                dt = None
                                                            
                                                            if dt and dt.date() == hoy_chile:
                                                                valores_hoy.append(yv)
                                                        except Exception:
                                                            pass
                                            
                                            if valores_hoy:
                                                val_pp = max(valores_hoy)
                                            else:
                                                val_pp = y_vals[-1]

                    return val_t, fecha_t, val_p, p_pasado, val_v, val_r, val_d, val_pp

                temp_val, fecha_temp, pres_val, pres_pasado_val, viento_val, racha_val, dir_val, pp_val = extraer_datos_serie()

                temp_f = convertir_numero(temp_val)
                temp = f"{temp_f:.1f}°C" if temp_f is not None else "--"
                gestionar_historial_temperatura(est["nombre"], temp)

                pres_f = convertir_numero(pres_val)
                tendencia_ifop = ""
                if pres_f is not None:
                    tendencia_ifop = gestionar_historial_presion(est["nombre"], pres_f)
                    p_pasado_f = convertir_numero(pres_pasado_val)
                    if p_pasado_f is not None:
                        dif = pres_f - p_pasado_f
                        if dif > 0.2: tendencia_ifop = " ↗"
                        elif dif < -0.2: tendencia_ifop = " ↘"
                        else: tendencia_ifop = " ➔"
                    pres = f"{pres_f:.1f} hPa{tendencia_ifop}"
                else:
                    pres = "--"

                viento_f = convertir_numero(viento_val)
                viento = f"{viento_f:.1f} kt" if viento_f is not None else "--"
                gestionar_historial_viento_val(est["nombre"], viento_f)

                racha_f = convertir_numero(racha_val)
                racha = f"{racha_f:.1f} kt" if racha_f is not None else "--"

                pp_f = convertir_numero(pp_val)
                precipitacion = f"{pp_f:.1f} mm" if pp_f is not None else "0.0 mm"

                dir_num = convertir_numero(dir_val)
                if dir_num is not None:
                    dir_viento = grados_a_cardinal(dir_num)
                else:
                    dir_viento = formatear_direccion(str(dir_val)) if dir_val is not None else ""

                fecha_str = str(fecha_temp) if fecha_temp else "Reciente"
                es_valido = (temp_f is not None or viento_f is not None or pres_f is not None)
                
                congelada = verificar_estacion_congelada(est["nombre"], temp, viento, racha)
                if congelada:
                    return False, f"CONGELADA ({LIMITE_LECTURAS_REPETIDAS} lect. iguales)", fecha_str, temp, pres, viento, dir_viento, racha, precipitacion

                estado_txt = "OPERATIVA" if es_valido else "SIN DATOS VALIDOS"
                return es_valido, estado_txt, fecha_str, temp, pres, viento, dir_viento, racha, precipitacion

            return False, "DATOS NO VALIDOS", "Estructura desconocida", "--", "--", "--", "", "--", "--"

    except Exception as e:
        print(f"Error IFOP [{est['nombre']}]: {e}")
        return False, "SIN CONEXION", str(e)[:30], "--", "--", "--", "", "--", "--"

def cargar_json_historial(archivo):
    if os.path.exists(archivo):
        try:
            with open(archivo, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def generar_html(resultados_totales, hay_alerta):
    total_estaciones = len(resultados_totales)
    operativas = sum(1 for r in resultados_totales if r['ok'] is True)

    markers_js = ""
    for r in resultados_totales:
        color = "green" if r['ok'] else "red"
        dir_txt = f" ({r['dir_viento']})" if r['dir_viento'] else ""
        popup_txt = f"<b>{r['nombre']}</b><br>Estado: {r['estado']}<br>Temp: {r['temp']} | Viento: {r['viento']}{dir_txt} | Racha: {r['racha']} | Pres: {r['pres']} | Lluvia: {r['precipitacion']}<br>Reporte: {r['ultimo']}<br><a href='{r['url']}' target='_blank'>Abrir enlace ↗</a>"
        
        markers_js += f"""
        L.circleMarker([{r['lat']}, {r['lon']}], {{
            color: '{color}', fillColor: '{color}', fillOpacity: 0.8, radius: 9
        }}).addTo(map).bindPopup("{popup_txt}");
        """

    cards_html = ""
    for r in resultados_totales:
        clase = "ok" if r['ok'] else "error"
        icono = "🔴" if not r['ok'] else "🟢"
        
        etiqueta_estado = ""
        if not r['ok']:
            est_txt_lower = r['estado'].lower()
            if "desactualizada" in est_txt_lower or "sin conexion" in est_txt_lower or "sin datos" in est_txt_lower:
                etiqueta_estado = '<span style="font-size: 10px; font-weight: bold; color: #dc2626; margin-left: 4px;">(offline)</span>'
            elif "congelada" in est_txt_lower:
                etiqueta_estado = '<span style="font-size: 10px; font-weight: bold; color: #dc2626; margin-left: 4px;">(sin red)</span>'
            else:
                etiqueta_estado = '<span style="font-size: 10px; font-weight: bold; color: #dc2626; margin-left: 4px;">(offline)</span>'

        pdf_archivo = MAPA_PDFS.get(r['nombre'], "papeleta_talcahuano_semanal.pdf")
        
        card_header_html = f"""
        <div class="card-header-top">
            <span class="station-name-text" title="{r['nombre']}">{r['nombre']}</span>
            <span class="status-badge">{icono}{etiqueta_estado}</span>
        </div>
        <div class="card-header-bottom">
            <a href="{pdf_archivo}" download target="_blank" class="pdf-pill-btn" onclick="event.stopPropagation();" title="Descargar Papeleta Semanal PDF">
                📥 Descargar Papeleta Semanal PDF
            </a>
        </div>
        """

        if r['dir_viento']:
            viento_contenido = f'<span style="display: block; font-size: 0.58em; color: var(--wind-color, #1d4ed8); font-weight: 800; line-height: 1.1;">🌬️ {r["dir_viento"]}</span><span class="viento-sostenido-val" style="display: block; font-size: 0.72em; font-weight: 700; line-height: 1.1;">{r["viento"]}</span>'
        else:
            viento_contenido = f'<span style="display: block; font-size: 0.58em; color: transparent; font-weight: 800; line-height: 1.1; user-select: none;">-</span><span class="viento-sostenido-val" style="display: block; font-size: 0.72em; font-weight: 700; line-height: 1.1;">{r["viento"]}</span>'

        cuerpo_tarjeta = f"""
            <div class="card-body-content">
                <div class="row-top">
                    <div class="item-box temp-box sparkline-btn" onclick="event.preventDefault(); event.stopPropagation(); abrirModalComparativa('{r['nombre']}', 'temperatura');" title="Ver gráficos comparativos 24h">
                        🌡️ {r['temp']}
                    </div>
                    <div class="item-box sparkline-btn" onclick="event.preventDefault(); event.stopPropagation(); abrirModalComparativa('{r['nombre']}', 'viento');" title="Ver gráficos comparativos 24h">
                        {viento_contenido}
                    </div>
                    <div class="item-box"><span style="font-size: 0.58em; color: var(--wind-color, #1d4ed8); font-weight: 800; display: block; line-height: 1.1;">💨 RACHA</span><span style="font-size: 0.72em; font-weight: 700; line-height: 1.1;">{r['racha']}</span></div>
                </div>
                <div class="row-bottom-3">
                    <div class="item-box"><span style="font-size: 0.62em; font-weight: 700;">⏲️ {r['pres']}</span></div>
                    <div class="item-box sparkline-btn" onclick="event.preventDefault(); event.stopPropagation(); abrirModalComparativa('{r['nombre']}', 'presion');" title="Ver gráficos comparativos 24h">
                        <span style="font-size: 0.52em; color: var(--wind-color, #1d4ed8); font-weight: 800; display: block; line-height: 1.0;">📈 TENDENCIA 24H</span>
                        <svg class="mini-sparkline" data-estacion="{r['nombre']}" width="70" height="18" style="overflow:visible;"></svg>
                    </div>
                    <div class="item-box"><span style="font-size: 0.62em; font-weight: 700;">🌧️ {r['precipitacion']}</span></div>
                </div>
            </div>
        """

        cards_html += f"""
        <a href="{r['url']}" target="_blank" class="card-link">
            <div class="card {clase}">
                {card_header_html}
                {cuerpo_tarjeta}
                <div class="card-footer-info">
                    <span class="time">Reporte: {r['ultimo']}</span>
                    <span class="click-text">Ver ↗</span>
                </div>
            </div>
        </a>
        """

    alerta_class = "alerta-activa" if hay_alerta else ""
    alerta_banner = '<div class="banner-alerta">⚠️ ¡ATENCION: HAY ESTACIONES CON FALLAS, DESACTUALIZADAS O CONGELADAS! ⚠️</div>' if hay_alerta else ""
    hora_actual_chile = obtener_hora_chile().strftime("%d-%m-%Y %H:%M:%S")

    json_presion_str = json.dumps(cargar_json_historial(ARCHIVO_HISTORIAL))
    json_temp_str = json.dumps(cargar_json_historial(ARCHIVO_TEMPERATURA))
    json_viento_str = json.dumps(cargar_json_historial(ARCHIVO_VIENTO))

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="30">
    <title>Monitor de Estaciones Automaticas</title>
    <link rel="manifest" href="manifest.json">
    <link rel="icon" type="image/png" sizes="192x192" href="icon-192.png">
    <link rel="apple-touch-icon" sizes="192x192" href="icon-192.png">
    <link rel="icon" type="image/png" sizes="512x512" href="icon-512.png">
    <link rel="apple-touch-icon" sizes="512x512" href="icon-512.png">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        :root {{
            --bg-color: #f4f6f9;
            --text-color: #1e293b;
            --h1-color: #0f2942;
            --sub2-color: #1e40af;
            --sub-color: #64748b;
            --summary-bg: #ffffff;
            --summary-border: #cbd5e1;
            --summary-text: #0f2942;
            --card-ok-bg: linear-gradient(135deg, #dbeafe 0%, #cbd5e1 55%, #94a3b8 100%);
            --card-ok-border: #94a3b8;
            --card-error-bg: linear-gradient(135deg, #fee2e2 0%, #fecaca 55%, #f87171 100%);
            --card-error-border: #f87171;
            --station-name-color: #0f172a;
            --item-bg: rgba(255, 255, 255, 0.9);
            --item-border: rgba(255, 255, 255, 0.95);
            --item-text: #0f172a;
            --time-color: #334155;
            --click-color: #1d4ed8;
            --wind-color: #1d4ed8;
            --footer-border: rgba(255, 255, 255, 0.4);
        }}
        body.dark-mode {{
            --bg-color: #121212;
            --text-color: #e0e0e0;
            --h1-color: #ffffff;
            --sub2-color: #60a5fa;
            --sub-color: #94a3b8;
            --summary-bg: #1e1e1e;
            --summary-border: #333333;
            --summary-text: #ffffff;
            --card-ok-bg: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            --card-ok-border: #334155;
            --card-error-bg: linear-gradient(135deg, #450a0a 0%, #7f1d1d 100%);
            --card-error-border: #991b1b;
            --station-name-color: #f8fafc;
            --item-bg: rgba(30, 41, 59, 0.85);
            --item-border: rgba(51, 65, 85, 0.8);
            --item-text: #f1f5f9;
            --time-color: #cbd5e1;
            --click-color: #60a5fa;
            --wind-color: #60a5fa;
            --footer-border: rgba(255, 255, 255, 0.1);
        }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: var(--bg-color); color: var(--text-color); padding: 15px; margin: 0; transition: background-color 0.3s ease, color 0.3s ease; }}
        h1 {{ text-align: center; color: var(--h1-color); margin-bottom: 0; font-size: 22px; line-height: 1.2; font-weight: 700; }}
        .subtitle-line2 {{ text-align: center; color: var(--sub2-color); margin-bottom: 6px; font-size: 16px; font-weight: bold; }}
        .subtitle {{ text-align: center; color: var(--sub-color); margin-bottom: 12px; font-size: 12px; }}
        .summary {{ text-align: center; font-weight: bold; margin-bottom: 15px; color: var(--summary-text); font-size: 14px; background: var(--summary-bg); padding: 6px 16px; border-radius: 20px; max-width: 290px; margin-left: auto; margin-right: auto; box-shadow: 0 2px 6px rgba(0,0,0,0.06); border: 1px solid var(--summary-border); }}
        @keyframes parpadeoFondo {{ 0% {{ background-color: var(--bg-color); }} 50% {{ background-color: #fca5a5; }} 100% {{ background-color: var(--bg-color); }} }}
        body.alerta-activa {{ animation: parpadeoFondo 1.5s infinite; }}
        body.dark-mode.alerta-activa {{ animation: none !important; background-color: #121212 !important; }}
        .banner-alerta {{ background: linear-gradient(135deg, #ef4444, #dc2626); color: white; text-align: center; font-weight: bold; padding: 10px; border-radius: 8px; margin-bottom: 15px; font-size: 14px; box-shadow: 0 4px 12px rgba(239, 68, 68, 0.3); }}
        #map {{ height: 350px; width: 100%; max-width: 1200px; margin: 0 auto 20px auto; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); border: 1px solid var(--summary-border); }}
        
        /* GRILLA BLINDADA A 3 COLUMNAS FIJAS (PUNTO DE QUIBRE BAJADO A 600px PARA EVITAR EL ESCALONAMIENTO) */
        .grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 15px; max-width: 1200px; margin: 0 auto; align-items: stretch; width: 100%; box-sizing: border-box; }}
        @media (max-width: 600px) {{
            .grid {{ grid-template-columns: 1fr; }}
        }}

        .card-link {{ text-decoration: none; color: inherit; display: flex; flex-direction: column; width: 100%; min-width: 0; box-sizing: border-box; }}
        .card {{ border-radius: 14px; padding: 10px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08); transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); position: relative; overflow: hidden; display: flex; flex-direction: column; justify-content: space-between; width: 100%; height: 100%; min-width: 0; box-sizing: border-box; }}
        .card.ok {{ background: var(--card-ok-bg); border: 1px solid var(--card-ok-border); border-left: 6px solid #16a34a; }}
        .card.error {{ background: var(--card-error-bg); border: 1px solid var(--card-error-border); border-left: 6px solid #dc2626; }}
        .card:hover {{ transform: translateY(-3px); box-shadow: 0 8px 20px rgba(30, 64, 175, 0.2); }}
        .card.error:hover {{ box-shadow: 0 8px 20px rgba(220, 38, 38, 0.3); }}
        
        /* Cabecera superior: Nombre y Luz de estado */
        .card-header-top {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; min-height: 22px; width: 100%; min-width: 0; box-sizing: border-box; }}
        .station-name-text {{ font-weight: bold; font-size: 13px; color: var(--station-name-color); line-height: 1.1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 1; min-width: 0; margin-right: 6px; }}
        .status-badge {{ font-size: 11px; display: flex; align-items: center; white-space: nowrap; flex-shrink: 0; }}
        
        /* Cabecera inferior exclusiva para el botón PDF en su propia línea independiente */
        .card-header-bottom {{ margin-bottom: 6px; width: 100%; box-sizing: border-box; }}
        .pdf-pill-btn {{ font-size: 11px; font-weight: 700; color: var(--click-color); text-decoration: none; display: flex; align-items: center; justify-content: center; gap: 4px; background: rgba(255, 255, 255, 0.7); padding: 3px 8px; border-radius: 6px; border: 1px solid var(--item-border); width: 100%; box-sizing: border-box; transition: opacity 0.2s ease; }}
        body.dark-mode .pdf-pill-btn {{ background: rgba(30, 41, 59, 0.7); }}
        .pdf-pill-btn:hover {{ opacity: 0.8; text-decoration: underline; }}
        
        .card-body-content {{ display: flex; flex-direction: column; gap: 4px; margin: 4px 0; width: 100%; box-sizing: border-box; }}
        .row-top, .row-bottom-3 {{ display: grid; gap: 4px; width: 100%; box-sizing: border-box; }}
        .row-top {{ grid-template-columns: 1.1fr 1fr 1fr; }}
        .row-bottom-3 {{ grid-template-columns: 1fr 1.1fr 1fr; }}
        .item-box {{ background: var(--item-bg); padding: 4px 2px; border-radius: 6px; border: 1px solid var(--item-border); text-align: center; display: flex; flex-direction: column; justify-content: center; align-items: center; white-space: nowrap; color: var(--item-text); overflow: hidden; box-sizing: border-box; }}
        .temp-box {{ font-size: 0.85em; font-weight: 800; color: var(--item-text); }}
        .sparkline-btn {{ cursor: pointer; transition: background 0.2s ease; }}
        .sparkline-btn:hover {{ background: rgba(29, 78, 216, 0.15); border-color: var(--click-color); }}
        
        .card-footer-info {{ display: flex; justify-content: space-between; align-items: center; margin-top: 2px; border-top: 1px solid var(--footer-border); padding-top: 3px; width: 100%; box-sizing: border-box; }}
        .time {{ font-size: 0.63em; color: var(--time-color); white-space: nowrap; }}
        .click-text {{ font-size: 0.65em; color: var(--click-color); font-weight: bold; font-style: italic; white-space: nowrap; }}

        .footer-dev {{ background: linear-gradient(135deg, #0f2942, #1e3a8a); color: #f8fafc; text-align: center; font-weight: 600; padding: 10px 24px; border-radius: 30px; margin: 30px auto 15px auto; display: table; font-size: 13px; box-shadow: 0 4px 12px rgba(15, 41, 66, 0.2); border: 1px solid rgba(255,255,255,0.15); }}
        .floating-controls {{ position: fixed; top: 10px; right: 10px; display: flex; flex-direction: column; gap: 6px; z-index: 1000; }}
        .icon-btn {{ width: 36px; height: 36px; border-radius: 50%; background: var(--summary-bg); color: var(--text-color); border: 1px solid var(--summary-border); display: flex; align-items: center; justify-content: center; cursor: pointer; font-size: 14px; box-shadow: 0 2px 8px rgba(0,0,0,0.15); transition: all 0.2s ease; padding: 0; }}
        .icon-btn:hover {{ transform: scale(1.1); }}
        .wind-unit-btn {{ font-size: 11px; font-weight: 800; letter-spacing: -0.5px; }}
        .modal-overlay {{ display: none; position: fixed; z-index: 2000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.6); align-items: center; justify-content: center; backdrop-filter: blur(4px); }}
        .modal-content, .modal-content-comparativa {{ background: var(--summary-bg); color: var(--text-color); padding: 20px; border-radius: 16px; text-align: center; box-shadow: 0 10px 25px rgba(0,0,0,0.3); border: 1px solid var(--summary-border); position: relative; }}
        .modal-content {{ max-width: 320px; width: 90%; }}
        .modal-content-comparativa {{ max-width: 580px; width: 95%; max-height: 90vh; overflow-y: auto; }}
        .close-modal {{ position: absolute; top: 10px; right: 15px; font-size: 20px; font-weight: bold; cursor: pointer; color: var(--sub-color); }}
        .close-modal:hover {{ color: var(--text-color); }}
        .chart-container-box {{ background: var(--item-bg); padding: 10px; border-radius: 12px; border: 1px solid var(--item-border); position: relative; margin-bottom: 15px; }}
        .chart-tooltip {{ position: absolute; background: rgba(15, 41, 66, 0.9); color: white; padding: 4px 8px; font-size: 11px; border-radius: 4px; pointer-events: none; display: none; z-index: 3000; }}
    </style>
</head>
<body class="{alerta_class}">
    <div class="floating-controls">
        <button class="icon-btn" onclick="toggleDarkMode()" id="darkModeBtn" title="Cambiar Modo">🌙</button>
        <button class="icon-btn wind-unit-btn" onclick="toggleWindUnit()" id="windUnitBtn" title="Unidad de Viento">kt</button>
        <button class="icon-btn" onclick="openQRModal()" title="Código QR">📱</button>
    </div>

    <div id="qrModal" class="modal-overlay">
        <div class="modal-content">
            <span class="close-modal" onclick="closeQRModal()">&times;</span>
            <h3>Acceso Directo</h3>
            <div style="background: white; padding: 10px; border-radius: 12px; display: inline-block;">
                <div id="qrcode"></div>
            </div>
        </div>
    </div>

    <!-- MODAL COMPARATIVO MULTIVARIABLE -->
    <div id="comparativaModal" class="modal-overlay">
        <div class="modal-content-comparativa">
            <span class="close-modal" onclick="closeComparativaModal()">&times;</span>
            <h3 id="modal-comparativa-title" style="margin-top: 5px; margin-bottom: 3px; font-size: 17px; color: var(--h1-color);">Panel Comparativo 24h</h3>
            <p style="font-size: 12px; color: var(--sub-color); margin-bottom: 15px;">Comportamiento de las variables de la estación</p>
            
            <div id="lista-graficos-comparativos">
                <!-- Contenedor 1 -->
                <div id="box-var-1" class="chart-container-box">
                    <div id="tooltip-var-1" class="chart-tooltip"></div>
                    <h4 id="title-var-1" style="margin: 0 0 5px 0; font-size: 13px; color: var(--sub2-color);"></h4>
                    <svg id="svg-var-1" width="100%" height="180" viewBox="0 0 500 180" style="overflow:visible;"></svg>
                </div>
                <!-- Contenedor 2 -->
                <div id="box-var-2" class="chart-container-box">
                    <div id="tooltip-var-2" class="chart-tooltip"></div>
                    <h4 id="title-var-2" style="margin: 0 0 5px 0; font-size: 13px; color: var(--sub2-color);"></h4>
                    <svg id="svg-var-2" width="100%" height="180" viewBox="0 0 500 180" style="overflow:visible;"></svg>
                </div>
                <!-- Contenedor 3 -->
                <div id="box-var-3" class="chart-container-box">
                    <div id="tooltip-var-3" class="chart-tooltip"></div>
                    <h4 id="title-var-3" style="margin: 0 0 5px 0; font-size: 13px; color: var(--sub2-color);"></h4>
                    <svg id="svg-var-3" width="100%" height="180" viewBox="0 0 500 180" style="overflow:visible;"></svg>
                </div>
            </div>
        </div>
    </div>

    <h1>Monitor de Estaciones Automaticas</h1>
    <div class="subtitle-line2">Centro Zonal de Meteorologia Marina de Talcahuano</div>
    <div class="subtitle">Ultima verificacion: {hora_actual_chile} (Tolerancia: {TOLERANCIA_MINUTOS} min)</div>
    {alerta_banner}
    <div class="summary">Estaciones Operativas: {operativas} de {total_estaciones}</div>
    <div id="map"></div>
    <div class="grid">{cards_html}</div>
    <div style="text-align: center;">
        <div class="footer-dev">Desarrollado por Sgto 2° (Met.) Luis Diego Achurra Garcés &nbsp;|&nbsp; 👁️ Visitas: <span id="visitor-count">150</span></div>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/qrcodejs/1.0.0/qrcode.min.js"></script>
    <script>
        const historialPresionData = {json_presion_str};
        const historialTemperaturaData = {json_temp_str};
        const historialVientoData = {json_viento_str};

        window.addEventListener('DOMContentLoaded', () => {{
            const currentUrl = window.location.href;
            new QRCode(document.getElementById("qrcode"), {{
                text: currentUrl, width: 180, height: 180, colorDark: "#0f2942", colorLight: "#ffffff", correctLevel: QRCode.CorrectLevel.H
            }});
            renderizarSparklines();
        }});

        function openQRModal() {{ document.getElementById('qrModal').style.display = 'flex'; }}
        function closeQRModal() {{ document.getElementById('qrModal').style.display = 'none'; }}
        function closeComparativaModal() {{ document.getElementById('comparativaModal').style.display = 'none'; }}

        window.onclick = function(event) {{
            if (event.target === document.getElementById('qrModal')) closeQRModal();
            if (event.target === document.getElementById('comparativaModal')) closeComparativaModal();
        }}

        function renderizarSparklines() {{
            const elements = document.querySelectorAll('.mini-sparkline');
            elements.forEach(svg => {{
                const estacion = svg.getAttribute('data-estacion');
                const registros = historialPresionData[estacion];
                if (!registros || registros.length < 2) return;

                const ahora = Date.now() / 1000;
                const hace24h = ahora - (24 * 3600);
                const datos24h = registros.filter(r => r.t >= hace24h && r.p !== null);
                if (datos24h.length < 2) return;

                const presiones = datos24h.map(r => r.p);
                const minP = Math.min(...presiones);
                const maxP = Math.max(...presiones);
                const rangoP = maxP - minP || 1;

                const w = 70; const h = 18;
                let pathD = "";
                datos24h.forEach((r, i) => {{
                    const x = (i / (datos24h.length - 1)) * w;
                    const y = h - ((r.p - minP) / rangoP) * (h - 4) - 2;
                    if (i === 0) pathD += `M ${{x.toFixed(1)}} ${{y.toFixed(1)}}`;
                    else pathD += ` L ${{x.toFixed(1)}} ${{y.toFixed(1)}}`;
                }});

                svg.innerHTML = `<path d="${{pathD}}" fill="none" stroke="var(--wind-color, #1d4ed8)" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />`;
            }});
        }}

        function formatHora(timestampSec) {{
            const d = new Date(timestampSec * 1000);
            return d.toLocaleTimeString([], {{ hour: '2-digit', minute: '2-digit', hour12: false }});
        }}

        function renderizarUnGraficoEnBox(registros, clave, color, unit, svgId, titleId, tooltipId, tituloGrafico) {{
            document.getElementById(titleId).innerText = tituloGrafico;
            const svgChart = document.getElementById(svgId);
            
            if (!registros || registros.length < 2) {{
                svgChart.innerHTML = '<text x="250" y="90" text-anchor="middle" fill="#64748b" font-size="13">No hay suficiente historial registrado aún</text>';
                return;
            }}

            const ahora = Date.now() / 1000;
            const hace24h = ahora - (24 * 3600);
            const datos24h = registros.filter(r => r.t >= hace24h && r[clave] !== null);

            if (datos24h.length < 2) {{
                svgChart.innerHTML = '<text x="250" y="90" text-anchor="middle" fill="#64748b" font-size="13">Esperando más ciclos de lectura (24h)</text>';
                return;
            }}

            const valores = datos24h.map(r => r[clave]);
            let minV = Math.min(...valores);
            let maxV = Math.max(...valores);
            if (minV === maxV) {{ minV -= 1; maxV += 1; }}
            const margen = (maxV - minV) * 0.1;
            minV -= margen; maxV += margen;
            const rangoV = maxV - minV;

            const width = 460; const height = 130; const offsetX = 35; const offsetY = 15;
            let pathD = ""; let puntosHtml = ""; let etiquetasHora = "";

            const totalPuntos = datos24h.length;
            let horasMarcadas = new Set();

            datos24h.forEach((r, i) => {{
                const x = offsetX + (i / (totalPuntos - 1)) * (width - offsetX);
                const y = offsetY + height - ((r[clave] - minV) / rangoV) * height;
                if (i === 0) pathD += `M ${{x}} ${{y}}`;
                else pathD += ` L ${{x}} ${{y}}`;
                
                puntosHtml += `<circle cx="${{x}}" cy="${{y}}" r="4.5" fill="${{color}}" style="cursor: pointer; opacity: 0.8;" 
                    ontouchstart="mostrarTooltip(event, '${{formatHora(r.t)}}', '${{r[clave].toFixed(1)}} ${{unit}}', '${{tooltipId}}')"
                    onmouseover="mostrarTooltip(event, '${{formatHora(r.t)}}', '${{r[clave].toFixed(1)}} ${{unit}}', '${{tooltipId}}')"
                    onmouseout="ocultarTooltip('${{tooltipId}}')"
                />`;

                const d = new Date(r.t * 1000);
                const hNum = d.getHours();
                if (hNum % 2 === 0 && !horasMarcadas.has(hNum)) {{
                    horasMarcadas.add(hNum);
                    const horaExactaStr = String(hNum).padStart(2, '0') + ":00";
                    etiquetasHora += `<text x="${{x}}" y="${{offsetY + height + 20}}" text-anchor="middle" font-size="9" fill="#64748b">${{horaExactaStr}}</text>`;
                    etiquetasHora += `<line x1="${{x}}" y1="${{offsetY}}" x2="${{x}}" y2="${{offsetY + height}}" stroke="#e2e8f0" stroke-dasharray="2,2" />`;
                }}
            }});

            const medV = (minV + maxV) / 2;
            const yMin = offsetY + height; const yMed = offsetY + height / 2; const yMax = offsetY;

            svgChart.innerHTML = `
                <line x1="${{offsetX}}" y1="${{yMin}}" x2="${{width}}" y2="${{yMin}}" stroke="#cbd5e1" stroke-dasharray="3,3" />
                <line x1="${{offsetX}}" y1="${{yMed}}" x2="${{width}}" y2="${{yMed}}" stroke="#cbd5e1" stroke-dasharray="3,3" />
                <line x1="${{offsetX}}" y1="${{yMax}}" x2="${{width}}" y2="${{yMax}}" stroke="#cbd5e1" stroke-dasharray="3,3" />
                
                <text x="${{offsetX - 5}}" y="${{yMin + 4}}" text-anchor="end" font-size="9" fill="#64748b">${{minV.toFixed(1)}}</text>
                <text x="${{offsetX - 5}}" y="${{yMed + 4}}" text-anchor="end" font-size="9" fill="#64748b">${{medV.toFixed(1)}}</text>
                <text x="${{offsetX - 5}}" y="${{yMax + 4}}" text-anchor="end" font-size="9" fill="#64748b">${{maxV.toFixed(1)}}</text>
                
                ${{etiquetasHora}}
                <path d="${{pathD}}" fill="none" stroke="${{color}}" stroke-width="2.2" />
                ${{puntosHtml}}
            `;
        }}

        function abrirModalComparativa(estacion, variableSeleccionada) {{
            document.getElementById('modal-comparativa-title').innerText = 'Estación: ' + estacion;
            
            let configs = [
                {{
                    id: 'temperatura',
                    titulo: 'Temperatura (°C)',
                    registros: historialTemperaturaData[estacion],
                    clave: 'temp',
                    color: '#e11d48',
                    unit: '°C'
                }},
                {{
                    id: 'viento',
                    titulo: 'Intensidad del Viento (kt)',
                    registros: historialVientoData[estacion],
                    clave: 'viento',
                    color: '#0284c7',
                    unit: 'kt'
                }},
                {{
                    id: 'presion',
                    titulo: 'Tendencia Barométrica (hPa)',
                    registros: historialPresionData[estacion],
                    clave: 'p',
                    color: '#2563eb',
                    unit: 'hPa'
                }}
            ];

            configs.sort((a, b) => (a.id === variableSeleccionada ? -1 : b.id === variableSeleccionada ? 1 : 0));

            for (let i = 0; i < 3; i++) {{
                let cfg = configs[i];
                let boxIndex = i + 1;
                renderizarUnGraficoEnBox(
                    cfg.registros, 
                    cfg.clave, 
                    cfg.color, 
                    cfg.unit, 
                    'svg-var-' + boxIndex, 
                    'title-var-' + boxIndex, 
                    'tooltip-var-' + boxIndex, 
                    cfg.titulo
                );
            }}

            document.getElementById('comparativaModal').style.display = 'flex';
        }}

        function mostrarTooltip(evt, hora, valor, tooltipId) {{
            const tooltip = document.getElementById(tooltipId);
            tooltip.innerHTML = `<b>${{hora}}</b><br>${{valor}}`;
            tooltip.style.display = 'block';
            
            const rect = evt.target.getBoundingClientRect();
            const parentRect = tooltip.parentElement.getBoundingClientRect();
            
            let left = rect.left - parentRect.left - 25;
            let top = rect.top - parentRect.top - 45;
            
            tooltip.style.left = left + 'px';
            tooltip.style.top = top + 'px';
        }}

        function ocultarTooltip(tooltipId) {{
            document.getElementById(tooltipId).style.display = 'none';
        }}
    </script>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <script>
        var map = L.map('map').setView([-37.5, -73.2], 7);
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{ maxZoom: 12 }}).addTo(map);
        {markers_js}

        function toggleDarkMode() {{
            document.body.classList.toggle('dark-mode');
            const isDark = document.body.classList.contains('dark-mode');
            localStorage.setItem('darkMode', isDark ? 'enabled' : 'disabled');
            updateButtonText(isDark);
        }}

        function updateButtonText(isDark) {{
            const btn = document.getElementById('darkModeBtn');
            if (btn) btn.innerHTML = isDark ? '☀️' : '🌙';
        }}

        if (localStorage.getItem('darkMode') === 'enabled') {{
            document.body.classList.add('dark-mode');
            updateButtonText(true);
        }}

        let windInKnots = true;
        function toggleWindUnit() {{
            windInKnots = !windInKnots;
            localStorage.setItem('windUnit', windInKnots ? 'kt' : 'khr');
            updateWindDisplay();
        }}

        function updateWindDisplay() {{
            const btn = document.getElementById('windUnitBtn');
            if (btn) btn.innerHTML = windInKnots ? 'kt' : 'kmh';

            const itemBoxes = document.querySelectorAll('.card-body-content .item-box:not(.sparkline-btn), .viento-sostenido-val');
            itemBoxes.forEach(box => {{
                let text = box.innerHTML;
                if (text.includes('kt') || text.includes('k/hr')) {{
                    box.innerHTML = text.replace(/([\\d.,]+)\\s*(kt|k\\/hr)/gi, (match, p1, p2) => {{
                        let num = parseFloat(p1.replace(',', '.'));
                        if (isNaN(num)) return match;
                        if (!windInKnots && p2.toLowerCase() === 'kt') {{
                            let converted = (num * 1.852).toFixed(1).replace('.', ',');
                            return `${{converted}} k/hr`;
                        }} else if (windInKnots && p2.toLowerCase() !== 'kt') {{
                            let converted = (num / 1.852).toFixed(1).replace('.', ',');
                            return `${{converted}} kt`;
                        }}
                        return match;
                    }});
                }}
            }});
        }}

        if (localStorage.getItem('windUnit') === 'khr') {{
            windInKnots = false;
            setTimeout(updateWindDisplay, 100);
        }}
    </script>
</body>
</html>"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("✓ index.html actualizado con grilla fija de 3 columnas para PC.")

def generar_json_esp32(resultados_totales):
    estados_12_estaciones = [r['ok'] for r in resultados_totales]
    data_json = {"estaciones": estados_12_estaciones}
    with open("estado_leds.json", "w", encoding="utf-8") as f:
        json.dump(data_json, f)

def ejecutar_monitoreo():
    print(f"\n--- [{obtener_hora_chile().strftime('%H:%M:%S')}] Verificando litoral ---")
    resultados_dict = {}
    hubo_fallas = False

    for est in ESTACIONES_DIRECTEMAR:
        ok, estado, ultimo, temp, pres, viento, dir_viento, racha, precipitacion = consultar_directemar(est)
        if not ok: hubo_fallas = True
        resultados_dict[est["nombre"]] = {
            "nombre": est["nombre"], "url": est["url"], "lat": est["lat"], "lon": est["lon"],
            "ok": ok, "estado": estado, "ultimo": ultimo, "temp": temp, "pres": pres,
            "viento": viento, "dir_viento": dir_viento, "racha": racha, "precipitacion": precipitacion
        }

    for faro in ESTACIONES_FAROS:
        ok, estado, temp, pres, viento, dir_viento, racha, precipitacion, ultimo = consultar_wunderground_web(faro)
        if not ok: hubo_fallas = True
        resultados_dict[faro["nombre"]] = {
            "nombre": faro["nombre"], "url": faro["url"], "lat": faro["lat"], "lon": faro["lon"],
            "ok": ok, "estado": estado, "ultimo": ultimo, "temp": temp, "pres": pres,
            "viento": viento, "dir_viento": dir_viento, "racha": racha, "precipitacion": precipitacion
        }

    for est_ifop in ESTACIONES_IFOP:
        ok, estado, ultimo, temp, pres, viento, dir_viento, racha, precipitacion = consultar_ifop(est_ifop)
        if not ok: hubo_fallas = True
        resultados_dict[est_ifop["nombre"]] = {
            "nombre": est_ifop["nombre"], "url": est_ifop["url"], "lat": est_ifop["lat"], "lon": est_ifop["lon"],
            "ok": ok, "estado": estado, "ultimo": ultimo, "temp": temp, "pres": pres,
            "viento": viento, "dir_viento": dir_viento, "racha": racha, "precipitacion": precipitacion
        }

    for nombre_est, archivo_pdf in MAPA_PDFS.items():
        generar_papeleta_pdf_estacion(nombre_est, archivo_pdf)
    print("✓ Papeletas barométricas semanales generadas para todas las estaciones.")

    resultados_totales = [resultados_dict[nombre] for nombre in ORDEN_ESTACIONES if nombre in resultados_dict]
    generar_html(resultados_totales, hubo_fallas)
    generar_json_esp32(resultados_totales)
    subir_a_github()

def subir_a_github():
    try:
        print("Sincronizando cambios con GitHub...")
        archivos_a_subir = ["index.html", "estado_leds.json", ARCHIVO_HISTORIAL, ARCHIVO_TEMPERATURA, ARCHIVO_VIENTO, ARCHIVO_CONGELADAS]
        for pdf in MAPA_PDFS.values():
            if os.path.exists(pdf):
                archivos_a_subir.append(pdf)

        subprocess.run(["git", "add"] + archivos_a_subir, check=True)
        resultado = subprocess.run(["git", "commit", "-m", "Fijar grilla a 3 columnas para evitar escalonamientos en PC [skip ci]"], capture_output=True, text=True)
        if resultado.returncode != 0 and "nothing to commit" in (resultado.stdout + resultado.stderr).lower():
            print("Sin cambios nuevos para subir.")
            return
        subprocess.run(["git", "push"], check=True)
        print("✓ Sincronización completada con éxito.")
    except subprocess.CalledProcessError as e:
        print(f"Error en Git: {e}")

if __name__ == "__main__":
    ejecutar_monitoreo()