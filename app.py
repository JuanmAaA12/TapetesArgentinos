from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json
import os
import logging

app = FastAPI(title="TapetesApp - Proyecto Base Oficial")
handler = app # Enlace obligatorio requerido por Vercel

# =====================================================================
# 1. RUTEOS ABSOLUTOS SEGUROS (Evita errores 404 y pantallas sin CSS)
# =====================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Persistencia inteligente (Usa /tmp solo si detecta que está corriendo en Vercel)
if os.environ.get("VERCEL"):
    ARCHIVO_USUARIOS = '/tmp/usuarios.json'
    ARCHIVO_PEDIDOS = '/tmp/pedidos.json'
    LOG_FILE = '/tmp/app_testing.log'
    
    if not os.path.exists(ARCHIVO_USUARIOS):
        with open(ARCHIVO_USUARIOS, 'w', encoding='utf-8') as f:
            json.dump([
                {"email": "admin@tapetesapp.com", "password": "contraseña", "role": "administrador"},
                {"email": "operador@tapetesapp.com", "password": "contraseña", "role": "operador"},
                {"email": "juan@gmail.com", "password": "juanma", "role": "usuario_comun"}
            ], f, indent=4)
            
    if not os.path.exists(ARCHIVO_PEDIDOS):
        with open(ARCHIVO_PEDIDOS, 'w', encoding='utf-8') as f:
            json.dump([{
                "id": 1,
                "cliente": "Juan Manuel Veiga Lucien",
                "email": "juan@gmail.com",
                "material": "Algodón Orgánico",
                "medidas": "1.5m x 2.0m",
                "precio_total": 27000.0,
                "anticipo_requerido": 13500.0,
                "estado": "Despachado (Envío Finalizado)",
                "boceto_aprobado": False,
                "saldo_pendiente": 0,
                "fecha_entrega": "En 15 días hábiles",
                "numero_guia": "AR-984723984-DH"
            }], f, indent=4)
else:
    # Rutas estándar locales para tu computadora
    ARCHIVO_USUARIOS = os.path.join(BASE_DIR, 'usuarios.json')
    ARCHIVO_PEDIDOS = os.path.join(BASE_DIR, 'pedidos.json')
    LOG_FILE = os.path.join(BASE_DIR, "app_testing.log")

# =====================================================================
# 2. SISTEMA DE LOGS CON ENCODING UTF-8 (Evita crasheos por tildes)
# =====================================================================
for u_handler in logging.root.handlers[:]:
    logging.root.removeHandler(u_handler)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8', mode='a'),
        logging.StreamHandler()
    ]
)

PRECIOS_MATERIAL = {
    "Lana de Oveja Premium": 25000,
    "Algodón Orgánico": 18000,
    "Sintético de Alta Densidad": 12000
}

# =====================================================================
# 3. FUNCIONES DE PERSISTENCIA (Lectura y Escritura de datos)
# =====================================================================
def cargar_usuarios():
    if not os.path.exists(ARCHIVO_USUARIOS):
        return []
    try:
        with open(ARCHIVO_USUARIOS, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

def guardar_usuarios(usuarios):
    try:
        with open(ARCHIVO_USUARIOS, 'w', encoding='utf-8') as f:
            json.dump(usuarios, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Error al guardar usuarios: {str(e)}")

def cargar_pedidos():
    if not os.path.exists(ARCHIVO_PEDIDOS):
        return []
    try:
        with open(ARCHIVO_PEDIDOS, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

def guardar_pedidos(pedidos):
    try:
        with open(ARCHIVO_PEDIDOS, 'w', encoding='utf-8') as f:
            json.dump(pedidos, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logging.error(f"Error al guardar pedidos: {str(e)}")

# =====================================================================
# 4. ENDPOINTS CONTROLADORES (Vistas e Inicios de Sesión)
# =====================================================================
@app.get("/", response_class=HTMLResponse)
async def vista_login(request: Request):
    logging.info("Se accedió a la pantalla de Autenticación inicial.")
    return templates.TemplateResponse(request, "login.html", context={"error": None, "msg": None})

@app.post("/auth/login")
async def procesar_login(request: Request, email: str = Form(...), password: str = Form(...)):
    logging.info(f"Intento de login procesado para el correo: {email}")
    usuarios_sistema = cargar_usuarios()
    
    usuario_valido = None
    for u in usuarios_sistema:
        if u['email'] == email and u['password'] == password:
            usuario_valido = u
            break
            
    if usuario_valido:
        rol = usuario_valido.get('role', 'usuario_comun')
        logging.info(f"Autenticación exitosa. Usuario: {email} | Rol: {rol}")
        if rol in ["administrador", "operador"]:
            return RedirectResponse(url="/admin", status_code=303)
        return RedirectResponse(url="/pedido", status_code=303)
    
    logging.warning(f"Fallo de credenciales para el usuario: {email}")
    return templates.TemplateResponse(request, "login.html", context={"error": "Credenciales inválidas de acceso.", "msg": None})

@app.post("/auth/register")
async def procesar_registro(request: Request, nombre: str = Form(...), email: str = Form(...), password: str = Form(...)):
    usuarios_sistema = cargar_usuarios()
    
    for u in usuarios_sistema:
        if u['email'] == email:
            return templates.TemplateResponse(request, "login.html", context={"error": "El correo ya está registrado.", "msg": None})
            
    nuevo_usuario = {"nombre": nombre, "email": email, "password": password, "role": "usuario_comun"}
    usuarios_sistema.append(nuevo_usuario)
    guardar_usuarios(usuarios_sistema)
    
    logging.info(f"Registro exitoso del usuario: {email}")
    return templates.TemplateResponse(request, "login.html", context={"error": None, "msg": "Registro completado con éxito."})

@app.get("/pedido", response_class=HTMLResponse)
async def vista_pedido(request: Request):
    logging.info("Acceso concedido al panel de diseño de tapetes.")
    pedidos_sistema = cargar_pedidos()
    return templates.TemplateResponse(request, "pedido.html", context={"pedidos": pedidos_sistema})

@app.post("/orders")
async def registrar_pedido(request: Request, cliente: str = Form(...), email: str = Form(...), material: str = Form(...), ancho: float = Form(...), largo: float = Form(...)):
    pedidos_sistema = cargar_pedidos()
    
    precio_por_m2 = PRECIOS_MATERIAL.get(material, 12000)
    metros_cuadrados = ancho * largo
    precio_calculado = metros_cuadrados * precio_por_m2
    anticipo = precio_calculado * 0.5
    
    nuevo_pedido = {
        "id": len(pedidos_sistema) + 1,
        "cliente": cliente,
        "email": email,
        "material": material,
        "medidas": f"{ancho}m x {largo}m",
        "precio_total": float(precio_calculado),
        "anticipo_requerido": float(anticipo),
        "estado": "Pendiente de Cotización",
        "boceto_aprobado": False,
        "saldo_pendiente": float(anticipo)
    }
    
    pedidos_sistema.append(nuevo_pedido)
    guardar_pedidos(pedidos_sistema)
    logging.info(f"Pedido #{nuevo_pedido['id']} creado con éxito para el cliente {email}")
    return RedirectResponse(url="/pedido", status_code=303)

@app.get("/admin", response_class=HTMLResponse)
async def vista_admin(request: Request):
    pedidos_sistema = cargar_pedidos()
    return templates.TemplateResponse(request, "admin.html", context={"pedidos": pedidos_sistema})

@app.post("/orders/{pedido_id}/advance")
async def avanzar_estado_pedido(pedido_id: int):
    pedidos_sistema = cargar_pedidos()
    flujo_estados = ["Pendiente de Cotización", "En Production", "Listo para Despacho", "Despachado (Envío Finalizado)"]
    
    for p in pedidos_sistema:
        if p['id'] == pedido_id:
            estado_actual = p.get('estado', "Pendiente de Cotización")
            if estado_actual in flujo_estados:
                indice = flujo_estados.index(estado_actual)
                if indice < len(flujo_estados) - 1:
                    p['estado'] = flujo_estados[indice + 1]
                    if p['estado'] == "Listo para Despacho":
                        p['saldo_pendiente'] = 0.0
                    guardar_pedidos(pedidos_sistema)
                    logging.info(f"Pedido #{pedido_id} actualizado al estado: {p['estado']}")
            break
            
    return RedirectResponse(url="/admin", status_code=303)

# =====================================================================
# 5. ENDPOINTS DE API (Sprint 2 - Postman)
# =====================================================================
@app.get("/api/stock")
async def obtener_stock():
    return {
        "Lana de Oveja Premium": {"disponible_m2": 45.5, "estado": "Stock Alto"},
        "Algodón Orgánico": {"disponible_m2": 12.0, "estado": "Stock Crítico (Reordenar)"},
        "Sintético de Alta Densidad": {"disponible_m2": 88.0, "estado": "Stock Alto"}
    }

@app.get("/api/rentabilidad")
async def calcular_rentabilidad():
    pedidos_sistema = cargar_pedidos()
    ingresos_totales = sum(p.get('precio_total', 0) for p in pedidos_sistema)
    costos_estimados = ingresos_totales * 0.40
    ganancia_neta = ingresos_totales - costos_estimados
    
    return {
        "mes_evaluado": "Junio 2026",
        "ingresos_brutos_ars": round(ingresos_totales, 2),
        "costos_operativos_ars": round(costos_estimados, 2),
        "ganancia_neta_ars": round(ganancia_neta, 2)
    }