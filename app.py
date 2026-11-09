import sqlite3
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = "clave_secreta_restaurante"
DB_NAME = "database.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Tabla de Usuarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            rol TEXT NOT NULL DEFAULT 'cliente'
        )
    ''')
    
    try:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN rol TEXT NOT NULL DEFAULT 'cliente'")
    except sqlite3.OperationalError:
        pass

    # Tabla de Productos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            precio REAL NOT NULL,
            imagen TEXT NOT NULL,
            categoria TEXT NOT NULL
        )
    ''')

    # Tabla de Pedidos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT,
            fecha TEXT NOT NULL,
            total REAL NOT NULL,
            detalles TEXT,
            estado TEXT NOT NULL DEFAULT 'Pendiente',
            categorias_listas TEXT DEFAULT '[]'
        )
    ''')

    try:
        cursor.execute("ALTER TABLE pedidos ADD COLUMN categorias_listas TEXT DEFAULT '[]'")
    except sqlite3.OperationalError:
        pass

    # =========================================================================
    # LIMPIEZA AUTOMÁTICA DE PEDIDOS CADA VEZ QUE SE INICIA EL SERVIDOR
    # =========================================================================
    cursor.execute("DELETE FROM pedidos")
    cursor.execute("DELETE FROM sqlite_sequence WHERE name='pedidos'")

    # Cargar productos iniciales si la tabla está vacía
    cursor.execute("SELECT COUNT(*) FROM productos")
    if cursor.fetchone()[0] == 0:
        productos_iniciales = [
            ('Pizzas de mozzarella', 15000, 'pizza_mozzarella.jpg', 'comidas'),
            ('Hamburguesa completa', 20000, 'hamburguesa.jpg', 'comidas'),
            ('Papas fritas clásicas', 30000, 'papas_clasicas.jpg', 'comidas'),
            ('Papas fritas con cheddar', 30000, 'papas_cheddar.jpg', 'comidas'),
            ('Tiramisú', 15000, 'tiramisu.jpg', 'postres'),
            ('Cheesecake de frutos rojos', 20000, 'cheesecake.jpg', 'postres'),
            ('copa helada', 20000, 'copa_helada.jpg', 'postres'),
            ('rubia clásica', 15000, 'cerveza_rubia.jpg', 'bebidas'),
            ('IPA', 20000, 'cerveza_ipa.jpg', 'bebidas'),
            ('Negra', 20000, 'cerveza_negra.jpg', 'bebidas'),
            ('Roja', 30000, 'cerveza_roja.jpg', 'bebidas'),
            ('Limonadas', 5000, 'limonada.jpg', 'bebidas'),
            ('Pepsi', 10000, 'pepsi.jpg', 'bebidas'),
            ('Sprite', 10000, 'sprite.jpg', 'bebidas'),
            ('Agua sin gas', 2500, 'agua_sin_gas.jpg', 'bebidas')
        ]
        cursor.executemany("INSERT INTO productos (nombre, precio, imagen, categoria) VALUES (?, ?, ?, ?)", productos_iniciales)

    # Insertar usuario CHEF si no existe
    cursor.execute("SELECT COUNT(*) FROM usuarios WHERE rol = 'chef'")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO usuarios (nombre, email, password, rol) VALUES (?, ?, ?, 'chef')",
            ("Chef Principal", "chef@ilducale.com", "chef123")
        )

    conn.commit()
    conn.close()

def obtener_categoria_producto(nombre_producto, conn):
    cursor = conn.cursor()
    cursor.execute("SELECT categoria FROM productos WHERE LOWER(nombre) = LOWER(?)", (nombre_producto,))
    res = cursor.fetchone()
    if res:
        return res[0].upper()
    
    nombre_low = nombre_producto.lower()
    if any(b in nombre_low for b in ['ipa', 'cerveza', 'pepsi', 'sprite', 'limonada', 'agua', 'rubia', 'negra', 'roja']):
        return 'BEBIDAS'
    elif any(p in nombre_low for p in ['tiramisú', 'tiramisu', 'cheesecake', 'copa helada', 'helada']):
        return 'POSTRES'
    return 'COMIDAS'

# --- RUTAS DE USUARIO ---

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/invitado")
def invitado():
    session['usuario'] = "Invitado"
    session['es_invitado'] = True
    session['rol'] = 'cliente'
    return redirect(url_for('menu'))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT nombre, email, password, rol FROM usuarios WHERE email = ? AND password = ?", (email, password))
        usuario = cursor.fetchone()
        conn.close()

        if usuario:
            session['usuario'] = usuario[0]
            session['email'] = usuario[1]
            session['password'] = usuario[2]
            session['rol'] = usuario[3]
            session['es_invitado'] = False

            if usuario[3] == 'chef':
                return redirect(url_for('pedidos'))
            
            return redirect(url_for('menu'))
        else:
            flash("Correo o contraseña incorrectos.")
            return redirect(url_for('login'))

    return render_template("login.html")

@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form.get("nombre")
        email = request.form.get("email")
        password = request.form.get("password")

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO usuarios (nombre, email, password, rol) VALUES (?, ?, ?, 'cliente')", (nombre, email, password))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            flash("El correo electrónico ya está registrado.")
            return redirect(url_for("registro"))

        conn.close()
        session['usuario'] = nombre
        session['email'] = email
        session['password'] = password
        session['rol'] = 'cliente'
        session['es_invitado'] = False

        return redirect(url_for("menu"))

    return render_template("registro.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route("/menu")
def menu():
    if 'usuario' not in session:
        session['usuario'] = "Invitado"
        session['rol'] = 'cliente'
    return render_template("menu.html")

@app.route("/categoria/<nombre_categoria>")
def ver_categoria(nombre_categoria):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM productos WHERE categoria = ?", (nombre_categoria.lower(),))
    productos = cursor.fetchall()
    conn.close()
    return render_template("categoria.html", productos=productos, titulo=nombre_categoria.upper())

@app.route("/tu_pedidos")
def tu_pedidos():
    if 'usuario' not in session:
        session['usuario'] = "Invitado"
        session['rol'] = 'cliente'
    return render_template("tu_pedidos.html")

@app.route("/nosotros")
def nosotros():
    return render_template("nosotros.html")

@app.route("/perfil")
def perfil():
    return render_template("perfil.html")

@app.route("/pedir_a_cuenta", methods=["GET", "POST"])
def pedir_a_cuenta():
    if request.method == "POST":
        cart_raw = request.form.get("cart_data", "[]")
        try:
            carrito = json.loads(cart_raw)
        except Exception:
            carrito = []
    else:
        carrito = session.get('carrito', [])

    if not carrito:
        return redirect(url_for('menu'))

    with sqlite3.connect(DB_NAME) as conn:
        for item in carrito:
            if 'categoria' not in item or not item['categoria']:
                item['categoria'] = obtener_categoria_producto(item.get('nombre', ''), conn).lower()

        total = sum(item['precio'] * item.get('cantidad', 1) for item in carrito)
        fecha_hora = datetime.now().strftime("%d/%m/%Y - %H:%M hs")
        cliente_nombre = session.get('usuario') or "Invitado"

        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO pedidos (cliente, fecha, total, detalles, estado, categorias_listas) VALUES (?, ?, ?, ?, 'Pendiente', '[]')",
            (cliente_nombre, fecha_hora, total, json.dumps(carrito))
        )
        pedido_id = cursor.lastrowid
        conn.commit()

    numero_pedido = f"{pedido_id:03d}"

    return render_template(
        "ticket.html",
        tienda="IL DUCALE",
        fecha_hora=fecha_hora,
        productos=carrito,
        total=total,
        numero_pedido=numero_pedido
    )

# --- RUTAS CHEF ---

@app.route("/pedidos")
def pedidos():
    if session.get('rol') != 'chef':
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, cliente, fecha, detalles, estado FROM pedidos ORDER BY id ASC")
    pedidos_db = cursor.fetchall()
    conn.close()

    pedidos_lista = []
    for p in pedidos_db:
        hora = p[2].split(" - ")[1].replace(" hs", "") if " - " in p[2] else p[2]
        pedidos_lista.append({
            'numero': f"{p[0]:03d}",
            'id_real': p[0],
            'cliente': p[1],
            'hora': hora,
            'detalles': json.loads(p[3]) if p[3] else [],
            'estado': p[4]
        })

    return render_template("pedidos.html", pedidos=pedidos_lista)

@app.route("/menu_chef")
def menu_chef():
    if session.get('rol') != 'chef':
        return redirect(url_for('login'))
    return render_template("menu_chef.html")

@app.route("/categoria_chef/<nombre_categoria>")
def ver_categoria_chef(nombre_categoria):
    if session.get('rol') != 'chef':
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM productos WHERE categoria = ?", (nombre_categoria.lower(),))
    productos = cursor.fetchall()
    conn.close()

    return render_template("categoria_chef.html", productos=productos, titulo=nombre_categoria.upper())

@app.route("/pedido_detalle/<int:pedido_id>")
def pedido_detalle(pedido_id):
    if session.get('rol') != 'chef':
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, cliente, fecha, detalles, estado, categorias_listas FROM pedidos WHERE id = ?", (pedido_id,))
    p = cursor.fetchone()

    if not p:
        conn.close()
        return redirect(url_for('pedidos'))

    hora = p[2].split(" - ")[1].replace(" hs", "") if " - " in p[2] else p[2]
    detalles = json.loads(p[3]) if p[3] else []
    cat_listas = json.loads(p[5]) if p[5] else []

    categorias_map = {
        'BEBIDAS': [],
        'COMIDAS': [],
        'POSTRES': []
    }

    for item in detalles:
        cat_real = obtener_categoria_producto(item.get('nombre', ''), conn)
        if cat_real in categorias_map:
            categorias_map[cat_real].append(item)
        else:
            categorias_map['COMIDAS'].append(item)

    conn.close()

    pedido = {
        'numero': f"{p[0]:03d}",
        'id_real': p[0],
        'cliente': p[1],
        'hora': hora,
        'estado': p[4],
        'categorias': categorias_map,
        'categorias_listas': cat_listas
    }

    return render_template("pedido_detalle.html", pedido=pedido)

@app.route("/pedido_categoria/<int:pedido_id>/<categoria_nombre>")
def pedido_categoria(pedido_id, categoria_nombre):
    if session.get('rol') != 'chef':
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, cliente, fecha, detalles, estado FROM pedidos WHERE id = ?", (pedido_id,))
    p = cursor.fetchone()

    if not p:
        conn.close()
        return redirect(url_for('pedidos'))

    hora = p[2].split(" - ")[1].replace(" hs", "") if " - " in p[2] else p[2]
    detalles_completos = json.loads(p[3]) if p[3] else []

    articulos_categoria = []
    for item in detalles_completos:
        cat_item = obtener_categoria_producto(item.get('nombre', ''), conn)
        if cat_item == categoria_nombre.upper():
            articulos_categoria.append(item)

    conn.close()

    pedido = {
        'numero': f"{p[0]:03d}",
        'id_real': p[0],
        'cliente': p[1],
        'hora': hora,
        'categoria_titulo': categoria_nombre.upper(),
        'articulos': articulos_categoria
    }

    return render_template("pedido_categoria.html", pedido=pedido)

# --- ACCIÓN MARCAR SOLO UNA CATEGORÍA COMO LISTA ---
@app.route("/marcar_categoria_lista/<int:pedido_id>/<categoria_nombre>", methods=["POST"])
def marcar_categoria_lista(pedido_id, categoria_nombre):
    if session.get('rol') != 'chef':
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT categorias_listas, detalles FROM pedidos WHERE id = ?", (pedido_id,))
    res = cursor.fetchone()

    if res:
        cat_listas = json.loads(res[0]) if res[0] else []
        cat_upper = categoria_nombre.upper()
        if cat_upper not in cat_listas:
            cat_listas.append(cat_upper)

        detalles = json.loads(res[1]) if res[1] else []
        cat_existentes = set()
        for item in detalles:
            cat_existentes.add(obtener_categoria_producto(item.get('nombre', ''), conn))

        # Si todas las categorías del pedido están listas, marcar pedido completo como 'Listo'
        nuevo_estado = 'Pendiente'
        if cat_existentes.issubset(set(cat_listas)):
            nuevo_estado = 'Listo'

        cursor.execute("UPDATE pedidos SET categorias_listas = ?, estado = ? WHERE id = ?", 
                       (json.dumps(cat_listas), nuevo_estado, pedido_id))
        conn.commit()

    conn.close()

    return redirect(url_for('pedido_detalle', pedido_id=pedido_id))

# --- ACCIÓN MARCAR TODO EL PEDIDO COMO LISTO ---
@app.route("/completar_pedido_chef/<int:pedido_id>", methods=["POST"])
def completar_pedido_chef(pedido_id):
    if session.get('rol') != 'chef':
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE pedidos SET estado = 'Listo' WHERE id = ?", (pedido_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('pedidos'))

# --- ACCIÓN MARCAR PEDIDO COMO ENTREGADO ---
@app.route("/entregar_pedido_chef/<int:pedido_id>", methods=["POST"])
def entregar_pedido_chef(pedido_id):
    if session.get('rol') != 'chef':
        return redirect(url_for('login'))

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE pedidos SET estado = 'Entregado' WHERE id = ?", (pedido_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('pedidos'))

@app.route("/actualizar_precio", methods=["POST"])
def actualizar_precio():
    if session.get('rol') != 'chef':
        return redirect(url_for('login'))

    producto_id = request.form.get("producto_id")
    nuevo_precio = request.form.get("nuevo_precio")

    if producto_id and nuevo_precio:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE productos SET precio = ? WHERE id = ?", (float(nuevo_precio), producto_id))
        conn.commit()
        conn.close()

    return redirect(request.referrer)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)