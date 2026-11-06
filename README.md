🤖 Bot de Automatización de Tareo (Telegram $\rightarrow$ Google Forms)

Este proyecto consiste en un Bot de Telegram diseñado para automatizar el registro de tiempos de atención en formularios de Google Forms. El bot actúa como un puente inteligente que guía al usuario a través de una serie de preguntas, valida los datos y los registra tanto en un formulario oficial como en uno de respaldo, manteniendo además una métrica de horas acumuladas en una base de datos local.

🚀 Funcionalidades Principales

- Interfaz Conversacional: Recolección de datos mediante un hilo de conversación guiado.
- Entrada Optimizada:
  - Botones de selección rápida para campos de lista.
  - Botón de "Hoy" para registro automático de fecha.
- Doble Registro (Espejo): Envío simultáneo a un formulario de respaldo (para validación) y a un formulario oficial.
- Flujo de Confirmación: El bot solo envía los datos al formulario oficial después de que el usuario confirme que el registro de respaldo fue exitoso.
- Contador de Productividad:
  - Conversión automática de formato HH:MM:SS a horas decimales.
  - Seguimiento de horas diarias y semanales mediante SQLite.
  - Cálculo automático de horas faltantes para alcanzar la meta diaria (9h) y semanal (45h).

---

🛠️ Arquitectura Técnica

- Lenguaje: Python 3.x
- Librerías Clave:
  - python-telegram-bot: Gestión de la API de Telegram y el flujo de conversación.
  - requests: Envío de datos mediante peticiones HTTP POST a Google Forms.
  - sqlite3: Almacenamiento local de métricas de tiempo.
  - python-dotenv: Gestión de variables sensibles (Tokens y URLs).

---

📈 Evolución del Proyecto (Bitácora de Desarrollo)

El proyecto evolucionó a través de varias etapas para garantizar la robustez y la precisión de los datos:

Fase 1: El Puente Básico

Se creó la primera versión capaz de enviar datos a Google Forms usando el endpoint /formResponse. Se implementó el ConversationHandler para hacer preguntas secuenciales.

Fase 2: Optimización de Experiencia de Usuario (UX)

Se detectó que escribir las opciones de las listas manualmente causaba errores (Error 400). Se implementaron:
- ReplyKeyboardMarkup: Botones interactivos para elegir opciones predefinidas.
- Botones Inteligentes: Implementación del botón "Hoy" para evitar errores de formato de fecha.

Fase 3: Sistema de Métricas (Time Tracking)

Se integró una base de datos SQLite para transformar el bot de un simple "enviador de datos" a una herramienta de gestión de tiempo:
- Implementación de un conversor de tiempo (HH:MM:SS $\rightarrow$ Decimal).
- Creación del comando /horas para visualizar la productividad semanal y diaria.

Fase 4: Estrategia de Seguridad y Validación

Para evitar errores en el formulario oficial (al cual no se tiene acceso al panel de control), se implementó la Estrategia de Espejo:
- Formulario de Respaldo: Un formulario propio donde se puede verificar que el dato entró correctamente.
- Confirmación Activa: El bot envía primero al respaldo y espera la confirmación del usuario mediante un CallbackQueryHandler (botones inline) antes de disparar los datos al formulario oficial.

Fase 5: Profesionalización del Entorno

Se aplicaron estándares de desarrollo de software:
- Entorno Virtual (.venv): Para aislamiento de dependencias.
- Variables de Entorno (.env): Para proteger el Token de Telegram y las URLs privadas.
- Estructura de Proyecto: Organización de carpetas para facilitar el despliegue en servidores.

---

📂 Estructura del Proyecto

Proyecto Tareo/
├── .venv/                # Entorno virtual de Python
├── .env                  # Variables sensibles (TOKEN, URLs)
├── horas_trabajo.db      # Base de datos de horas acumuladas
├── bot_formulario.py      # Lógica principal del Bot
├── requirements.txt      # Dependencias del proyecto
└── README.md             # Documentación del proyecto

⚙️ Configuración Rápida

1. Instalar dependencias:
pip install -r requirements.txt
2. Configurar .env:
   Añadir TELEGRAM_TOKEN, URL_RESPALDO y URL_OFICIAL.
3. Ejecutar:
python bot_formulario.py

📋 Comandos del Bot

- /start: Inicia el proceso de registro de un nuevo servicio.
- /horas: Muestra el resumen de horas trabajadas y el faltante para la meta.
- /cancel: Aborta el registro actual.