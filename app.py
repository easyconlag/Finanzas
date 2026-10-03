import sqlite3
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, simpledialog
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from tkcalendar import Calendar

# ==========================================
# 1. BASE DE DATOS Y LÓGICA
# ==========================================
def conectar():
    return sqlite3.connect("finanzas.db")

def crear_tablas():
    conexion = conectar()
    cursor = conexion.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transacciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT, monto REAL, categoria TEXT, descripcion TEXT,
            estado TEXT, fecha_registro DATE DEFAULT CURRENT_DATE, fecha_limite DATE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS abonos_deudas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deuda_id INTEGER,
            monto REAL,
            fecha DATE DEFAULT CURRENT_DATE,
            descripcion TEXT,
            FOREIGN KEY(deuda_id) REFERENCES transacciones(id) ON DELETE CASCADE
        )
    ''')

    cursor.execute('CREATE TABLE IF NOT EXISTS categorias (nombre TEXT PRIMARY KEY)')
    cursor.execute('CREATE TABLE IF NOT EXISTS tipos (nombre TEXT PRIMARY KEY)')
    
    cursor.execute('SELECT COUNT(*) FROM categorias')
    if cursor.fetchone()[0] == 0:
        for cat in ['Universidad', 'Moto', 'Catalina', 'General', 'Salario']:
            cursor.execute('INSERT INTO categorias (nombre) VALUES (?)', (cat,))
            
    cursor.execute('SELECT COUNT(*) FROM tipos')
    if cursor.fetchone()[0] == 0:
        for tipo in ['Ingreso', 'Gasto', 'Deuda', 'Gasto Futuro']:
            cursor.execute('INSERT INTO tipos (nombre) VALUES (?)', (tipo,))
    conexion.commit()
    conexion.close()

def obtener_lista(tabla):
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute(f'SELECT nombre FROM {tabla} ORDER BY nombre')
    resultados = [fila[0] for fila in cursor.fetchall()]
    conexion.close()
    return resultados

def registrar_movimiento(tipo, monto, categoria, descripcion, estado, fecha_limite):
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute('''
        INSERT INTO transacciones (tipo, monto, categoria, descripcion, estado, fecha_registro, fecha_limite)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (tipo, monto, categoria, descripcion, estado, datetime.now().strftime("%Y-%m-%d"), fecha_limite))
    conexion.commit()
    conexion.close()

def actualizar_movimiento(id_transaccion, tipo, monto, categoria, descripcion, estado, fecha_limite):
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute('''
        UPDATE transacciones SET tipo = ?, monto = ?, categoria = ?, descripcion = ?, estado = ?, fecha_limite = ? WHERE id = ?
    ''', (tipo, monto, categoria, descripcion, estado, fecha_limite, id_transaccion))
    conexion.commit()
    conexion.close()

def eliminar_movimiento(id_transaccion):
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("DELETE FROM transacciones WHERE id = ?", (id_transaccion,))
    cursor.execute("DELETE FROM abonos_deudas WHERE deuda_id = ?", (id_transaccion,))
    conexion.commit()
    conexion.close()

def marcar_como_completado(id_transaccion):
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("UPDATE transacciones SET estado = 'Completado' WHERE id = ?", (id_transaccion,))
    conexion.commit()
    conexion.close()

def obtener_meses_registrados():
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute("SELECT DISTINCT strftime('%Y-%m', fecha_registro) FROM transacciones ORDER BY 1 DESC")
    meses = [fila[0] for fila in cursor.fetchall() if fila[0]]
    conexion.close()
    return ["Todos los meses"] + meses

# ==========================================
# 2. INTERFAZ VISUAL
# ==========================================
def iniciar_interfaz():
    ventana = tb.Window(themename="darkly")
    ventana.title("Control Financiero Pro")
    ventana.state('zoomed') 
    
    main_frame = tb.Frame(ventana, padding=20)
    main_frame.pack(fill=BOTH, expand=YES)

    # --- TOP: TÍTULO Y FILTRO ---
    header_frame = tb.Frame(main_frame)
    header_frame.pack(fill=X, pady=(0, 20))
    
    tb.Label(header_frame, text="📊 Panel de Finanzas", font=("Helvetica", 24, "bold")).pack(side=LEFT)
    
    filtro_frame = tb.Frame(header_frame)
    filtro_frame.pack(side=RIGHT)
    tb.Label(filtro_frame, text="📅 Mes:", font=("Helvetica", 12)).pack(side=LEFT, padx=5)
    combo_meses = tb.Combobox(filtro_frame, state="readonly", width=15, font=("Helvetica", 11))
    combo_meses.pack(side=LEFT)

    # --- MÉTRICAS EN TARJETAS (6 TARJETAS) ---
    metricas_frame = tb.Frame(main_frame)
    metricas_frame.pack(fill=X, pady=(0, 20))
    etiquetas = {}

    def crear_tarjeta(parent, titulo, color):
        card = tb.Frame(parent, bootstyle=color)
        card.pack(side=LEFT, fill=BOTH, expand=YES, padx=2)
        tb.Label(card, text=titulo, font=("Helvetica", 10), bootstyle=f"inverse-{color}").pack(pady=(8,0))
        lbl_val = tb.Label(card, text="$0.00", font=("Helvetica", 15, "bold"), bootstyle=f"inverse-{color}")
        lbl_val.pack(pady=(3,8))
        return lbl_val

    etiquetas['IngresosBrutos'] = crear_tarjeta(metricas_frame, "Total Ingresos", "success")
    etiquetas['Liquidez'] = crear_tarjeta(metricas_frame, "Liquidez Total", "info")
    etiquetas['Deudas'] = crear_tarjeta(metricas_frame, "Deudas Pendientes", "danger")
    etiquetas['Real'] = crear_tarjeta(metricas_frame, "Dinero Real (Neto)", "primary")
    etiquetas['Futuros'] = crear_tarjeta(metricas_frame, "Gastos Proyectados", "secondary")
    etiquetas['BalanceProyectado'] = crear_tarjeta(metricas_frame, "Ingresos - Proyectados", "warning")

    # --- CUERPO PRINCIPAL (2 COLUMNAS) ---
    content_frame = tb.Frame(main_frame)
    content_frame.pack(fill=BOTH, expand=YES)

    # COLUMNA IZQUIERDA: Formulario
    form_frame = tb.LabelFrame(content_frame, text=" Registrar Movimiento ", padding=25, bootstyle="primary")
    form_frame.pack(side=LEFT, fill=Y, padx=(0, 20))

    ancho_campos = 28

    tb.Label(form_frame, text="Tipo:").pack(anchor=W, pady=(5,2))
    combo_tipo = tb.Combobox(form_frame, state="readonly", width=ancho_campos)
    combo_tipo.pack(fill=X, pady=(0,15))

    tb.Label(form_frame, text="Monto ($):").pack(anchor=W, pady=(0,2))
    entry_monto = tb.Entry(form_frame, width=ancho_campos)
    entry_monto.pack(fill=X, pady=(0,15))

    tb.Label(form_frame, text="Categoría:").pack(anchor=W, pady=(0,2))
    combo_categoria = tb.Combobox(form_frame, state="readonly", width=ancho_campos)
    combo_categoria.pack(fill=X, pady=(0,15))

    tb.Label(form_frame, text="Descripción:").pack(anchor=W, pady=(0,2))
    entry_desc = tb.Entry(form_frame, width=ancho_campos)
    entry_desc.pack(fill=X, pady=(0,15))

    # --- SELECTOR DE FECHA MEJORADO ---
    tb.Label(form_frame, text="Fecha Pago (Opcional):").pack(anchor=W, pady=(0,2))
    
    frame_fecha = tb.Frame(form_frame)
    frame_fecha.pack(fill=X, pady=(0,25))

    entry_fecha = tb.Entry(frame_fecha, width=18)
    entry_fecha.pack(side=LEFT, fill=X, expand=YES, padx=(0, 5))
    entry_fecha.insert(0, datetime.now().strftime("%Y-%m-%d"))

    def abrir_selector_calendario(entry_destino):
        top_cal = tb.Toplevel(ventana)
        top_cal.title("Seleccionar Fecha")
        top_cal.geometry("320x300")
        top_cal.grab_set()
        
        cal = Calendar(top_cal, selectmode='day', year=datetime.now().year, month=datetime.now().month, day=datetime.now().day, date_pattern='yyyy-mm-dd')
        cal.pack(fill=BOTH, expand=YES, padx=10, pady=10)

        def seleccionar():
            entry_destino.delete(0, tk.END)
            entry_destino.insert(0, cal.get_date())
            top_cal.destroy()

        tb.Button(top_cal, text="Confirmar Fecha", bootstyle="success", command=seleccionar).pack(pady=(0, 10))

    tb.Button(frame_fecha, text="📅 Elegir", bootstyle="info-outline", command=lambda: abrir_selector_calendario(entry_fecha)).pack(side=RIGHT)

    # COLUMNA DERECHA: Tabla y Acciones
    right_frame = tb.Frame(content_frame)
    right_frame.pack(side=LEFT, fill=BOTH, expand=YES)

    columnas = ("ID", "Registro", "Vence", "Tipo", "Categoría", "Monto", "Estado", "Descripción")
    tabla = tb.Treeview(right_frame, columns=columnas, show="headings", bootstyle="primary")
    for col in columnas:
        tabla.heading(col, text=col)
        tabla.column(col, width=100, anchor=CENTER)
    tabla.column("Descripción", width=250, anchor=W)
    tabla.column("ID", width=40)
    tabla.pack(fill=BOTH, expand=YES, pady=(0, 10))

    acciones_frame = tb.Frame(right_frame)
    acciones_frame.pack(fill=X)

    # --- LÓGICA DE ACTUALIZACIÓN ---
    def actualizar_desplegables():
        combo_tipo['values'] = obtener_lista('tipos')
        combo_categoria['values'] = obtener_lista('categorias')
        if combo_tipo['values']: combo_tipo.current(0)
        if combo_categoria['values']: combo_categoria.current(0)
        meses = obtener_meses_registrados()
        mes_actual = combo_meses.get()
        combo_meses['values'] = meses
        if mes_actual not in meses: combo_meses.current(0)

    def actualizar_pantalla(*args):
        mes_filtro = combo_meses.get()
        conexion = conectar()
        cursor = conexion.cursor()

        query_datos = "SELECT id, fecha_registro, IFNULL(fecha_limite, '-'), tipo, categoria, monto, estado, descripcion FROM transacciones"
        query_metricas = "SELECT id, tipo, monto, estado FROM transacciones"
        parametros = ()
        
        if mes_filtro and mes_filtro != "Todos los meses":
            filtro_sql = " WHERE strftime('%Y-%m', fecha_registro) = ?"
            query_datos += filtro_sql
            query_metricas += filtro_sql
            parametros = (mes_filtro,)

        query_datos += " ORDER BY id DESC"

        cursor.execute(query_metricas, parametros)
        registros = cursor.fetchall()
        
        total_ingresos, total_gastos, total_abonos_salidos, deudas_pendientes, futuros = 0, 0, 0, 0, 0
        
        for id_reg, tipo, monto, estado in registros:
            cursor.execute("SELECT SUM(monto) FROM abonos_deudas WHERE deuda_id = ?", (id_reg,))
            total_abonado = cursor.fetchone()[0] or 0
            monto_pendiente = max(0, monto - total_abonado)

            if tipo in ['Ingreso', 'Ingresos']: 
                total_ingresos += monto
            elif tipo == 'Gasto': 
                total_gastos += monto
            elif tipo == 'Deuda' and estado == 'Pendiente': 
                deudas_pendientes += monto_pendiente
                total_abonos_salidos += total_abonado
            elif tipo == 'Gasto Futuro' and estado == 'Pendiente': 
                futuros += monto

        liquidez_efectivo = total_ingresos - total_gastos - total_abonos_salidos
        dinero_neto_sin_deudas = liquidez_efectivo - deudas_pendientes
        balance_proyectado = total_ingresos - futuros

        etiquetas['IngresosBrutos'].config(text=f"${total_ingresos:,.2f}")
        etiquetas['Liquidez'].config(text=f"${liquidez_efectivo:,.2f}")
        etiquetas['Deudas'].config(text=f"${deudas_pendientes:,.2f}")
        etiquetas['Real'].config(text=f"${dinero_neto_sin_deudas:,.2f}")
        etiquetas['Futuros'].config(text=f"${futuros:,.2f}")
        etiquetas['BalanceProyectado'].config(text=f"${balance_proyectado:,.2f}")

        for item in tabla.get_children(): tabla.delete(item)
        cursor.execute(query_datos, parametros)
        for fila in cursor.fetchall(): tabla.insert("", tk.END, values=fila)
        conexion.close()

    combo_meses.bind("<<ComboboxSelected>>", actualizar_pantalla)

    # --- MÓDULO DE GESTIÓN DE ABONOS ---
    def abrir_modulo_abonos():
        seleccion = tabla.selection()
        if not seleccion: return messagebox.showwarning("Atención", "Selecciona una fila de la tabla primero.")
        
        item = tabla.item(seleccion[0])['values']
        id_deuda = item[0]
        tipo_reg = item[3]
        monto_total = float(item[5])
        descripcion_deuda = item[7]

        if tipo_reg != 'Deuda':
            return messagebox.showwarning("Aviso", "Solo puedes gestionar abonos en transacciones de tipo 'Deuda'.")

        vent_abonos = tb.Toplevel(ventana)
        vent_abonos.title(f"Gestión de Abonos - {descripcion_deuda}")
        vent_abonos.geometry("620x500")
        vent_abonos.grab_set()

        header_abono = tb.Frame(vent_abonos, padding=15, bootstyle="dark")
        header_abono.pack(fill=X)
        
        lbl_info_deuda = tb.Label(header_abono, text=f"Deuda: {descripcion_deuda} | Total: ${monto_total:,.2f}", font=("Helvetica", 12, "bold"), bootstyle="inverse-dark")
        lbl_info_deuda.pack(side=LEFT)

        lbl_falta = tb.Label(header_abono, text="", font=("Helvetica", 12, "bold"), bootstyle="inverse-danger")
        lbl_falta.pack(side=RIGHT)

        col_abonos = ("ID", "Fecha", "Monto Abonado", "Descripción")
        tabla_abonos = tb.Treeview(vent_abonos, columns=col_abonos, show="headings", bootstyle="info", height=8)
        for col in col_abonos:
            tabla_abonos.heading(col, text=col)
            tabla_abonos.column(col, width=120, anchor=CENTER)
        tabla_abonos.column("Descripción", width=180, anchor=W)
        tabla_abonos.column("ID", width=40)
        tabla_abonos.pack(fill=BOTH, expand=YES, padx=15, pady=15)

        form_abono = tb.LabelFrame(vent_abonos, text=" Registrar Nuevo Abono ", padding=15, bootstyle="secondary")
        form_abono.pack(fill=X, padx=15, pady=(0, 15))

        tb.Label(form_abono, text="Monto ($):").grid(row=0, column=0, padx=5, sticky=E)
        entry_monto_abono = tb.Entry(form_abono, width=12)
        entry_monto_abono.grid(row=0, column=1, padx=5)

        tb.Label(form_abono, text="Fecha:").grid(row=0, column=2, padx=5, sticky=E)
        entry_fecha_abono = tb.Entry(form_abono, width=12)
        entry_fecha_abono.insert(0, datetime.now().strftime("%Y-%m-%d"))
        entry_fecha_abono.grid(row=0, column=3, padx=5)

        tb.Button(form_abono, text="📅", bootstyle="info-outline", command=lambda: abrir_selector_calendario(entry_fecha_abono)).grid(row=0, column=4, padx=2)

        tb.Label(form_abono, text="Desc:").grid(row=0, column=5, padx=5, sticky=E)
        entry_desc_abono = tb.Entry(form_abono, width=15)
        entry_desc_abono.grid(row=0, column=6, padx=5)

        def refrescar_abonos():
            for item in tabla_abonos.get_children(): tabla_abonos.delete(item)
            
            conexion = conectar()
            cursor = conexion.cursor()
            cursor.execute("SELECT id, fecha, monto, descripcion FROM abonos_deudas WHERE deuda_id = ?", (id_deuda,))
            abonos = cursor.fetchall()
            
            total_abonado = sum(row[2] for row in abonos)
            for row in abonos:
                tabla_abonos.insert("", tk.END, values=(row[0], row[1], f"${row[2]:,.2f}", row[3]))
            
            falta = monto_total - total_abonado
            lbl_falta.config(text=f"Falta: ${falta:,.2f}")
            
            if falta <= 0:
                marcar_como_completado(id_deuda)
            
            conexion.close()
            actualizar_pantalla()

        def guardar_abono():
            try: m_abono = float(entry_monto_abono.get())
            except: return messagebox.showerror("Error", "Monto de abono inválido.")
            
            desc_abono = entry_desc_abono.get() or "Abono parcial"
            f_abono = entry_fecha_abono.get() or datetime.now().strftime("%Y-%m-%d")

            conexion = conectar()
            cursor = conexion.cursor()
            cursor.execute("INSERT INTO abonos_deudas (deuda_id, monto, fecha, descripcion) VALUES (?, ?, ?, ?)", 
                           (id_deuda, m_abono, f_abono, desc_abono))
            conexion.commit()
            conexion.close()

            entry_monto_abono.delete(0, tk.END)
            entry_desc_abono.delete(0, tk.END)
            refrescar_abonos()

        def eliminar_abono():
            seleccion_ab = tabla_abonos.selection()
            if not seleccion_ab: return messagebox.showwarning("Atención", "Selecciona un abono para eliminar.")
            id_ab = tabla_abonos.item(seleccion_ab[0])['values'][0]
            
            conexion = conectar()
            cursor = conexion.cursor()
            cursor.execute("DELETE FROM abonos_deudas WHERE id = ?", (id_ab,))
            conexion.commit()
            conexion.close()
            refrescar_abonos()

        tb.Button(form_abono, text="➕", bootstyle="success", command=guardar_abono).grid(row=0, column=7, padx=5)
        
        btn_eliminar_ab = tb.Button(vent_abonos, text="❌ Eliminar Abono Seleccionado", bootstyle="danger-outline", command=eliminar_abono)
        btn_eliminar_ab.pack(pady=(0, 15))

        refrescar_abonos()

    # --- FUNCIONES DE BOTONES PRINCIPALES ---
    def guardar():
        try: monto = float(entry_monto.get())
        except: return messagebox.showerror("Error", "Monto inválido.")
        tipo = combo_tipo.get()
        estado = 'Pendiente' if tipo in ['Deuda', 'Gasto Futuro'] else 'Completado'
        fecha = entry_fecha.get() if entry_fecha.get() != "" else None
        
        registrar_movimiento(tipo, monto, combo_categoria.get(), entry_desc.get(), estado, fecha)
        entry_monto.delete(0, tk.END); entry_desc.delete(0, tk.END)
        actualizar_desplegables(); actualizar_pantalla()

    def completar():
        if not tabla.selection(): return messagebox.showwarning("Atención", "Selecciona una fila.")
        marcar_como_completado(tabla.item(tabla.selection()[0])['values'][0])
        actualizar_pantalla()

    def borrar():
        if not tabla.selection(): return messagebox.showwarning("Atención", "Selecciona una fila.")
        if messagebox.askyesno("Confirmar", "¿Eliminar registro y sus abonos asociados?"):
            eliminar_movimiento(tabla.item(tabla.selection()[0])['values'][0])
            actualizar_pantalla()

    def editar_movimiento():
        seleccion = tabla.selection()
        if not seleccion: return messagebox.showwarning("Atención", "Selecciona un registro para editar.")
        
        item = tabla.item(seleccion[0])['values']
        id_reg = item[0]
        
        vent_edicion = tb.Toplevel(ventana)
        vent_edicion.title("Editar Movimiento")
        vent_edicion.geometry("450x450")
        vent_edicion.grab_set()

        padding = 10
        tb.Label(vent_edicion, text="Tipo:").grid(row=0, column=0, padx=padding, pady=padding, sticky=E)
        edit_tipo = tb.Combobox(vent_edicion, values=obtener_lista('tipos'), state="readonly", width=25)
        edit_tipo.set(item[3])
        edit_tipo.grid(row=0, column=1, padx=padding, pady=padding)

        tb.Label(vent_edicion, text="Monto ($):").grid(row=1, column=0, padx=padding, pady=padding, sticky=E)
        edit_monto = tb.Entry(vent_edicion, width=27)
        edit_monto.insert(0, str(item[5]))
        edit_monto.grid(row=1, column=1, padx=padding, pady=padding)

        tb.Label(vent_edicion, text="Categoría:").grid(row=2, column=0, padx=padding, pady=padding, sticky=E)
        edit_cat = tb.Combobox(vent_edicion, values=obtener_lista('categorias'), state="readonly", width=25)
        edit_cat.set(item[4])
        edit_cat.grid(row=2, column=1, padx=padding, pady=padding)

        tb.Label(vent_edicion, text="Descripción:").grid(row=3, column=0, padx=padding, pady=padding, sticky=E)
        edit_desc = tb.Entry(vent_edicion, width=27)
        edit_desc.insert(0, item[7])
        edit_desc.grid(row=3, column=1, padx=padding, pady=padding)
        
        tb.Label(vent_edicion, text="Vencimiento:").grid(row=4, column=0, padx=padding, pady=padding, sticky=E)
        
        frame_ed_fecha = tb.Frame(vent_edicion)
        frame_ed_fecha.grid(row=4, column=1, padx=padding, pady=padding)
        edit_fecha = tb.Entry(frame_ed_fecha, width=18)
        edit_fecha.pack(side=LEFT, padx=(0, 5))
        if item[2] != '-': edit_fecha.insert(0, item[2])
        tb.Button(frame_ed_fecha, text="📅", bootstyle="info-outline", command=lambda: abrir_selector_calendario(edit_fecha)).pack(side=RIGHT)

        tb.Label(vent_edicion, text="Estado:").grid(row=5, column=0, padx=padding, pady=padding, sticky=E)
        edit_estado = tb.Combobox(vent_edicion, values=["Completado", "Pendiente"], state="readonly", width=25)
        edit_estado.set(item[6])
        edit_estado.grid(row=5, column=1, padx=padding, pady=padding)

        def guardar_edicion():
            try: nuevo_monto = float(edit_monto.get())
            except: return messagebox.showerror("Error", "Monto inválido.")
            f_limite = edit_fecha.get() if edit_fecha.get() != "" else None
            actualizar_movimiento(id_reg, edit_tipo.get(), nuevo_monto, edit_cat.get(), edit_desc.get(), edit_estado.get(), f_limite)
            vent_edicion.destroy()
            actualizar_pantalla()
            messagebox.showinfo("Éxito", "Registro actualizado.")

        tb.Button(vent_edicion, text="Guardar Cambios", bootstyle="warning", command=guardar_edicion).grid(row=6, columnspan=2, pady=20)

    # --- VENTANA DE CONFIGURACIÓN ---
    def abrir_configuracion():
        vent_config = tb.Toplevel(ventana)
        vent_config.title("Gestor de Categorías y Tipos")
        vent_config.geometry("540x420")
        vent_config.grab_set()

        frame_modal = tb.Frame(vent_config, padding=15)
        frame_modal.pack(fill=BOTH, expand=YES)

        def crear_panel_gestion(parent, titulo, tabla_db):
            card = tb.LabelFrame(parent, text=f" {titulo} ", padding=15, bootstyle="info")
            card.pack(side=LEFT, fill=BOTH, expand=YES, padx=5)

            listbox = tk.Listbox(card, height=10, width=18, bg="#2b3e50", fg="white", selectbackground="#00bc8c", font=("Helvetica", 11), relief=FLAT)
            listbox.pack(fill=BOTH, expand=YES, pady=(0, 10))

            def agregar():
                nuevo = simpledialog.askstring("Nuevo Registro", f"Nombre para nueva {titulo[:-1].lower()}:", parent=vent_config)
                if nuevo:
                    conexion = conectar()
                    cursor = conexion.cursor()
                    try:
                        cursor.execute(f"INSERT INTO {tabla_db} (nombre) VALUES (?)", (nuevo.strip(),))
                        conexion.commit()
                    except: messagebox.showerror("Error", "Este elemento ya existe.")
                    conexion.close()
                    refrescar(); actualizar_desplegables()

            def editar():
                seleccion = listbox.curselection()
                if seleccion:
                    viejo = listbox.get(seleccion[0])
                    nuevo = simpledialog.askstring("Editar Registro", f"Modificar '{viejo}':", initialvalue=viejo, parent=vent_config)
                    if nuevo and nuevo.strip() != viejo:
                        conexion = conectar()
                        cursor = conexion.cursor()
                        try:
                            cursor.execute(f"UPDATE {tabla_db} SET nombre = ? WHERE nombre = ?", (nuevo.strip(), viejo))
                            columna = 'categoria' if tabla_db == 'categorias' else 'tipo'
                            cursor.execute(f"UPDATE transacciones SET {columna} = ? WHERE {columna} = ?", (nuevo.strip(), viejo))
                            conexion.commit()
                        except sqlite3.IntegrityError:
                            messagebox.showerror("Error", "Ese nombre ya existe.")
                        conexion.close()
                        refrescar(); actualizar_desplegables(); actualizar_pantalla()

            def eliminar():
                seleccion = listbox.curselection()
                if seleccion:
                    valor = listbox.get(seleccion[0])
                    if messagebox.yesno("Confirmar", f"¿Eliminar '{valor}'?"):
                        conexion = conectar()
                        cursor = conexion.cursor()
                        cursor.execute(f"DELETE FROM {tabla_db} WHERE nombre = ?", (valor,))
                        conexion.commit()
                        conexion.close()
                        refrescar(); actualizar_desplegables()

            btn_frame = tb.Frame(card)
            btn_frame.pack(fill=X)

            tb.Button(btn_frame, text="➕", bootstyle="success-outline", command=agregar).pack(side=LEFT, expand=YES, fill=X, padx=2)
            tb.Button(btn_frame, text="✏️", bootstyle="warning-outline", command=editar).pack(side=LEFT, expand=YES, fill=X, padx=2)
            tb.Button(btn_frame, text="❌", bootstyle="danger-outline", command=eliminar).pack(side=LEFT, expand=YES, fill=X, padx=2)

            def refrescar():
                listbox.delete(0, tk.END)
                for item in obtener_lista(tabla_db): listbox.insert(tk.END, item)

            refrescar()

        crear_panel_gestion(frame_modal, "Categorías", "categorias")
        crear_panel_gestion(frame_modal, "Tipos de Movimiento", "tipos")

    def abrir_analisis():
        mes_filtro = combo_meses.get()
        vent_analisis = tb.Toplevel(ventana)
        vent_analisis.title("Análisis")
        vent_analisis.geometry("400x450")
        tb.Label(vent_analisis, text="📈 Gastos por Categoría", font=("Helvetica", 14, "bold")).pack(pady=15)
        
        conexion = conectar()
        cursor = conexion.cursor()
        query = "SELECT categoria, SUM(monto) FROM transacciones WHERE tipo = 'Gasto'"
        params = ()
        if mes_filtro != "Todos los meses":
            query += " AND strftime('%Y-%m', fecha_registro) = ?"
            params = (mes_filtro,)
        query += " GROUP BY categoria ORDER BY SUM(monto) DESC"
        
        cursor.execute(query, params)
        gastos = cursor.fetchall()
        conexion.close()

        if not gastos: return tb.Label(vent_analisis, text="Sin gastos en este periodo.").pack(pady=20)

        tabla_analisis = tb.Treeview(vent_analisis, columns=("Cat", "Tot"), show="headings", bootstyle="info")
        tabla_analisis.heading("Cat", text="Categoría"); tabla_analisis.heading("Tot", text="Total")
        tabla_analisis.column("Cat", width=200); tabla_analisis.column("Tot", width=150, anchor=CENTER)
        tabla_analisis.pack(fill=BOTH, expand=YES, padx=20, pady=10)

        total_mes = 0
        for cat, monto in gastos:
            tabla_analisis.insert("", tk.END, values=(cat, f"${monto:,.2f}"))
            total_mes += monto
        tb.Label(vent_analisis, text=f"Total: ${total_mes:,.2f}", font=("Helvetica", 14, "bold"), bootstyle="danger").pack(pady=10)

    # --- BOTONES EN LA INTERFAZ ---
    tb.Button(form_frame, text="➕ Guardar Movimiento", bootstyle="success", width=22, command=guardar).pack(pady=20)
    
    tb.Button(acciones_frame, text="✔ Completar", bootstyle="outline-success", command=completar).pack(side=LEFT, padx=5)
    tb.Button(acciones_frame, text="💸 Ver Abonos", bootstyle="outline-info", command=abrir_modulo_abonos).pack(side=LEFT, padx=5)
    tb.Button(acciones_frame, text="✏️ Editar", bootstyle="outline-warning", command=editar_movimiento).pack(side=LEFT, padx=5)
    tb.Button(acciones_frame, text="❌ Eliminar", bootstyle="outline-danger", command=borrar).pack(side=LEFT, padx=5)
    tb.Button(acciones_frame, text="⚙️ Configurar", bootstyle="warning", command=abrir_configuracion).pack(side=LEFT, padx=5)
    
    tb.Button(acciones_frame, text="📊 Ver Análisis", bootstyle="info", command=abrir_analisis).pack(side=RIGHT, padx=5)

    actualizar_desplegables()
    actualizar_pantalla()
    ventana.mainloop()

if __name__ == "__main__":
    crear_tablas()
    iniciar_interfaz()