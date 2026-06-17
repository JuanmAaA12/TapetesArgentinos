from fastapi import FastAPI, Request, Form, HTTPException, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json
import os
import logging

app = FastAPI(title="TapetesApp - Proyecto Base Oficial")
handler = app # Enlace obligatorio requerido por Vercel

# =====================================================================
# 1. RUTEOS ABSOLUTOS SEGUROS
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
    ARCHIVO_STOCK = '/tmp/stock.json'
    LOG_FILE = '/tmp/app_testing.log'
    
    if not os.path.exists(ARCHIVO_USUARIOS):
        with open(ARCHIVO_USUARIOS, 'w', encoding='utf-8') as f:
            json.dump([
                {"email": "admin@tapetesapp.com", "password": "contraseña", "role": "administrador"},
                {"email": "operador@tapetesapp.com", "password": "contraseña", "role": "operador"},
                {"email": "juan@gmail.com", "password": "juanma", "role": "usuario_comun"}
            ], f, ensure_ascii=False, indent=4)
            
    if not os.path.exists(ARCHIVO_PEDIDOS):
        with open(ARCHIVO_PEDIDOS, 'w', encoding='utf-8') as f:
            json.dump([
                {
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
                }
            ], f, ensure_ascii=False, indent=4)
else:
    ARCHIVO_USUARIOS = 'usuarios.json'
    ARCHIVO_PEDIDOS = 'pedidos.json'
    ARCHIVO_STOCK = 'stock.json'
    LOG_FILE = 'app_testing.log'

# Configuración del logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# =====================================================================
# 2. FUNCIONES REUTILIZABLES DE PERSISTENCIA
# =====================================================================
def cargar_usuarios():
    try:
        with open(ARCHIVO_USUARIOS, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error al cargar usuarios: {str(e)}")
        return []

def guardar_usuarios(datos):
    try:
        with open(ARCHIVO_USUARIOS, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Error al guardar usuarios: {str(e)}")

def cargar_pedidos():
    try:
        with open(ARCHIVO_PEDIDOS, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Error al cargar pedidos: {str(e)}")
        return []

def guardar_pedidos(datos):
    try:
        with open(ARCHIVO_PEDIDOS, 'w', encoding='utf-8') as f:
            json.dump(datos, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logging.error(f"Error al guardar pedidos: {str(e)}")

def cargar_stock():
    if not os.path.exists(ARCHIVO_STOCK):
        default_stock = [
            {"id": 1, "material": "Lana de Oveja Premium", "precio_base": 25000, "stock": 120},
            {"id": 2, "material": "Algodón Orgánico", "precio_base": 18000, "stock": 85},
            {"id": 3, "material": "Sintético de Alta Densidad", "precio_base": 12000, "stock": 60}
        ]
        with open(ARCHIVO_STOCK, 'w', encoding='utf-8') as f:
            json.dump(default_stock, f, ensure_ascii=False, indent=4)
    with open(ARCHIVO_STOCK, 'r', encoding='utf-8') as f:
        return json.load(f)

def guardar_stock(datos):
    with open(ARCHIVO_STOCK, 'w', encoding='utf-8') as f:
        json.dump(datos, f, ensure_ascii=False, indent=4)

def verificar_sesion_rol(request: Request, roles_permitidos: list):
    rol = request.cookies.get("rol")
    if not rol:
        raise HTTPException(status_code=401, detail="No autenticado. Debe iniciar sesion.")
    if rol not in roles_permitidos:
        raise HTTPException(status_code=403, detail="Acceso denegado. Se requiere rol autorizado.")
    return rol

# =====================================================================
# 3. INTERFACES GRÁFICAS (RUTAS HTML ADAPTADAS A TUS PLANTILLAS)
# =====================================================================
@app.get("/", response_class=HTMLResponse)
async def pantalla_autenticacion(request: Request):
    logging.info("Se accedió a la pantalla de Autenticación inicial.")
    return templates.TemplateResponse(request=request, name="login.html", context={"error": None, "msg": None})

@app.post("/auth/login", response_class=HTMLResponse)
async def procesar_autenticacion(request: Request, email: str = Form(...), password: str = Form(...)):
    logging.info(f"Intento de login procesado para el correo: {email}")
    usuarios = cargar_usuarios()
    
    usuario_valido = None
    for u in usuarios:
        if u['email'] == email and u['password'] == password:
            usuario_valido = u
            break
            
    if usuario_valido:
        logging.info(f"Autenticación exitosa. Usuario: {email} | Rol: {usuario_valido['role']}")
        
        if usuario_valido['role'] in ['administrador', 'operador']:
            redireccion = RedirectResponse(url="/admin", status_code=303)
        else:
            redireccion = RedirectResponse(url="/pedido", status_code=303)
            
        redireccion.set_cookie(key="usuario", value=email)
        redireccion.set_cookie(key="rol", value=usuario_valido['role'])
        return redireccion
        
    logging.warning(f"Fallo de autenticación para el correo: {email}")
    return templates.TemplateResponse(request=request, name="login.html", context={"error": "Credenciales incorrectas o usuario inexistente.", "msg": None})

@app.post("/auth/register", response_class=HTMLResponse)
async def procesar_registro(request: Request, nombre: str = Form(...), email: str = Form(...), password: str = Form(...)):
    logging.info(f"Intento de registro para el correo: {email}")
    usuarios = cargar_usuarios()
    
    for u in usuarios:
        if u['email'] == email:
            return templates.TemplateResponse(request=request, name="login.html", context={"error": "El correo ya se encuentra registrado.", "msg": None})
            
    nuevo_usuario = {
        "email": email,
        "password": password,
        "role": "usuario_comun"
    }
    usuarios.append(nuevo_usuario)
    guardar_usuarios(usuarios)
    
    logging.info(f"Nuevo usuario común registrado exitosamente: {email}")
    return templates.TemplateResponse(request=request, name="login.html", context={"error": None, "msg": "¡Registro exitoso! Ya podés iniciar sesión arriba."})

@app.get("/pedido", response_class=HTMLResponse)
async def formulario_pedido(request: Request):
    usuario_sesion = request.cookies.get("usuario")
    if not usuario_sesion:
        return RedirectResponse(url="/", status_code=303)
        
    logging.info(f"El usuario {usuario_sesion} ingresó al panel de personalización de tapetes.")
    pedidos_totales = cargar_pedidos()
    # Filtrar para que el usuario común solo vea sus propios pedidos históricos en la tabla inferior
    mis_pedidos = [p for p in pedidos_totales if p.get('email') == usuario_sesion]
    
    return templates.TemplateResponse(request=request, name="pedido.html", context={"usuario": usuario_sesion, "pedidos": mis_pedidos, "msg": None})

@app.post("/orders", response_class=HTMLResponse)
async def registrar_nuevo_pedido(
    request: Request,
    cliente: str = Form(...),
    email: str = Form(...),
    material: str = Form(...),
    medidas: str = Form(None)  # Cambiado a None (opcional) para evitar el error de FastAPI si el HTML falla
):
    # Si por algún problema del HTML llega vacío o no llega, le asignamos una medida por defecto segura
    if not medidas or medidas.strip() == "":
        medidas = "2.0m x 1.5m"

    pedidos_sistema = cargar_pedidos()
    nuevo_id = max([p['id'] for p in pedidos_sistema], default=0) + 1
    
    precios_materiales = {
        "Lana de Oveja Premium": 25000.0,
        "Algodón Orgánico": 18000.0,
        "Sintético de Alta Densidad": 12000.0
    }
    
    precio_m2 = precios_materiales.get(material, 15000.0)
    
    try:
        dimensiones = medidas.lower().replace("m", "").split("x")
        ancho = float(dimensiones[0].strip())
        largo = float(dimensiones[1].strip())
        m2 = ancho * largo
    except Exception as e:
        logging.error(f"Error procesando medidas '{medidas}'. Fallback de 2m2 aplicado. Detalle: {str(e)}")
        m2 = 2.0
        
    precio_calculado = m2 * precio_m2
    anticipo = precio_calculado * 0.50
    
    pedido_nuevo = {
        "id": nuevo_id,
        "cliente": cliente,
        "email": email,
        "material": material,
        "medidas": medidas,
        "precio_total": precio_calculado,
        "anticipo_requerido": anticipo,
        "estado": "Cotizacion Generada (Pendiente)",
        "boceto_aprobado": False,
        "saldo_pendiente": precio_calculado,
        "fecha_entrega": "Pendiente de confirmación",
        "numero_guia": "N/A"
    }
    
    pedidos_sistema.append(pedido_nuevo)
    guardar_pedidos(pedidos_sistema)
    
    logging.info(f"Nueva solicitud de tapete registrada exitosamente. Pedido ID: #{nuevo_id}")
    
    # Recargar la vista con los pedidos actualizados de este usuario
    mis_pedidos = [p for p in pedidos_sistema if p.get('email') == email]
    return templates.TemplateResponse(request=request, name="pedido.html", context={
        "msg": f"¡Pedido #{nuevo_id} enviado con éxito! Tu cotización fue registrada.", 
        "usuario": email,
        "pedidos": mis_pedidos
    })

@app.get("/admin", response_class=HTMLResponse)
async def panel_administracion(request: Request):
    usuario_sesion = request.cookies.get("usuario")
    rol_sesion = request.cookies.get("rol")
    
    if not usuario_sesion or rol_sesion not in ['administrador', 'operador']:
        logging.warning(f"Acceso no autorizado bloqueado a la ruta /admin.")
        return RedirectResponse(url="/", status_code=303)
        
    pedidos_sistema = cargar_pedidos()
    logging.info(f"El {rol_sesion} {usuario_sesion} accedió al Panel de Control de Pedidos.")
    return templates.TemplateResponse(request=request, name="admin.html", context={"pedidos": pedidos_sistema, "usuario": usuario_sesion, "role": rol_sesion})

@app.post("/orders/{pedido_id}/advance")
async def avanzar_estado_pedido(pedido_id: int):
    pedidos_sistema = cargar_pedidos()
    flujo_estados = [
        "Cotizacion Generada (Pendiente)", 
        "Anticipo Pagado", 
        "Diseño en Proceso", 
        "Boceto Enviado", 
        "Boceto Aprobado", 
        "En Producción", 
        "Listo para Despacho", 
        "Despachado (Envío Finalizado)"
    ]
    
    for p in pedidos_sistema:
        if p['id'] == pedido_id:
            estado_actual = p.get('estado', "Cotizacion Generada (Pendiente)")
            if estado_actual in flujo_estados:
                indice = flujo_estados.index(estado_actual)
                if indice < len(flujo_estados) - 1:
                    p['estado'] = flujo_estados[indice + 1]
                    if p['estado'] == "Despachado (Envío Finalizado)" or p['estado'] == "Listo para Despacho":
                        p['saldo_pendiente'] = 0.0
                    guardar_pedidos(pedidos_sistema)
                    logging.info(f"Pedido #{pedido_id} actualizado al estado: {p['estado']}")
            break
            
    return RedirectResponse(url="/admin", status_code=303)

@app.get("/logout")
async def cerrar_sesion():
    logging.info("Sesión finalizada por el usuario.")
    redireccion = RedirectResponse(url="/", status_code=303)
    redireccion.delete_cookie("usuario")
    redireccion.delete_cookie("rol")
    return redireccion

# =====================================================================
# 4. ENDPOINTS DE API ADICIONALES (Para Postman / Testing)
# =====================================================================
@app.get("/stock")
async def obtener_stock(request: Request):
    verificar_sesion_rol(request, ["administrador", "operador"])
    return cargar_stock()

@app.patch("/stock/{material_id}")
async def actualizar_stock(material_id: int, request: Request):
    verificar_sesion_rol(request, ["administrador", "operador"])
    
    try:
        body = await request.json()
        quantity = body.get("quantity")
    except:
        raise HTTPException(status_code=422, detail="Cuerpo de solicitud inválido.")
        
    if quantity is None:
        raise HTTPException(status_code=422, detail="El campo 'quantity' es requerido.")
    if quantity < 0:
        raise HTTPException(status_code=422, detail="El stock no puede ser negativo.")
        
    stocks = cargar_stock()
    material_encontrado = None
    for s in stocks:
        if s["id"] == material_id:
            material_encontrado = s
            break
            
    if not material_encontrado:
        raise HTTPException(status_code=404, detail="Material no encontrado.")
        
    material_encontrado["stock"] = quantity
    guardar_stock(stocks)
    
    return {"id": material_encontrado["id"], "material": material_encontrado["material"], "stock": material_encontrado["stock"], "mensaje": "Stock actualizado."}

@app.get("/reports/profitability")
async def obtener_rentabilidad(request: Request, mes: str = None):
    verificar_sesion_rol(request, ["administrador"])
    
    pedidos = cargar_pedidos()
    pedidos_confirmados = [p for p in pedidos if "Pendiente" not in p.get("estado", "")]
    
    reportes_mes = {}
    for p in pedidos_confirmados:
        mes_pedido = "2026-06" 
        if mes and mes != mes_pedido:
            continue
            
        if mes_pedido not in reportes_mes:
            reportes_mes[mes_pedido] = {
                "mes": mes_pedido,
                "ingresos_totales": 0.0,
                "anticipos_cobrados": 0.0,
                "saldo_pendiente": 0.0,
                "pedidos_count": 0,
                "desglose_dict": {}
            }
            
        rep = reportes_mes[mes_pedido]
        rep["pedidos_count"] += 1
        precio_total = float(p.get("precio_total", 0))
        rep["ingresos_totales"] += precio_total
        rep["anticipos_cobrados"] += float(p.get("anticipo_requerido", 0))
        rep["saldo_pendiente"] += float(p.get("saldo_pendiente", 0))
            
        mat = p.get("material", "Desconocido")
        if mat not in rep["desglose_dict"]:
            rep["desglose_dict"][mat] = {"material": mat, "cantidad": 0, "ingreso": 0.0}
        rep["desglose_dict"][mat]["cantidad"] += 1
        rep["desglose_dict"][mat]["ingreso"] += precio_total

    resultado = []
    for m, datos in reportes_mes.items():
        datos["desglose"] = list(datos["desglose_dict"].values())
        del datos["desglose_dict"]
        resultado.append(datos)
        
    if mes and not resultado:
        return {"mes": mes, "ingresos_totales": 0, "anticipos_cobrados": 0, "saldo_pendiente": 0, "pedidos_count": 0, "desglose": []}
        
    return resultado
