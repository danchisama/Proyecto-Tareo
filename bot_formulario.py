import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import logging
import requests
import sqlite3
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
)

# ================= CONFIGURACIÓN =================
# 1. Tu Token de BotFather
load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
# 2. FORMULARIO DE RESPALDO (El que ya tienes)
URL_RESPALDO = os.getenv('URL_RESPALDO')
# FORMULARIO OFICIAL (Sustituye los entry. la misma cantidad y orden que el respaldo)
URL_OFICIAL = os.getenv('URL_OFICIAL')  

# 3. Mapeo de tus campos (Reemplaza los números por tus IDs de entry.xxxx)
# El formato es: 'id': {'nombre': 'Etiqueta', 'opcional': False, 'tipo': 'texto' | 'lista'}
CAMPOS_RESPALDO = {
    'entry.2005620554': {'nombre': 'Responsable','opcional':False, 'tipo':'lista'},
    'entry.1045781291': {'nombre': 'Cliente', 'opcional':False, 'tipo':'lista'},
    'entry.1065046570': {'nombre': 'Otro cliente', 'opcional':True, 'tipo':'texto'},
    'entry.1166974658': {'nombre': 'Tipo de soporte', 'opcional':False, 'tipo':'lista'},
    'entry.839337160': {'nombre': 'Tiempo de atencion', 'opcional':False, 'tipo':'num_horas'},
    'entry.292238941': {'nombre': 'Fecha', 'opcional':False, 'tipo':'fecha'}
    # Agrega aquí todos los campos que necesites...
}

CAMPOS_OFICIAL = {
    'entry.1063817524': {'nombre': 'Responsable','opcional':False, 'tipo':'lista'},
    'entry.637947358': {'nombre': 'Cliente', 'opcional':False, 'tipo':'lista'},
    'entry.1417292649': {'nombre': 'Otro cliente', 'opcional':True, 'tipo':'texto'},
    'entry.1343289606': {'nombre': 'Tipo de soporte', 'opcional':False, 'tipo':'lista'},
    'entry.88038586': {'nombre': 'Tiempo de atencion', 'opcional':False, 'tipo':'num_horas'},
    'entry.467260638': {'nombre': 'Fecha', 'opcional':False, 'tipo':'fecha'}
}


# OPCIONES PARA LOS CAMPOS TIPO 'lista'
# El ID debe coincidir con el de CAMPOS_FORMULARIO
OPCIONES_LISTAS = {
    'entry.2005620554': ['Dante Uechi Ota'],
    'entry.1045781291': ['SOLANA COMERCIAL S.A.C. - DOLLAR CITY', 'EMPRESAS COMERCIALES S.A. - BATA', 'INNOVA SCHOOLS', 'OTROS'],
    'entry.1166974658': ['CAPACITACION CLIENTE', 'CAPACITACION INTERNA', 'REUNION CON PROVEEDOR', 'REUNION CON CLIENTE', 'REUNION EN CAMPO', 'CONFIGURACION DE EQUIPOS', 'APOYO ADMINISTRATIVO', 'APOYO LOGISTICO', 'APOYO A SOPORTE', 'CURSOS SECURITAS', 'APOYO TI'],
    # Agrega aquí los IDs de otros campos que sean listas y sus opciones
}

# Definimos el orden de las preguntas basándonos en los valores del diccionario anterior
ORDEN_PREGUNTAS = list(CAMPOS_RESPALDO.keys())
META_DIARIA = 9.0
# =================================================

# --- FUNCIÓN CONVERSORA DE TIEMPO ---
def convertir_duracion_a_decimal(tiempo_str):
    """Convierte 'HH:MM:SS' o 'MM:SS' a horas decimales (ej: '00:30:00' -> 0.5)"""
    try:
        partes = tiempo_str.split(':')
        if len(partes) == 3: # HH:MM:SS
            h, m, s = map(int, partes)
        elif len(partes) == 2: # MM:SS
            h = 0
            m, s = map(int, partes)
        else:
            return 0.0

        return h + (m / 60.0) + (s / 3600.0)
    except:
        return 0.0

# --- LÓGICA DE BASE DE DATOS ---
def init_db():
    conn = sqlite3.connect('horas_trabajo.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS registro (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, horas REAL)')
    conn.commit()
    conn.close()

def guardar_horas(fecha, horas):
    conn = sqlite3.connect('horas_trabajo.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO registro (fecha, horas) VALUES (?, ?)', (fecha, horas))
    conn.commit()
    conn.close()

def obtener_resumen_semanal():
    conn = sqlite3.connect('horas_trabajo.db')
    cursor = conn.cursor()
    hoy = datetime.now().date()
    lunes = hoy - timedelta(days=hoy.weekday())
    cursor.execute('SELECT fecha, SUM(horas) FROM registro WHERE fecha >= ? GROUP BY fecha', (lunes.isoformat(),))
    datos = cursor.fetchall()
    conn.close()
    return datos

def obtener_resumen_diario():
    conn = sqlite3.connect('horas_trabajo.db')
    cursor = conn.cursor()
    hoy = datetime.now().date()
    cursor.execute('SELECT fecha, SUM(horas) FROM registro WHERE fecha = ? GROUP BY fecha', (hoy.isoformat(),))
    datos = cursor.fetchall()
    conn.close()
    return datos    
    

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Reiniciamos el contador de pasos y limpiamos los datos anteriores
    context.user_data['step'] = 0
    # Opcional: si quieres borrar las respuestas anteriores para evitar errores
    # context.user_data.clear()
    # context.user_data['step'] = 0
    # ---------------------------------

    first_field = ORDEN_PREGUNTAS[0]
    nombre_campo = CAMPOS_RESPALDO[first_field]['nombre']

    # Verificar si el primer campo es una lista para mostrar botones
    reply_markup = None
    if CAMPOS_RESPALDO[first_field]['tipo'] == 'lista':
        opciones = OPCIONES_LISTAS.get(first_field, [])
        # Organiza las opciones en filas de 2 botones
        keyboard = [opciones[i:i + 2] for i in range(0, len(opciones), 2)]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(
        "👋 ¡Hola! Vamos a llenar el formulario.\n\n"
        f"Para empezar: ¿{nombre_campo}?",
        reply_markup=reply_markup
    )
    return 0

async def process_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        step = context.user_data.get('step', 0)
        answer = update.message.text

        field_id = ORDEN_PREGUNTAS[step]
        field_config = CAMPOS_RESPALDO[field_id]

        # --- LÓGICA DE BOTONES INTELIGENTES ---
        if field_config['tipo'] == 'fecha' and answer.lower() == 'hoy':
            answer = datetime.now().strftime('%Y-%m-%d') # Formato 2023-11-06
            #answer = datetime.now().strftime('%d/%m/%Y') # Formato 06/11/2023
        # --------------------------------------

        # Manejo de opcionales
        if field_config['opcional'] and (answer.lower() in ['no', 'ninguno', 'nada', 'n/a', '']):
            context.user_data[field_id] = ""
        else:
            context.user_data[field_id] = answer

        step += 1

        if step < len(ORDEN_PREGUNTAS):
            context.user_data['step'] = step
            next_field_id = ORDEN_PREGUNTAS[step]
            next_config = CAMPOS_RESPALDO[next_field_id]

            # Determinar si el siguiente campo es una lista para mostrar botones
            reply_markup = None
            if next_config['tipo'] == 'lista':
                opciones = OPCIONES_LISTAS.get(next_field_id, [])
                keyboard = [opciones[i:i + 2] for i in range(0, len(opciones), 2)]
                reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

            # Botones para FECHA (Hoy)
            elif next_config['tipo'] == 'fecha':
                reply_markup = ReplyKeyboardMarkup([['Hoy']], one_time_keyboard=True, resize_keyboard=True)

            msg = f"Gracias. Ahora: ¿{next_config['nombre']}?"
            if next_config['opcional']:
                msg += "\n(Puedes escribir 'no' para dejarlo vacío)"

            await update.message.reply_text(msg, reply_markup=reply_markup)
            return step
        else:
            # Enviar al formulario
            await update.message.reply_text("⏳ Enviando datos...", reply_markup=ReplyKeyboardRemove())

            payload = {field_id: context.user_data.get(field_id, "") for field_id in CAMPOS_RESPALDO.keys()}

            # DIAGNÓSTICO: Esto imprimirá en tu consola los datos que se están enviando
            print(f"DEBUG: Enviando payload a Google: {payload}")

            try:
                # Enviamos el formulario primero
                response = requests.post(URL_RESPALDO, data=payload, timeout=15)

                if response.status_code == 200:
                    print("DEBUG: Google Forms aceptó los datos (200 OK)")
                    envio_exitoso = True
                    # Guardar horas localmente solo si el respaldo fue exitoso
                    fecha_id = [k for k, v in CAMPOS_RESPALDO.items() if v['tipo'] == 'fecha'][0]
                    horas_id = [k for k, v in CAMPOS_RESPALDO.items() if v['tipo'] == 'num_horas'][0]
                    
                    horas_decimal = convertir_duracion_a_decimal(context.user_data.get(horas_id, "00:00:00"))
                    guardar_horas(context.user_data.get(fecha_id), horas_decimal)

                    # --- BOTONES DE CONFIRMACIÓN PARA EL OFICIAL ---
                    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                    keyboard = [[
                        InlineKeyboardButton("✅ Enviar al Oficial", callback_data='enviar_oficial'),
                        InlineKeyboardButton("❌ Solo respaldo", callback_data='solo_respaldo')
                    ]]
                    await update.message.reply_text(
                        f"✅ Respaldo guardado ({horas_decimal:.2f}h).\n\n¿Deseas enviar ahora al Formulario Oficial?",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )

                else:
                    print(f"DEBUG: Google Forms rechazó los datos. Error: {response.status_code}")
                    print(f"DEBUG: Respuesta del servidor: {response.text[:200]}") # Ver los primeros 200 caracteres del error
                    envio_exitoso = False
            except Exception as e:
                print(f"DEBUG: Error de conexión con Google: {e}")
                envio_exitoso = False

            return ConversationHandler.END # Importante: no cerramos la conversación para esperar el botón

    except Exception as e:
        logger.error(f"Error: {e}")
        return ConversationHandler.END

async def ver_horas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    datos_semanal = obtener_resumen_semanal()
    datos_diario = obtener_resumen_diario()
    if not datos_semanal and not datos_diario:
        await update.message.reply_text("No hay horas registradas esta semana.")
        return

    resumen = "📊 *Resumen de Horas Semanal/Diaria*\n\n"

    total_semanal = 0
    resumen += "🗓 *Semana:*\n"
    for fecha, total in datos_semanal:
        # FILTRO: Solo agregar si la fecha tiene el formato AAAA-MM-DD (evita el "Yo")
        if len(str(fecha)) == 10 and str(fecha).count('-') == 2:
            resumen += f"📅 {fecha}: {total:.2f}h\n" # Usamos 'total', no 'total_semanal'
            total_semanal += total

    # Cálculo Meta Semanal
    meta_semanal = META_DIARIA * 5
    faltante_sem = meta_semanal - total_semanal
    resumen += f"\n━━━━━━━━━━━━━━\n🚀 *Total Semanal:* {total_semanal:.2f}h\n"
    resumen += f"⏳ *Faltan:* {max(0, faltante_sem):.2f}h para la meta (45h)\n"

    # --- SECCIÓN DIARIA ---
    resumen += "\n🗓 *Hoy:*\n"
    total_diario = 0
    for fecha, total in datos_diario:
        if len(str(fecha)) == 10 and str(fecha).count('-') == 2:
            resumen += f"📅 {fecha}: {total:.2f}h\n"
            total_diario += total

    meta_diaria = META_DIARIA
    faltante_dia = meta_diaria - total_diario
    resumen += f"\n━━━━━━━━━━━━━━\n🚀 *Total Diario:* {total_diario:.2f}h\n"
    resumen += f"⏳ *Faltan:* {max(0, faltante_dia):.2f}h para la meta (09h)"

    await update.message.reply_text(resumen, parse_mode='Markdown')

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Operación cancelada.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'enviar_oficial':
        # Mapeamos los valores del respaldo a los IDs del oficial
        payload_oficial = {}
        for i, (id_resp, _) in enumerate(CAMPOS_RESPALDO.items()):
            valor = context.user_data.get(id_resp)
            id_oficial = list(CAMPOS_OFICIAL.keys())[i]
            payload_oficial[id_oficial] = valor

        try:
            res = requests.post(URL_OFICIAL, data=payload_oficial, timeout=15)
            if res.status_code == 200:
                await query.edit_message_text("✅ ¡Perfecto! Datos enviados al Formulario Oficial.")
            else:
                await query.edit_message_text(f"⚠️ El oficial rechazó los datos (Error {res.status_code}).")
        except Exception as e:
            await query.edit_message_text("❌ Error de conexión con el oficial.")
    else:
        await query.edit_message_text("ℹ️ Registro guardado solo en el respaldo.")

def main():
    init_db()
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    from telegram.ext import CallbackQueryHandler
    app.add_handler(CallbackQueryHandler(handle_confirmation))
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={i: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_step)] for i in range(len(ORDEN_PREGUNTAS))},
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler('horas', ver_horas))
    print("🚀 Bot con Conversor de Tiempo Iniciado...")
    app.run_polling()

if __name__ == '__main__':
    main()