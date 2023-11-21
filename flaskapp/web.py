from flask import Flask, Response, render_template, request, url_for, redirect
import pymysql
import datetime
import io
import xlwt
import barcode
from barcode.writer import ImageWriter
from flask_weasyprint import HTML, render_pdf
from conexion import Conhost, Conuser, Conpassword, Condb

app = Flask(__name__)
app.secret_key = 'd589d3d0d15d764ed0a98ff5a37af547'

@app.route('/', methods=['GET', 'POST'])
def home():
	mensaje = ""
	if request.method == 'POST':
		codigo = request.form["codigo"]
		if '012023' in codigo:
			idcatedratico = obtener_id_catedratico(codigo)
			return redirect(url_for('presenciales', idcatedratico = idcatedratico))
		else:
			mensaje = "Código incorrecto, vuelva a escanear"
			return render_template('home.html', title="Inicio", mensaje = mensaje)
	return render_template('home.html', title="Inicio", mensaje = mensaje)

def obtener_id_catedratico(codigo):
    idcatedratico = codigo.split('012023')[0]
    return int(idcatedratico)

@app.route('/presenciales/<idcatedratico>', methods=['GET', 'POST'])
def presenciales(idcatedratico):
	try:
		hoy = datetime.date.today()
		now = datetime.datetime.now()
		fechahora = now.strftime("%H:%M:%S")
		conexion = pymysql.connect(host=Conhost, user=Conuser, password=Conpassword, db=Condb)
		try:
			with conexion.cursor() as cursor:
				consulta = f"Select identradas from entradas where idcatedratico = {idcatedratico} and fecha = '{str(hoy)}' and completo = 0 order by horaentrada desc"
				cursor.execute(consulta)
				banderin = cursor.fetchall()
				if len(banderin) > 0:
					consulta = f"select p.idperiodos, c.nombre, c.horainicio, c.horafin, DATE_FORMAT(p.fecha,'%d/%m/%Y'), a.codigo, c.seccion, c.modalidad from periodos p inner join clase c on p.idclase = c.idclase inner join carrera a on a.idcarrera = c.idcarrera where c.modalidad = 1 and p.idestado = 7 and c.idcatedratico = {str(idcatedratico)} and '{str(fechahora)}' < c.horafin and p.fecha = '{str(hoy)}' order by c.horainicio asc;"
					cursor.execute(consulta)
					periodostarde = cursor.fetchall()
					consulta = f"select p.idperiodos, c.nombre, c.horainicio, c.horafin, DATE_FORMAT(p.fecha,'%d/%m/%Y'), a.codigo, c.seccion, c.modalidad from periodos p inner join clase c on p.idclase = c.idclase inner join carrera a on a.idcarrera = c.idcarrera where c.modalidad = 1 and p.idestado = 7 and c.idcatedratico = {str(idcatedratico)} and '{str(fechahora)}' >= c.horafin and p.fecha = '{str(hoy)}' order by c.horainicio asc;"
					estado = 1
					cursor.execute(consulta)
				else:
					periodostarde = []
					consulta = f"select p.idperiodos, c.nombre, c.horainicio, c.horafin, DATE_FORMAT(p.fecha,'%d/%m/%Y'), a.codigo, c.seccion, c.modalidad from periodos p inner join clase c on p.idclase = c.idclase inner join carrera a on a.idcarrera = c.idcarrera where c.modalidad = 1 and p.idestado = 1 and c.idcatedratico = {str(idcatedratico)} and AddTime(c.horainicio, '00:10:00') > '{str(fechahora)}' and p.fecha = '{str(hoy)}' order by c.horainicio asc;"
					estado = 0
					cursor.execute(consulta)
			# Con fetchall traemos todas las filas
				periodos = cursor.fetchall()
				consulta = f"select c.nombre, c.apellido, n.abreviatura, c.telefono, c.correo from catedratico c inner join nivelacademico n on c.idnivelacademico = n.idnivelacademico where c.idcatedratico = {idcatedratico};"
				cursor.execute(consulta)
				catedratico = cursor.fetchone()
				if len(periodostarde) > 0:
					mensajeini = 1
				else:
					mensajeini = 0
		finally:
			conexion.close()
	except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
		print("Ocurrió un error al conectar: ", e)
	if request.method == 'POST':
		try:
			conexion = pymysql.connect(host=Conhost, user=Conuser, password=Conpassword, db=Condb)
			try:
				with conexion.cursor() as cursor:
					if estado == 0:
						consulta = f"insert into entradas(idcatedratico, fecha, horaentrada) VALUES({idcatedratico}, '{str(hoy)}', '{str(fechahora)}')"
						cursor.execute(consulta)
						for i in periodos:
							consulta = f"Update periodos set idestado = 7 where idperiodos = {i[0]}"
							cursor.execute(consulta)
					elif estado == 1:
						consulta = f"update entradas set horasalida = '{str(fechahora)}', completo = 1 where idcatedratico = {idcatedratico} and fecha = '{str(hoy)}' and completo = 0"
						cursor.execute(consulta)
						for i in periodos:
							consulta = f"Update periodos set idestado = 2, fecharegistro = '{str(hoy)}' where idperiodos = {i[0]}"
							cursor.execute(consulta)
					conexion.commit()
			finally:
				conexion.close()
		except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
			print("Ocurrió un error al conectar: ", e)
		return redirect(url_for('home'))
	return render_template('presenciales.html', title="Registrar Periodos", periodos = periodos, catedratico = catedratico, estado = estado, fechahora = fechahora, mensajeini = mensajeini)

@app.route('/catedraticos')
def catedraticos():
	try:
		conexion = pymysql.connect(host=Conhost, user=Conuser, password=Conpassword, db=Condb)
		try:
			with conexion.cursor() as cursor:
				cursor.execute("SELECT c.nombre, c.apellido, n.abreviatura, c.idcatedratico from catedratico c inner join nivelacademico n on c.idnivelacademico = n.idnivelacademico order by n.abreviatura, c.nombre;")
			# Con fetchall traemos todas las filas
				catedraticos = cursor.fetchall()
		finally:
			conexion.close()
	except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
		print("Ocurrió un error al conectar: ", e)
	return render_template('catedraticos.html', title="Catedraticos", catedraticos = catedraticos)

@app.route('/nuevocatedratico', methods=['GET', 'POST'])
def nuevocatedratico():
	try:
		conexion = pymysql.connect(host=Conhost, user=Conuser, password=Conpassword, db=Condb)
		try:
			with conexion.cursor() as cursor:
				cursor.execute("SELECT idnivelacademico, nombre from nivelacademico order by nombre;")
			# Con fetchall traemos todas las filas
				niveles = cursor.fetchall()
		finally:
			conexion.close()
	except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
		print("Ocurrió un error al conectar: ", e)

	if request.method == 'POST':
		nombre = request.form["nombre"]
		apellido = request.form["apellido"]
		nivel = request.form["nivel"]
		telefono = request.form["telefono"]
		correo = request.form["correo"].lower()
		try:
			conexion = pymysql.connect(host=Conhost, user=Conuser, password=Conpassword, db=Condb)
			try:
				with conexion.cursor() as cursor:
					consulta = f"INSERT INTO catedratico(nombre,apellido,idnivelacademico, telefono, correo) VALUES ('{nombre}','{apellido}',{nivel},'{telefono}','{correo}');"
					cursor.execute(consulta)
				conexion.commit()
			finally:
				conexion.close()
		except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
			print("Ocurrió un error al conectar: ", e)
		return redirect(url_for('catedraticos'))
	return render_template('nuevocatedratico.html', title="Nuevo Catedratico", niveles = niveles)

@app.route('/editarcatedratico/<id>', methods=['GET', 'POST'])
def editarcatedratico(id):
	try:
		conexion = pymysql.connect(host=Conhost, user=Conuser, password=Conpassword, db=Condb)
		try:
			with conexion.cursor() as cursor:
				cursor.execute("SELECT idnivelacademico, nombre from nivelacademico order by nombre;")
			# Con fetchall traemos todas las filas
				niveles = cursor.fetchall()
				consulta = f"SELECT nombre, apellido, idnivelacademico, telefono, correo from catedratico where idcatedratico = {str(id)}"
				cursor.execute(consulta)
				catedratico = cursor.fetchone()
		finally:
			conexion.close()
	except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
		print("Ocurrió un error al conectar: ", e)
	id = str(int(id))
	number = id.rjust(4, '0')
	number = number + '01202346'
	barcode_format = barcode.get_barcode_class('upc')

	#Generate barcode and render as image
	my_barcode = barcode_format(number, writer=ImageWriter())

	#Save barcode as PNG
	aux = f"static/barcodes/{catedratico[0]}_{catedratico[1]}"
	my_barcode.save(aux)


	if request.method == 'POST':
		nombre = request.form["nombre"]
		apellido = request.form["apellido"]
		nivel = request.form["nivel"]
		telefono = request.form["telefono"]
		correo = request.form["correo"]
		correo = correo.lower()
		try:
			conexion = pymysql.connect(host=Conhost, user=Conuser, password=Conpassword, db=Condb)
			try:
				with conexion.cursor() as cursor:
					consulta = f"UPDATE catedratico SET nombre = '{nombre}', apellido = '{apellido}', idnivelacademico = {nivel}, telefono = '{telefono}', correo = '{correo}' WHERE idcatedratico = {id};"
					cursor.execute(consulta)
				conexion.commit()
			finally:
				conexion.close()
		except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
			print("Ocurrió un error al conectar: ", e)
		return redirect(url_for('catedraticos'))
	return render_template('editarcatedratico.html', title="Editar Catedratico", niveles = niveles, catedratico=catedratico)

@app.route('/eliminarcatedratico/<id>', methods=['GET', 'POST'])
def eliminarcatedratico(id):
	try:
		conexion = pymysql.connect(host=Conhost, user=Conuser, password=Conpassword, db=Condb)
		try:
			with conexion.cursor() as cursor:
				consulta = f"DELETE from catedratico WHERE idcatedratico = {str(id)}"
				cursor.execute(consulta)
			conexion.commit()
		finally:
			conexion.close()
	except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
		print("Ocurrió un error al conectar: ", e)

	return redirect(url_for('catedraticos'))

@app.route('/eliminarclase/<id>', methods=['GET', 'POST'])
def eliminarclase(id):
	try:
		conexion = pymysql.connect(host=Conhost, user=Conuser, password=Conpassword, db=Condb)
		try:
			with conexion.cursor() as cursor:
				consulta = f"SELECT c.idcatedratico, c.nombre, c.apellido, n.abreviatura from catedratico c inner join nivelacademico n on c.idnivelacademico = n.idnivelacademico inner join clase l on c.idcatedratico = l.idcatedratico where l.idclase = {id} order by n.abreviatura, c.nombre;"
				cursor.execute(consulta)
			# Con fetchall traemos todas las filas
				catedraticos = cursor.fetchone()
				consulta = f"DELETE from clase WHERE idclase = {str(id)}"
				cursor.execute(consulta)
				consulta = f"DELETE from periodos WHERE idclase = {str(id)}"
				cursor.execute(consulta)
			conexion.commit()
		finally:
			conexion.close()
	except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
		print("Ocurrió un error al conectar: ", e)
	return redirect(url_for('periodoscat', id = catedraticos[0]))

@app.route('/deshabilitarclase/<id>', methods=['GET', 'POST'])
def deshabilitarclase(id):
	try:
		conexion = pymysql.connect(host=Conhost, user=Conuser, password=Conpassword, db=Condb)
		try:
			with conexion.cursor() as cursor:
				consulta = f"SELECT c.idcatedratico, c.nombre, c.apellido, n.abreviatura from catedratico c inner join nivelacademico n on c.idnivelacademico = n.idnivelacademico inner join clase l on c.idcatedratico = l.idcatedratico where l.idclase = {id} order by n.abreviatura, c.nombre;"
				cursor.execute(consulta)
			# Con fetchall traemos todas las filas
				catedraticos = cursor.fetchone()
				consulta = f"update periodos set idestado = 5 WHERE idclase = {str(id)} and idestado = 1"
				cursor.execute(consulta)
			conexion.commit()
		finally:
			conexion.close()
	except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
		print("Ocurrió un error al conectar: ", e)
	return redirect(url_for('periodoscat', id = catedraticos[0]))

@app.route('/periodos')
def periodos():
	return render_template('periodos.html', title="Periodos")

@app.route('/nuevaclase', methods=['GET', 'POST'])
def nuevaclase():
	dias = [[0, "Lunes"], [1, "Martes"], [2, "Miercoles"], [3, "Jueves"], [4, "Viernes"], [5, "Sabado"], [6, "Domingo"]]
	try:
		conexion = pymysql.connect(host=Conhost, user=Conuser, password=Conpassword, db=Condb)
		try:
			with conexion.cursor() as cursor:
				cursor.execute("SELECT idcarrera, nombre, codigo from carrera order by codigo;")
			# Con fetchall traemos todas las filas
				carreras = cursor.fetchall()
				cursor.execute("SELECT c.idcatedratico, c.nombre, c.apellido, n.abreviatura from catedratico c inner join nivelacademico n on c.idnivelacademico = n.idnivelacademico order by n.abreviatura, c.nombre;")
			# Con fetchall traemos todas las filas
				catedraticos = cursor.fetchall()
		finally:
			conexion.close()
	except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
		print("Ocurrió un error al conectar: ", e)

	if request.method == 'POST':
		curso = request.form["curso"]
		carrera = request.form["carrera"]
		fechainicio = request.form["fechainicio"]
		fechafin = request.form["fechafin"]
		horainicio = request.form["horainicio"]
		horafin = request.form["horafin"]
		seccion = request.form["seccion"]
		precio = request.form["precio"]
		dia = request.form["dia"]
		catedratico = request.form["catedratico"]
		modalidad = request.form["modalidad"]
		formadepago = request.form["formadepago"]
		plan = request.form["plan"]
		try:
			conexion = pymysql.connect(host=Conhost, user=Conuser, password=Conpassword, db=Condb)
			try:
				with conexion.cursor() as cursor:
					consulta = "INSERT INTO clase(nombre,fechainicio,fechafin, seccion, idcarrera, horainicio, horafin, precio, idcatedratico, dia, modalidad, formadepago) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);"
					cursor.execute(consulta, (curso, fechainicio, fechafin, seccion, carrera, horainicio, horafin, precio, catedratico, dia, modalidad, formadepago))
					conexion.commit()
					arrfechainicio = str(fechainicio).split('-')
					arrfechafin = str(fechafin).split('-')
					newfechainicio = datetime.date(int(arrfechainicio[0]), int(arrfechainicio[1]), int(arrfechainicio[2]))
					newfechafin = datetime.date(int(arrfechafin[0]), int(arrfechafin[1]), int(arrfechafin[2]))
					print(dia)
					while int(newfechainicio.weekday()) != int(dia):
						print(newfechainicio.weekday())
						newfechainicio += datetime.timedelta(days=1)
						print(newfechainicio)
					if int(newfechainicio.weekday()) == int(dia):
						aux = newfechainicio
						while aux <= newfechafin:
							consulta = "SELECT idclase FROM clase ORDER BY idclase DESC LIMIT 1;"
							cursor.execute(consulta)
							idclase = cursor.fetchone()
							idclase = idclase[0]
							consulta = "INSERT INTO periodos(idclase,fecha,idestado, liquidado, precio, formadepago) VALUES (%s,%s,%s,%s,%s,%s);"
							cursor.execute(consulta, (idclase, aux, 1, 0, precio, formadepago))
							if plan == "Semanal":
								aux = aux + datetime.timedelta(days=7)
							elif plan == "Quincenal":
								aux = aux + datetime.timedelta(days=14)
						conexion.commit()
			finally:
				conexion.close()
		except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
			print("Ocurrió un error al conectar: ", e)
		return redirect(url_for('periodos'))
	return render_template('nuevaclase.html', title="Nuevo Periodo", carreras = carreras, dias=dias, catedraticos=catedraticos)

@app.route('/editarclase/<id>', methods=['GET', 'POST'])
def editarclase(id):
	hoy = datetime.date.today()
	dias = [[0, "Lunes"], [1, "Martes"], [2, "Miercoles"], [3, "Jueves"], [4, "Viernes"], [5, "Sabado"], [6, "Domingo"]]
	try:
		conexion = pymysql.connect(host=Conhost, user=Conuser, password=Conpassword, db=Condb)
		try:
			with conexion.cursor() as cursor:
				cursor.execute("SELECT idcarrera, nombre, codigo from carrera order by codigo;")
			# Con fetchall traemos todas las filas
				carreras = cursor.fetchall()
				consulta = f"SELECT c.idcatedratico, c.nombre, c.apellido, n.abreviatura from catedratico c inner join nivelacademico n on c.idnivelacademico = n.idnivelacademico inner join clase l on c.idcatedratico = l.idcatedratico where l.idclase = {id} order by n.abreviatura, c.nombre;"
				cursor.execute(consulta)
			# Con fetchall traemos todas las filas
				catedraticos = cursor.fetchone()
				consulta = f"SELECT nombre, seccion, idcarrera, horainicio, horafin, precio, idcatedratico, modalidad, formadepago, fechainicio, fechafin, dia  from clase where idclase = {id}"
				cursor.execute(consulta)
				periodo = cursor.fetchone()
				horas = []
				horas.append(str(periodo[3]).rjust(8, '0'))
				horas.append(str(periodo[4]).rjust(8, '0'))
		finally:
			conexion.close()
	except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
		print("Ocurrió un error al conectar: ", e)

	if request.method == 'POST':
		curso = request.form["curso"]
		seccion = request.form["seccion"]
		carrera = request.form["carrera"]
		horainicio = request.form["horainicio"]
		horafin = request.form["horafin"]
		precio = request.form["precio"]
		modalidad = request.form["modalidad"]
		formadepago = request.form["formadepago"]
		fechainicio = request.form["fechainicio"]
		fechafin = request.form["fechafin"]
		dia = request.form["dia"]
		try:
			conexion = pymysql.connect(host=Conhost, user=Conuser, password=Conpassword, db=Condb)
			try:
				with conexion.cursor() as cursor:
					consulta = "UPDATE clase set nombre = %s, seccion = %s, idcarrera = %s, horainicio = %s, horafin = %s, precio = %s, modalidad = %s, formadepago = %s, fechainicio = %s, fechafin = %s, dia = %s where idclase = %s;"
					cursor.execute(consulta, (curso, seccion, carrera, horainicio, horafin, precio, modalidad, formadepago, fechainicio, fechafin, dia, id))
					consulta = f"UPDATE periodos set precio = {precio} WHERE idclase = {id} and liquidado = 0 and idestado = 1"
					cursor.execute(consulta)
					consulta = f"UPDATE periodos set formadepago = '{formadepago}' WHERE idclase = {id} and liquidado = 0"
					cursor.execute(consulta)
					if str(dia) != str(periodo[11]):
						consulta = f"DELETE FROM periodos where idclase = {id} and liquidado = 0 and idestado = 1 and fecha > '{str(hoy)}'"
						cursor.execute(consulta)
						arrfechafin = str(fechafin).split('-')
						newfechainicio = datetime.date.today()
						newfechafin = datetime.date(int(arrfechafin[0]), int(arrfechafin[1]), int(arrfechafin[2]))
						print(newfechainicio.weekday())
						print(dia)
						print(int(newfechainicio.weekday()) != int(dia))
						while int(newfechainicio.weekday()) != int(dia):
							print(newfechainicio.weekday())
							newfechainicio += datetime.timedelta(days=1)
							print(newfechainicio)
						if int(newfechainicio.weekday()) == int(dia):
							aux = newfechainicio
							while aux <= newfechafin:
								idclase = id
								consulta = "INSERT INTO periodos(idclase,fecha,idestado, liquidado, precio, formadepago) VALUES (%s,%s,%s,%s,%s,%s);"
								cursor.execute(consulta, (idclase, aux, 1, 0, precio, formadepago))
								aux = aux + datetime.timedelta(days=7)
					conexion.commit()
			finally:
				conexion.close()
		except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
			print("Ocurrió un error al conectar: ", e)
		return redirect(url_for('periodoscat', id = catedraticos[0]))
	return render_template('editarclase.html', title="Editar Periodo", carreras = carreras, dias=dias, catedraticos = catedraticos, periodo=periodo, horas = horas,idclase=id)

@app.route('/periodosclase', methods=['GET', 'POST'])
def periodosclase():
	try:
		hoy = datetime.date.today()
		conexion = pymysql.connect(host=Conhost, user=Conuser, password=Conpassword, db=Condb)
		try:
			with conexion.cursor() as cursor:
				consulta = f"SELECT d.idcarrera, d.codigo, d.nombre, c.seccion from carrera d inner join clase c on c.idcarrera = d.idcarrera where c.fechafin >=CURDATE() group by d.codigo, d.nombre, c.seccion order by d.codigo, d.nombre, c.seccion;"
				cursor.execute(consulta)
			# Con fetchall traemos todas las filas
				carreras = cursor.fetchall()
		finally:
			conexion.close()
	except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
		print("Ocurrió un error al conectar: ", e)
	return render_template('periodosclase.html', title="Periodos por Clase", carreras=carreras)

@app.route('/periodosclas/<idcarrera>&<seccion>', methods=['GET', 'POST'])
def periodosclas(idcarrera, seccion):
	dias = [[0, "Lunes"], [1, "Martes"], [2, "Miercoles"], [3, "Jueves"], [4, "Viernes"], [5, "Sabado"], [6, "Domingo"]]
	try:
		conexion = pymysql.connect(host=Conhost, user=Conuser, password=Conpassword, db=Condb)
		try:
			with conexion.cursor() as cursor:
				consulta = f"SELECT c.nombre, c.codigo from carrera c where c.idcarrera = {idcarrera}"
				cursor.execute(consulta)
				carrera = cursor.fetchone()
				clasesdias = []
				cantidades = []
				for i in range(7):
					consulta = f"SELECT c.nombre, DATE_FORMAT(c.fechainicio,'%d/%m/%Y'), DATE_FORMAT(c.fechafin,'%d/%m/%Y'), c.horainicio, c.horafin, n.abreviatura, m.nombre, m.apellido, c.modalidad from carrera d inner join clase c on c.idcarrera = d.idcarrera inner join catedratico m on m.idcatedratico = c.idcatedratico inner join nivelacademico n on n.idnivelacademico = m.idnivelacademico where c.fechafin >=CURDATE() and c.idcarrera = {idcarrera} and c.seccion = '{seccion}' and c.dia = {i} order by c.dia, c.horainicio, c.nombre;"
					cursor.execute(consulta)
					clases = cursor.fetchall()
					cantidad = len(clases)
					cantidades.append(cantidad)
					clasesdias.append(clases)
		finally:
			conexion.close()
	except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
		print("Ocurrió un error al conectar: ", e)
	return render_template('periodosclas.html', title="Periodos por Clase", carrera=carrera, clasesdias = clasesdias, dias=dias, seccion=seccion, cantidades = cantidades)

@app.route('/periodoscatedratico', methods=['GET', 'POST'])
def periodoscatedratico():
	try:
		hoy = datetime.date.today()
		conexion = pymysql.connect(host=Conhost, user=Conuser, password=Conpassword, db=Condb)
		try:
			with conexion.cursor() as cursor:
				consulta = f"SELECT c.idcatedratico, c.nombre, c.apellido, n.abreviatura from catedratico c inner join nivelacademico n on c.idnivelacademico = n.idnivelacademico inner join clase l on l.idcatedratico = c.idcatedratico where l.fechafin >= '{str(hoy)}' group by c.idcatedratico, c.nombre, c.apellido, n.abreviatura order by n.abreviatura, c.nombre;"
				cursor.execute(consulta)
			# Con fetchall traemos todas las filas
				catedraticos = cursor.fetchall()
		finally:
			conexion.close()
	except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
		print("Ocurrió un error al conectar: ", e)
	return render_template('periodoscatedratico.html', title="Periodos por Catedrático", catedraticos=catedraticos)

@app.route('/periodoscat/<id>', methods=['GET', 'POST'])
def periodoscat(id):
	dias = [[0, "Lunes"], [1, "Martes"], [2, "Miercoles"], [3, "Jueves"], [4, "Viernes"], [5, "Sabado"], [6, "Domingo"]]
	try:
		conexion = pymysql.connect(host=Conhost, user=Conuser, password=Conpassword, db=Condb)
		try:
			with conexion.cursor() as cursor:
				consulta = f"SELECT c.idcatedratico, c.nombre, c.apellido, c.correo, c.telefono, n.abreviatura from catedratico c inner join nivelacademico n on c.idnivelacademico = n.idnivelacademico where c.idcatedratico = {id}"
				cursor.execute(consulta)
			# Con fetchall traemos todas las filas
				catedratico = cursor.fetchone()
				consulta = f"SELECT c.nombre, c.horainicio, c.horafin, DATE_FORMAT(c.fechainicio,'%d/%m/%Y'), DATE_FORMAT(c.fechafin,'%d/%m/%Y'), a.codigo, c.dia, c.seccion, c.modalidad, c.formadepago, c.idclase from clase c inner join carrera a on a.idcarrera = c.idcarrera  where c.idcatedratico = {id} and LAST_DAY(c.fechafin)  >= CURDATE() order by c.horainicio"
				cursor.execute(consulta)
				clases = cursor.fetchall()
				clasesdias = []
				for i in range(7):
					consulta = f"SELECT count(dia) from clase where idcatedratico = {id} and dia = {i} and LAST_DAY(fechafin) >= CURDATE()"
					cursor.execute(consulta)
					num = cursor.fetchone()
					aux = []
					aux.append(i)
					aux.append(num[0])
					clasesdias.append(aux)
		finally:
			conexion.close()
	except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
		print("Ocurrió un error al conectar: ", e)
	id = int(id)
	id = str(id)
	number = id.rjust(4, '0')
	number = number + '01202346'
	barcode_format = barcode.get_barcode_class('upc')

	#Generate barcode and render as image
	my_barcode = barcode_format(number, writer=ImageWriter())

	#Save barcode as PNG
	aux = f"static/barcodes/{catedratico[1]}_{catedratico[2]}"
	my_barcode.save(aux)
	return render_template('periodoscat.html', title="Periodos por Catedrático", catedratico=catedratico, clases = clases, clasesdias = clasesdias, dias=dias)

@app.route('/periodoscatpdf/<id>', methods=['GET', 'POST'])
def periodoscatpdf(id):
	dias = [[0, "Lunes"], [1, "Martes"], [2, "Miercoles"], [3, "Jueves"], [4, "Viernes"], [5, "Sabado"], [6, "Domingo"]]
	try:
		conexion = pymysql.connect(host=Conhost, user=Conuser, password=Conpassword, db=Condb)
		try:
			with conexion.cursor() as cursor:
				consulta = f"SELECT c.idcatedratico, c.nombre, c.apellido, c.correo, c.telefono, n.abreviatura from catedratico c inner join nivelacademico n on c.idnivelacademico = n.idnivelacademico where c.idcatedratico = {id}"
				cursor.execute(consulta)
			# Con fetchall traemos todas las filas
				catedratico = cursor.fetchone()
				consulta = f"SELECT c.nombre, c.horainicio, c.horafin, DATE_FORMAT(c.fechainicio,'%d/%m/%Y'), DATE_FORMAT(c.fechafin,'%d/%m/%Y'), a.codigo, c.dia, c.seccion, c.modalidad, c.formadepago, c.idclase from clase c inner join carrera a on a.idcarrera = c.idcarrera  where c.idcatedratico = {id} and c.fechafin >= CURDATE() order by c.horainicio"
				cursor.execute(consulta)
				clases = cursor.fetchall()
				clasesdias = []
				for i in range(7):
					consulta = f"SELECT count(dia) from clase where idcatedratico = {id} and dia = {i} and fechafin >= CURDATE()"
					cursor.execute(consulta)
					num = cursor.fetchone()
					aux = []
					aux.append(i)
					aux.append(num[0])
					clasesdias.append(aux)
		finally:
			conexion.close()
	except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
		print("Ocurrió un error al conectar: ", e)
	html = render_template('periodoscatpdf.html', title="Horario Catedratico", catedratico=catedratico, clases = clases, clasesdias = clasesdias, dias=dias)
	return render_pdf(HTML(string=html))

@app.route('/nuevacarrera', methods=['GET', 'POST'])
def nuevacarrera():
	if request.method == 'POST':
		nombre = request.form["nombre"]
		codigo = request.form["codigo"]
		try:
			conexion = pymysql.connect(host=Conhost, user=Conuser, password=Conpassword, db=Condb)
			try:
				with conexion.cursor() as cursor:
					consulta = f"INSERT INTO carrera(nombre,codigo) VALUES ('{nombre}','{codigo}');"
					cursor.execute(consulta)
				conexion.commit()
			finally:
				conexion.close()
		except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
			print("Ocurrió un error al conectar: ", e)
		return redirect(url_for('periodos'))
	return render_template('nuevacarrera.html', title="Nueva Carrera")

@app.route('/registroperiodos', methods=['GET', 'POST'])
def registroperiodos():
	hoy = datetime.date.today()
	try:
		conexion = pymysql.connect(host=Conhost, user=Conuser, password=Conpassword, db=Condb)
		try:
			with conexion.cursor() as cursor:
				consulta = f"SELECT c.idcatedratico, c.nombre, c.apellido, n.abreviatura from catedratico c inner join nivelacademico n on c.idnivelacademico = n.idnivelacademico inner join clase l on l.idcatedratico = c.idcatedratico inner join periodos p on l.idclase = p.idclase where p.fecha <= '{hoy}' and p.idestado = 1 group by c.idcatedratico, c.nombre, c.apellido, n.abreviatura order by n.abreviatura, c.nombre;"
				cursor.execute(consulta)
			# Con fetchall traemos todas las filas
				catedraticos = cursor.fetchall()
		finally:
			conexion.close()
	except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
		print("Ocurrió un error al conectar: ", e)
	return render_template('registroperiodos.html', title="Registrar Periodos", catedraticos=catedraticos)

@app.route('/registroper/<id>', methods=['GET', 'POST'])
def registroper(id):
	hoy = datetime.date.today()
	meses = [[1, "Enero"], [2, "Febrero"], [3, "Marzo"], [4, "Abril"], [5, "Mayo"], [6, "Junio"], [7, "Julio"], [8, "Agosto"], [9, "Septiembre"], [10, "Octubre"], [11, "Noviembre"], [12, "Diciembre"]]
	try:
		conexion = pymysql.connect(host=Conhost, user=Conuser, password=Conpassword, db=Condb)
		try:
			with conexion.cursor() as cursor:
				consulta = f"SELECT c.idcatedratico, c.nombre, c.apellido, c.correo, c.telefono, n.abreviatura from catedratico c inner join nivelacademico n on c.idnivelacademico = n.idnivelacademico where c.idcatedratico = {id}"
				cursor.execute(consulta)
			# Con fetchall traemos todas las filas
				catedratico = cursor.fetchone()
				cursor.execute("SELECT idestado, estado from estado")
			# Con fetchall traemos todas las filas
				estados = cursor.fetchall()
				periodosmeses = []
				consulta = f"SELECT p.idperiodos from periodos p inner join clase c on c.idclase = p.idclase inner join catedratico a on a.idcatedratico = c.idcatedratico where p.idestado = 1 and c.idcatedratico = {id} and p.fecha <= '{hoy}'"
				cursor.execute(consulta)
				validar = cursor.fetchall()
				for i in range(12):
					consulta = f"SELECT count(fecha) from periodos p inner join clase c on p.idclase = c.idclase where c.idcatedratico = {id} and month(p.fecha) = {i+1} and p.idestado = 1 and p.fecha <= '{hoy}';"
					cursor.execute(consulta)
					num = cursor.fetchone()
					consulta = f"SELECT c.nombre, c.horainicio, c.horafin, a.codigo, DATE_FORMAT(p.fecha,'%d/%m/%Y'), p.idperiodos, p.idestado, c.seccion, c.modalidad from clase c inner join carrera a on a.idcarrera = c.idcarrera inner join periodos p on p.idclase = c.idclase where c.idcatedratico = {id} and p.idestado = 1 and p.fecha <= '{hoy}' and month(p.fecha) = {i+1} order by p.fecha, c.horainicio"
					cursor.execute(consulta)
					periodos = cursor.fetchall()
					aux = []
					aux.append(meses[i][1])
					aux.append(num[0])
					aux.append(periodos)
					periodosmeses.append(aux)
		finally:
			conexion.close()
	except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
		print("Ocurrió un error al conectar: ", e)
	id = int(id)
	id = str(id)
	number = id.rjust(4, '0')
	number = number + '01202346'
	barcode_format = barcode.get_barcode_class('upc')

	#Generate barcode and render as image
	my_barcode = barcode_format(number, writer=ImageWriter())

	#Save barcode as PNG
	aux = f"static/barcodes/{catedratico[1]}_{catedratico[2]}"
	my_barcode.save(aux)
	if request.method == 'POST':
		try:
			conexion = pymysql.connect(host=Conhost, user=Conuser, password=Conpassword, db=Condb)
			try:
				with conexion.cursor() as cursor:
					consulta = f"SELECT p.idperiodos from periodos p inner join clase c on c.idclase = p.idclase where p.idestado = 1 and p.fecha <= '{hoy}' and c.idcatedratico = {id}"
					cursor.execute(consulta)
					# Con fetchall traemos todas las filas
					periodos = cursor.fetchall()
					for i in periodos:
						aux = f"estado{i[0]}"
						estado = request.form[aux]
						aux = f"fecharegistro{i[0]}"
						fecharegistro = request.form[aux]
						consulta = f"UPDATE periodos set idestado = {estado}, fecharegistro = '{fecharegistro}' where idperiodos = {i[0]}"
						cursor.execute(consulta)
				conexion.commit()
			finally:
				conexion.close()
		except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
			print("Ocurrió un error al conectar: ", e)
		return redirect(url_for('registroperiodos'))
	return render_template('registroper.html', title="Periodos por Catedrático", catedratico=catedratico, periodosmeses = periodosmeses, meses=meses, estados=estados, validar=validar, hoy=hoy)

@app.route('/montofacturar', methods=['GET', 'POST'])
def montofacturar():
	try:
		conexion = pymysql.connect(host=Conhost, user=Conuser, password=Conpassword, db=Condb)
		try:
			with conexion.cursor() as cursor:
				consulta = "SELECT c.idcatedratico, c.nombre, c.apellido, n.abreviatura, p.formadepago from catedratico c inner join nivelacademico n on c.idnivelacademico = n.idnivelacademico inner join clase l on l.idcatedratico = c.idcatedratico inner join periodos p on l.idclase = p.idclase where p.idestado = 2 and p.liquidado = 0 and p.fecharegistro <= LAST_DAY(DATE_SUB(CURDATE(), INTERVAL 1 MONTH)) group by c.idcatedratico, c.nombre, c.apellido, n.abreviatura, p.formadepago order by n.abreviatura, c.nombre;"
				cursor.execute(consulta)
			# Con fetchall traemos todas las filas
				catedraticos = cursor.fetchall()
				cantidad = len(catedraticos)
				data = []
				for i in catedraticos:
					consulta = f"SELECT sum(p.precio) from periodos p inner join clase c on c.idclase = p.idclase where c.idcatedratico = {i[0]} and p.formadepago = '{i[4]}' and p.idestado = 2 and p.liquidado = 0 and p.fecharegistro <= LAST_DAY(DATE_SUB(CURDATE(), INTERVAL 2 MONTH));"
					cursor.execute(consulta)
					total = cursor.fetchone()
					consulta = f"SELECT sum(p.precio) from periodos p inner join clase c on c.idclase = p.idclase where c.idcatedratico = {i[0]} and p.formadepago = '{i[4]}' and p.idestado = 2 and p.liquidado = 0 and p.fecharegistro <= LAST_DAY(DATE_SUB(CURDATE(), INTERVAL 1 MONTH)) and p.fecharegistro > LAST_DAY(DATE_SUB(CURDATE(), INTERVAL 2 MONTH));"
					cursor.execute(consulta)
					print(consulta)
					totalmes = cursor.fetchone()
					try:
						totalmes = float(totalmes[0])
					except:
						totalmes = 0
					try:
						total = float(total[0])
					except:
						total = 0
					dataaux = [total, totalmes, total+totalmes]
					data.append(dataaux)
		finally:
			conexion.close()
	except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
		print("Ocurrió un error al conectar: ", e)
	return render_template('montofacturar.html', title="Montos a Facturar", catedraticos=catedraticos, data = data, cantidad = cantidad)

@app.route('/montofacturarpdf', methods=['GET', 'POST'])
def montofacturarpdf():
	try:
		conexion = pymysql.connect(host=Conhost, user=Conuser, password=Conpassword, db=Condb)
		try:
			with conexion.cursor() as cursor:
				consulta = "SELECT c.idcatedratico, c.nombre, c.apellido, n.abreviatura, p.formadepago from catedratico c inner join nivelacademico n on c.idnivelacademico = n.idnivelacademico inner join clase l on l.idcatedratico = c.idcatedratico inner join periodos p on l.idclase = p.idclase where p.idestado = 2 and p.liquidado = 0 and p.fecharegistro <= LAST_DAY(DATE_SUB(CURDATE(), INTERVAL 1 MONTH)) group by c.idcatedratico, c.nombre, c.apellido, n.abreviatura, p.formadepago order by n.abreviatura, c.nombre;"
				cursor.execute(consulta)
			# Con fetchall traemos todas las filas
				catedraticos = cursor.fetchall()
				cantidad = len(catedraticos)
				data = []
				for i in catedraticos:
					consulta = f"SELECT sum(p.precio) from periodos p inner join clase c on c.idclase = p.idclase where c.idcatedratico = {i[0]} and p.formadepago = '{i[4]}' and p.idestado = 2 and p.liquidado = 0 and p.fecharegistro <= LAST_DAY(DATE_SUB(CURDATE(), INTERVAL 2 MONTH));"
					cursor.execute(consulta)
					total = cursor.fetchone()
					consulta = f"SELECT sum(p.precio) from periodos p inner join clase c on c.idclase = p.idclase where c.idcatedratico = {i[0]} and p.formadepago = '{i[4]}' and p.idestado = 2 and p.liquidado = 0 and p.fecharegistro <= LAST_DAY(DATE_SUB(CURDATE(), INTERVAL 1 MONTH)) and p.fecharegistro > LAST_DAY(DATE_SUB(CURDATE(), INTERVAL 2 MONTH));"
					cursor.execute(consulta)
					print(consulta)
					totalmes = cursor.fetchone()
					try:
						totalmes = float(totalmes[0])
					except:
						totalmes = 0
					try:
						total = float(total[0])
					except:
						total = 0
					dataaux = [total, totalmes, total+totalmes]
					data.append(dataaux)
		finally:
			conexion.close()
	except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
		print("Ocurrió un error al conectar: ", e)
	html = render_template('montofacturarpdf.html', title="Montos a Facturar", catedraticos=catedraticos, data = data, cantidad = cantidad)
	return render_pdf(HTML(string=html))

@app.route('/montofacturarexcel', methods=['GET', 'POST'])
def montofacturarexcel():
	try:
		conexion = pymysql.connect(host=Conhost, user=Conuser, password=Conpassword, db=Condb)
		try:
			with conexion.cursor() as cursor:
				consulta = "SELECT c.idcatedratico, c.nombre, c.apellido, n.abreviatura, p.formadepago from catedratico c inner join nivelacademico n on c.idnivelacademico = n.idnivelacademico inner join clase l on l.idcatedratico = c.idcatedratico inner join periodos p on l.idclase = p.idclase where p.idestado = 2 and p.liquidado = 0 and p.fecharegistro <= LAST_DAY(DATE_SUB(CURDATE(), INTERVAL 1 MONTH)) group by c.idcatedratico, c.nombre, c.apellido, n.abreviatura, p.formadepago order by n.abreviatura, c.nombre;"
				cursor.execute(consulta)
			# Con fetchall traemos todas las filas
				catedraticos = cursor.fetchall()
				cantidad = len(catedraticos)
				data = []
				for i in catedraticos:
					consulta = f"SELECT sum(p.precio) from periodos p inner join clase c on c.idclase = p.idclase where c.idcatedratico = {i[0]} and p.formadepago = '{i[4]}' and p.idestado = 2 and p.liquidado = 0 and p.fecharegistro <= LAST_DAY(DATE_SUB(CURDATE(), INTERVAL 2 MONTH));"
					cursor.execute(consulta)
					total = cursor.fetchone()
					consulta = f"SELECT sum(p.precio) from periodos p inner join clase c on c.idclase = p.idclase where c.idcatedratico = {i[0]} and p.formadepago = '{i[4]}' and p.idestado = 2 and p.liquidado = 0 and p.fecharegistro <= LAST_DAY(DATE_SUB(CURDATE(), INTERVAL 1 MONTH)) and p.fecharegistro > LAST_DAY(DATE_SUB(CURDATE(), INTERVAL 2 MONTH));"
					cursor.execute(consulta)
					print(consulta)
					totalmes = cursor.fetchone()
					try:
						totalmes = float(totalmes[0])
					except:
						totalmes = 0
					try:
						total = float(total[0])
					except:
						total = 0
					dataaux = [total, totalmes, total+totalmes]
					data.append(dataaux)
		finally:
			conexion.close()
	except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
		print("Ocurrió un error al conectar: ", e)
	output = io.BytesIO()
	workbook = xlwt.Workbook()
	sh = workbook.add_sheet("Monto a Facturar")

	#bordes
	borders = xlwt.Borders()
	borders.left = 1
	borders.right = 1
	borders.top = 1
	borders.bottom = 1

	#encabezados
	header_font = xlwt.Font()
	header_font.name = 'Arial'
	header_font.bold = True
	header_style = xlwt.XFStyle()
	header_style.font = header_font
	header_style.borders = borders

	#contenido
	content_font = xlwt.Font()
	content_font.name = 'Arial'
	content_style = xlwt.XFStyle()
	content_style.font = content_font
	content_style.borders = borders

	#titulos
	tittle_font = xlwt.Font()
	tittle_font.name = 'Arial'
	tittle_font.bold = True
	tittle_font.italic = True
	tittle_font.height = 20*20
	tittle_style = xlwt.XFStyle()
	tittle_style.font = tittle_font



	sh.write(0,0,"Montos a Facturar", tittle_style)

	sh.write(3,0,"Grado Academico", header_style)
	sh.write(3,1,"Nombre", header_style)
	sh.write(3,2,"Apellido", header_style)
	sh.write(3,3,"Forma de Pago", header_style)
	sh.write(3,4,"Acumulado", header_style)
	sh.write(3,5,"Mes Actual", header_style)
	sh.write(3,6,"Total", header_style)

	for i in range(cantidad):
		sh.write(i+4,0,catedraticos[i][3], content_style)
		sh.write(i+4,1,catedraticos[i][1], content_style)
		sh.write(i+4,2,catedraticos[i][2], content_style)
		sh.write(i+4,3,catedraticos[i][4], content_style)
		sh.write(i+4,4,data[i][0], content_style)
		sh.write(i+4,5,data[i][1], content_style)
		sh.write(i+4,6,data[i][2], content_style)

	sh.col(0).width = 18 * 256
	sh.col(1).width = 24 * 256
	sh.col(2).width = 28 * 256
	sh.col(3).width = 28 * 256
	sh.col(4).width = 15 * 256
	sh.col(5).width = 15 * 256
	sh.col(6).width = 15 * 256

	workbook.save(output)
	output.seek(0)

	return Response(output, mimetype="application/ms-excel", headers={"Content-Disposition":"attachment;filename=Montos_Facturar.xls"})

@app.route('/montofact/<id>', methods=['GET', 'POST'])
def montofact(id):
	meses = [[1, "Enero"], [2, "Febrero"], [3, "Marzo"], [4, "Abril"], [5, "Mayo"], [6, "Junio"], [7, "Julio"], [8, "Agosto"], [9, "Septiembre"], [10, "Octubre"], [11, "Noviembre"], [12, "Diciembre"]]
	try:
		conexion = pymysql.connect(host=Conhost, user=Conuser, password=Conpassword, db=Condb)
		try:
			with conexion.cursor() as cursor:
				consulta = f"SELECT c.idcatedratico, c.nombre, c.apellido, c.correo, c.telefono, n.abreviatura from catedratico c inner join nivelacademico n on c.idnivelacademico = n.idnivelacademico where c.idcatedratico = {id}"
				cursor.execute(consulta)
			# Con fetchall traemos todas las filas
				catedratico = cursor.fetchone()
				consulta = f"SELECT year(p.fecharegistro) from periodos p inner join clase c on c.idclase = p.idclase where c.idcatedratico = {id} and p.idestado = 2 and p.liquidado = 0 group by year(p.fecharegistro) order by year(p.fecharegistro);"
				cursor.execute(consulta)
			# Con fetchall traemos todas las filas
				anios = cursor.fetchall()
				periodosmeses = []
				totales = 0
				for i in anios:
					for j in meses:
						consulta = f'SELECT count(fecha) from periodos p inner join clase c on p.idclase = c.idclase where p.idestado = 2 and p.liquidado = 0 and c.idcatedratico = {id} and year(p.fecharegistro) = {i[0]} and month(p.fecharegistro) = {j[0]};'
						cursor.execute(consulta)
						num = cursor.fetchone()
						consulta = f"SELECT c.nombre, c.horainicio, c.horafin, a.codigo, DATE_FORMAT(p.fecha,'%d/%m/%Y'), p.idperiodos, p.idestado, p.precio, c.seccion, DATE_FORMAT(p.fecharegistro,'%d/%m/%Y'), p.formadepago from clase c inner join carrera a on a.idcarrera = c.idcarrera inner join periodos p on p.idclase = c.idclase where p.idestado = 2 and p.liquidado = 0 and c.idcatedratico = {id} and year(p.fecharegistro) = {i[0]} and month(p.fecharegistro) = {j[0]} order by p.fecha;"
						cursor.execute(consulta)
						periodos = cursor.fetchall()
						total = 0
						for k in periodos:
							total = total + float(k[7])
						aux = []
						if int(num[0]) > 0:
							aux.append(i[0])
							aux.append(j)
							aux.append(num[0])
							aux.append(periodos)
							aux.append(total)
							periodosmeses.append(aux)
							totales = totales + total
		finally:
			conexion.close()
	except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
		print("Ocurrió un error al conectar: ", e)
	id = int(id)
	id = str(id)
	number = id.rjust(4, '0')
	number = number + '01202346'
	barcode_format = barcode.get_barcode_class('upc')

	#Generate barcode and render as image
	my_barcode = barcode_format(number, writer=ImageWriter())

	#Save barcode as PNG
	aux = f"static/barcodes/{catedratico[1]}_{catedratico[2]}"
	my_barcode.save(aux)
	if request.method == 'POST':
		for i in periodosmeses:
			try:
				conexion = pymysql.connect(host=Conhost, user=Conuser, password=Conpassword, db=Condb)
				try:
					with conexion.cursor() as cursor:
						aux = f'factura{i[0]}{i[1][0]}'
						auxfactura = request.form[aux]
						if len(auxfactura) > 0:
							for j in i[3]:
								consulta = f"UPDATE periodos set liquidado = 1, factura = '{auxfactura}' where idperiodos = {j[5]}"
								cursor.execute(consulta)
								conexion.commit()
						else:
							for j in i[3]:
								aux = 'facturai' + str(j[5])
								auxfacturai = request.form[aux]
								if len(auxfacturai) > 0:
									consulta = f"UPDATE periodos set liquidado = 1, factura = '{auxfacturai}' where idperiodos = {j[5]}"
									cursor.execute(consulta)
								conexion.commit()
						print(aux)
				finally:
					conexion.close()
			except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
				print("Ocurrió un error al conectar: ", e)
		return redirect(url_for('montofacturar'))
	return render_template('montofact.html', title="Monto a Facturar", catedratico=catedratico, periodosmeses = periodosmeses, meses=meses, totales = totales)

@app.route('/registrarcheque', methods=['GET', 'POST'])
def registrarcheque():
	try:
		conexion = pymysql.connect(host=Conhost, user=Conuser, password=Conpassword, db=Condb)
		try:
			with conexion.cursor() as cursor:
				consulta = "SELECT c.idcatedratico, c.nombre, c.apellido, n.abreviatura, sum(p.precio), p.factura, p.cheque from catedratico c inner join nivelacademico n on c.idnivelacademico = n.idnivelacademico inner join clase a on c.idcatedratico = a.idcatedratico inner join periodos p on a.idclase = p.idclase where p.factura != '0' and (p.cheque = '0' or p.cheque IS Null) group by p.factura, c.nombre, c.apellido, n.abreviatura order by n.abreviatura, c.nombre;"
				cursor.execute(consulta)
			# Con fetchall traemos todas las filas
				catedraticos = cursor.fetchall()
		finally:
			conexion.close()
	except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
		print("Ocurrió un error al conectar: ", e)
	if request.method == 'POST':
		try:
			conexion = pymysql.connect(host=Conhost, user=Conuser, password=Conpassword, db=Condb)
			try:
				with conexion.cursor() as cursor:
					for i in catedraticos:
						aux = str(i[0]) + str(i[5])
						cheque = request.form[aux]
						if len(cheque) <= 0:
							cheque = '0'
						consulta = "UPDATE periodos inner join clase on periodos.idclase = clase.idclase set cheque = %s where clase.idcatedratico = %s and periodos.factura = %s"
						cursor.execute(consulta, (cheque, i[0], i[5]))
				conexion.commit()
			finally:
				conexion.close()
		except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
			print("Ocurrió un error al conectar: ", e)
		return redirect(url_for('registrarcheque'))
	return render_template('registrarcheque.html', title="Registrar Cheques", catedraticos=catedraticos)

@app.route('/reportepdf/<id>', methods=['GET', 'POST'])
def reportepdf(id):
	meses = [[1, "Enero"], [2, "Febrero"], [3, "Marzo"], [4, "Abril"], [5, "Mayo"], [6, "Junio"], [7, "Julio"], [8, "Agosto"], [9, "Septiembre"], [10, "Octubre"], [11, "Noviembre"], [12, "Diciembre"]]
	today = datetime.datetime.today()
	anio = int(today.year)
	try:
		conexion = pymysql.connect(host=Conhost, user=Conuser, password=Conpassword, db=Condb)
		try:
			with conexion.cursor() as cursor:
				consulta = "SELECT c.idcatedratico, c.nombre, c.apellido, c.correo, c.telefono, n.abreviatura from catedratico c inner join nivelacademico n on c.idnivelacademico = n.idnivelacademico where c.idcatedratico = %s"
				cursor.execute(consulta, (id))
			# Con fetchall traemos todas las filas
				catedratico = cursor.fetchone()
				periodosmeses = []
				totales = 0
				for i in range(12):
					consulta = "SELECT count(fecha) from periodos p inner join clase c on p.idclase = c.idclase where p.idestado = 2 and p.liquidado = 0 and c.idcatedratico = %s and ((month(p.fecha) = %s and month(p.fecharegistro) = %s and year(p.fecha) = %s and year(p.fecharegistro) = %s) or (month(p.fecha) < %s and month(p.fecharegistro) = %s and day(p.fecharegistro) < 5 and year(p.fecha) = %s and year(p.fecharegistro) = %s) or (month(p.fecha) <> %s and year(p.fecha) < %s and month(p.fecharegistro) = %s and year(p.fecharegistro) = %s) or (month(p.fecha) < %s and year(p.fecha) = %s and month(p.fecharegistro) = %s and day(p.fecharegistro) >= 5 and year(p.fecharegistro) = %s));"
					cursor.execute(consulta, (id,i+1,i+1, anio, anio, i+1, i+2, anio, anio, i+1, anio, i+1, anio, i+1, anio, i+1, anio))
					num = cursor.fetchone()
					consulta = "SELECT c.nombre, c.horainicio, c.horafin, a.codigo, DATE_FORMAT(p.fecha,'%d/%m/%Y'), p.idperiodos, p.idestado, p.precio, c.seccion, DATE_FORMAT(p.fecharegistro,'%d/%m/%Y'), p.formadepago from clase c inner join carrera a on a.idcarrera = c.idcarrera inner join periodos p on p.idclase = c.idclase where c.idcatedratico = " + str(id) + " and p.idestado = 2 and p.liquidado = 0 and ((month(p.fecha) = " + str(i+1) + " and month(p.fecharegistro) = " + str(i+1) + " and year(p.fecha) = " + str(anio) + " and year(p.fecharegistro) = " + str(anio) + ") or (month(p.fecha) < " + str(i+1) + " and month(p.fecharegistro) = " + str(i+2) + " and day(p.fecharegistro) < 5 and year(p.fecha) = " + str(anio) + " and year(p.fecharegistro) = " + str(anio) + ") or (month(p.fecha) <> " + str(i+1) + " and year(p.fecha) < " + str(anio) + " and month(p.fecharegistro) = " + str(i+1) + " and year(p.fecharegistro) = " + str(anio) + ") or (month(p.fecha) < " + str(i+1) + " and year(p.fecha) = " + str(anio) + " and month(p.fecharegistro) = " + str(i+1) + " and day(p.fecharegistro) >= 5 and year(p.fecharegistro) = " + str(anio) + ")) order by p.fecha"
					print(consulta)
					cursor.execute(consulta)
					periodos = cursor.fetchall()
					total = 0
					for j in periodos:
						total = total + float(j[7])
					aux = []
					aux.append(i)
					aux.append(num[0])
					aux.append(periodos)
					aux.append(total)
					periodosmeses.append(aux)
					totales = totales + total
		finally:
			conexion.close()
	except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
		print("Ocurrió un error al conectar: ", e)
	html = render_template('reportepdf.html', title="Monto a Facturar", catedratico=catedratico, periodosmeses = periodosmeses, meses=meses, totales = totales)
	return render_pdf(HTML(string=html))

@app.route('/historico', methods=['GET', 'POST'])
def historico():
	try:
		conexion = pymysql.connect(host=Conhost, user=Conuser, password=Conpassword, db=Condb)
		try:
			with conexion.cursor() as cursor:
				cursor.execute("SELECT c.idcatedratico, c.nombre, c.apellido, n.abreviatura from catedratico c inner join nivelacademico n on c.idnivelacademico = n.idnivelacademico order by n.abreviatura, c.nombre;")
			# Con fetchall traemos todas las filas
				catedraticos = cursor.fetchall()
		finally:
			conexion.close()
	except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
		print("Ocurrió un error al conectar: ", e)
	return render_template('historico.html', title="Histórico", catedraticos=catedraticos)

@app.route('/catedraticohistorico/<id>', methods=['GET', 'POST'])
def catedraticohistorico(id):
	hoy = datetime.date.today()
	periodos = []
	desde = 0
	hasta = 0
	curso = ""
	try:
		conexion = pymysql.connect(host=Conhost, user=Conuser, password=Conpassword, db=Condb)
		try:
			with conexion.cursor() as cursor:
				consulta = "SELECT c.idcatedratico, c.nombre, c.apellido, c.correo, c.telefono, n.abreviatura from catedratico c inner join nivelacademico n on c.idnivelacademico = n.idnivelacademico where c.idcatedratico = %s"
			# Con fetchall traemos todas las filas
				cursor.execute(consulta, (id))
				catedratico = cursor.fetchone()
				consulta = "SELECT idestado, estado from estado"
				cursor.execute(consulta)
				estados = cursor.fetchall()
		finally:
			conexion.close()
	except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
		print("Ocurrió un error al conectar: ", e)
	id = int(id)
	id = str(id)
	number = id.rjust(4, '0')
	number = number + '01202346'
	barcode_format = barcode.get_barcode_class('upc')

	#Generate barcode and render as image
	my_barcode = barcode_format(number, writer=ImageWriter())

	#Save barcode as PNG
	aux = f"static/barcodes/{catedratico[1]}_{catedratico[2]}"
	my_barcode.save(aux)
	if request.method == 'POST':
		boton = request.form["varaux"]
		desde = request.form["desde"]
		hasta = request.form["hasta"]
		curso = request.form["curso"]
		if "fechas" in boton:
			try:
				conexion = pymysql.connect(host=Conhost, user=Conuser, password=Conpassword, db=Condb)
				try:
					with conexion.cursor() as cursor:
						consulta = f"""SELECT c.nombre, DATE_FORMAT(p.fecha,'%d/%m/%Y'), c.horainicio, c.horafin, a.codigo, c.seccion, p.precio, p.idestado, p.liquidado, p.factura, p.cheque, p.idperiodos, p.formadepago,DATE_FORMAT(p.fecharegistro,'%d/%m/%Y')
						from clase c inner join periodos p on c.idclase = p.idclase inner join carrera a on a.idcarrera = c.idcarrera inner join estado e on e.idestado = p.idestado
						where p.fecha >= '{desde}' and p.fecha <= '{hasta}'"""
						if len(curso) > 0:
							consulta = consulta + f" and c.nombre like '%{curso}%'"
						consulta = consulta + f" and c.idcatedratico = {id} order by p.fecha, c.horainicio asc"
						cursor.execute(consulta)
					# Con fetchall traemos todas las filas
						periodos = cursor.fetchall()
				finally:
					conexion.close()
			except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
				print("Ocurrió un error al conectar: ", e)
		else:
			try:
				conexion = pymysql.connect(host=Conhost, user=Conuser, password=Conpassword, db=Condb)
				try:
					with conexion.cursor() as cursor:
						consulta = f"""SELECT c.nombre, DATE_FORMAT(p.fecha,'%d/%m/%Y'), c.horainicio, c.horafin, a.codigo, c.seccion, p.precio, p.idestado, p.liquidado, p.factura, p.cheque, p.idperiodos, p.formadepago,DATE_FORMAT(p.fecharegistro,'%d/%m/%Y')
						from clase c inner join periodos p on c.idclase = p.idclase inner join carrera a on a.idcarrera = c.idcarrera inner join estado e on e.idestado = p.idestado
						where p.fecha >= '{desde}' and p.fecha <= '{hasta}'"""
						if len(curso) > 0:
							consulta = consulta + f" and c.nombre like '%{curso}%'"
						consulta = consulta + f" and c.idcatedratico = {id} order by p.fecha, c.horainicio asc"
						cursor.execute(consulta)
					# Con fetchall traemos todas las filas
						periodos = cursor.fetchall()
						for i in periodos:
							aux = 'periodo' + str(i[11])
							estadoaux = request.form[aux]
							consulta = f"UPDATE periodos set idestado = {estadoaux}, fecharegistro = '{hoy}' where idperiodos = {i[11]}"
							cursor.execute(consulta)
							conexion.commit()
						consulta = f"""SELECT c.nombre, DATE_FORMAT(p.fecha,'%d/%m/%Y'), c.horainicio, c.horafin, a.codigo, c.seccion, p.precio, p.idestado, p.liquidado, p.factura, p.cheque, p.idperiodos, p.formadepago,DATE_FORMAT(p.fecharegistro,'%d/%m/%Y')
						from clase c inner join periodos p on c.idclase = p.idclase inner join carrera a on a.idcarrera = c.idcarrera inner join estado e on e.idestado = p.idestado
						where p.fecha >= '{desde}' and p.fecha <= '{hasta}'"""
						if len(curso) > 0:
							consulta = consulta + f" and c.nombre like '%{curso}%'"
						consulta = consulta + f" and c.idcatedratico = {id} order by p.fecha, c.horainicio asc"
						cursor.execute(consulta)
					# Con fetchall traemos todas las filas
						periodos = cursor.fetchall()
				finally:
					conexion.close()
			except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
				print("Ocurrió un error al conectar: ", e)
	return render_template('catedraticohistorico.html', title="Histórico", periodos=periodos, catedratico = catedratico, desde = desde, hasta = hasta, estados = estados, curso = curso)

@app.route('/entradas', methods=['GET', 'POST'])
def entradas():
	entradas = []
	desde = 0
	hasta = 0
	catedratico = 0
	try:
		conexion = pymysql.connect(host=Conhost, user=Conuser, password=Conpassword, db=Condb)
		try:
			with conexion.cursor() as cursor:
				consulta = "SELECT c.idcatedratico, n.abreviatura, c.nombre, c.apellido from catedratico c inner join nivelacademico n on c.idnivelacademico = n.idnivelacademico order by n.abreviatura, c.nombre, c.apellido;"
			# Con fetchall traemos todas las filas
				cursor.execute(consulta)
				catedraticos = cursor.fetchall()
		finally:
			conexion.close()
	except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
		print("Ocurrió un error al conectar: ", e)
	if request.method == 'POST':
		desde = request.form["desde"]
		hasta = request.form["hasta"]
		catedratico = request.form["catedratico"]
		try:
			catedratico = int(catedratico)
			catedratico = str(catedratico)
		except:
			catedratico = ""
		try:
			conexion = pymysql.connect(host=Conhost, user=Conuser, password=Conpassword, db=Condb)
			try:
				with conexion.cursor() as cursor:
					consulta = "SELECT d.nombre, d.apellido, e.fecha, e.horaentrada, e.horasalida from catedratico d inner join entradas e on e.idcatedratico = d.idcatedratico "
					if len(desde) > 0 or len(hasta) > 0 or len(catedratico) > 0:
						consulta = consulta + "where "
						if len(catedratico) > 0:
							consulta = consulta + f"e.idcatedratico = {catedratico} "
						if len(desde) > 0:
							if len(catedratico) > 0:
								consulta = consulta + "and"
							consulta = consulta + f" e.fecha >= '{desde}' "
						if len(hasta) > 0:
							if len(catedratico) > 0 or len(desde) > 0:
								consulta = consulta + "and"
							consulta = consulta + f" e.fecha <= '{hasta}' "
					consulta = consulta + "order by e.fecha, d.nombre desc;"
					# Con fetchall traemos todas las filas
					cursor.execute(consulta)
					entradas = cursor.fetchall()
			finally:
				conexion.close()
		except (pymysql.err.OperationalError, pymysql.err.InternalError) as e:
			print("Ocurrió un error al conectar: ", e)

	return render_template('entradas.html', title="Entradas", entradas=entradas, desde = desde, hasta = hasta, catedratico = catedratico, catedraticos = catedraticos)

if __name__ == '__main__':
	app.run(host='0.0.0.0', port=5003, threaded=True, debug=True)