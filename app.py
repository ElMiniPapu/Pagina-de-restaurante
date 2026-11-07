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
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            precio REAL NOT NULL,
            imagen TEXT NOT NULL,
            categoria TEXT NOT NULL
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            total REAL NOT NULL
        )
    ''')

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

    conn.commit()
    conn.close()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/invitado")
def invitado():
    session['usuario'] = "Invitado"
    session['es_invitado'] = True
    return redirect(url_for('menu'))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT nombre, email, password FROM usuarios WHERE email = ? AND password = ?", (email, password))
        usuario = cursor.fetchone()
        conn.close()

        if usuario:
            session['usuario'] = usuario[0]
            session['email'] = usuario[1]
            session['password'] = usuario[2]
            session['es_invitado'] = False
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
            cursor.execute("INSERT INTO usuarios (nombre, email, password) VALUES (?, ?, ?)", (nombre, email, password))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            flash("El correo electrónico ya está registrado.")
            return redirect(url_for("registro"))

        conn.close()

        session['usuario'] = nombre
        session['email'] = email
        session['password'] = password
        session['es_invitado'] = False

        return redirect(url_for("menu"))

    return render_template("registro.html")

# --- RUTA DE CERRAR SESIÓN ---
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route("/menu")
def menu():
    if 'usuario' not in session:
        session['usuario'] = "Invitado"
    return render_template("menu.html")

@app.route("/categoria/<nombre_categoria>")
def ver_categoria(nombre_categoria):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM productos WHERE categoria = ?", (nombre_categoria.lower(),))
    productos = cursor.fetchall()
    conn.close()

    titulo_formateado = nombre_categoria.upper()
    return render_template("categoria.html", productos=productos, titulo=titulo_formateado)

@app.route("/pedidos")
def pedidos():
    if 'usuario' not in session:
        session['usuario'] = "Invitado"
    return render_template("pedidos.html")

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

    total = sum(item['precio'] * item.get('cantidad', 1) for item in carrito)
    fecha_hora = datetime.now().strftime("%d/%m/%Y - %H:%M hs")

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO pedidos (fecha, total) VALUES (?, ?)", (fecha_hora, total))
    pedido_id = cursor.lastrowid
    conn.commit()
    conn.close()

    numero_pedido = f"{pedido_id:03d}"

    return render_template(
        "ticket.html",
        tienda="IL DUCALE",
        fecha_hora=fecha_hora,
        productos=carrito,
        total=total,
        numero_pedido=numero_pedido
    )

if __name__ == "__main__":
    init_db()
    app.run(debug=True)