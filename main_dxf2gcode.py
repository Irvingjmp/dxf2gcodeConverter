# -*- coding: utf-8 -*-
"""
Created on Tue Nov 28 17:06:20 2023

@author: aaron VM AVM4ST3R
"""
import os
import ezdxf

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas


import numpy as np
import re
import math
from PyQt5 import QtWidgets,QtGui, uic
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtWidgets import QMessageBox

file_path = ""
file_name = ""
bounding_box = []
entidades = []
file_charged = False

class Ui(QtWidgets.QMainWindow):  
    def __init__(self):
        super(Ui, self).__init__()
        self.setWindowIcon(QtGui.QIcon('dxf2gcode_icon.png'))
        uic.loadUi("dxf2gcode.ui", self)  
        lineEdit_largo = self.findChild(QtWidgets.QLineEdit, 'largo')
        lineEdit_alto = self.findChild(QtWidgets.QLineEdit, 'Alto')
        lineEdit_sep_vert = self.findChild(QtWidgets.QLineEdit, 'sep_hor')
        lineEdit_sep_hor = self.findChild(QtWidgets.QLineEdit, 'sep_vert')
        # Establece el validador para que solo acepten números con decimales
        validator = QDoubleValidator()
        lineEdit_largo.setValidator(validator)
        lineEdit_alto.setValidator(validator)
        lineEdit_sep_vert.setValidator(validator)
        lineEdit_sep_hor.setValidator(validator)
        
        

        
        self.button = self.findChild(QtWidgets.QPushButton,'Cargar_Archivo') 
        self.button.clicked.connect(self.print_file_path)  # Conecta el botón a la función
        
        self.button = self.findChild(QtWidgets.QPushButton,'Convertir_Gcode') 
        self.button.clicked.connect(self.onclick_generate_gcode)  # Conecta el botón a la función onclick_generate_gcode
        
        
        self.show()
        

    def print_file_path(self):
        file_pathc, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Selecciona un archivo", "","Drawing Exchange Format (*.dxf)")
        if file_pathc:
            global file_path, file_name, file_charged, entidades, bounding_box
            file_path = os.path.dirname(file_pathc)

            file_name= os.path.basename(file_pathc)
        
            file_charged = True
            
            #print(f"La ruta del archivo seleccionado es: {file_path}")
            entidades, bounding_box = dibujar_entidades_dxf(self,file_pathc,"0")
            
    def onclick_generate_gcode(self):
        lineEdit_largo = self.findChild(QtWidgets.QLineEdit, 'largo')
        lineEdit_alto = self.findChild(QtWidgets.QLineEdit, 'Alto')
        lineEdit_sep_vert = self.findChild(QtWidgets.QLineEdit, 'sep_hor')
        lineEdit_sep_hor = self.findChild(QtWidgets.QLineEdit, 'sep_vert')
        contra_moldura = self.findChild(QtWidgets.QCheckBox, 'Contra_moldura')
        state = contra_moldura.isChecked()
        
        global file_charged, entidades, bounding_box, file_path, file_name

        if file_charged is False:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setText("Sin Archivo")
            msg.setInformativeText('Carga un archivo por favor')
            msg.setWindowTitle("Sin Archivo")
            msg.exec_()

        elif not lineEdit_largo.text() or not lineEdit_alto.text():
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setText("Error")
            msg.setInformativeText('Complete los campos de dimensiones de Bloque')
            msg.setWindowTitle("Error")
            msg.exec_()
            
        elif not lineEdit_sep_hor.text() or not lineEdit_sep_vert.text():
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Warning)
            msg.setText("Error")
            msg.setInformativeText('Complete los campos la separación Horizontal y Vertical')
            msg.setWindowTitle("Error")
            msg.exec_()               

        else:
            largo_bloque = int(lineEdit_largo.text())
            alto_bloque = int(lineEdit_alto.text())
            sep_vert = int(lineEdit_sep_vert.text())
            sep_hor = int(lineEdit_sep_hor.text())
            
            file_name_gcode = file_name.replace(".dxf", ".gcode")
            
            dxf_file_path = file_path + "/"+ file_name
            gcode_file_path = file_path + "/"+ file_name_gcode
            
            origins, vertices, filas = empaquetar_bounding_boxes(bounding_box ,separacion_horizontal = sep_hor, separacion_vertical = sep_vert, separacion_inicial_izquierda = sep_hor, separacion_inicial_inferior = sep_vert, ancho_area = largo_bloque , alto_area = alto_bloque)
            todas_las_entidades = dibujar_entidades_multiples(self, origins, entidades, vertices, largo_bloque,alto_bloque,state)
            create_dxf(todas_las_entidades,origins) 
            dxf2gcode(dxf_file_path, gcode_file_path, origins, vertices, filas, dist_ini_izq = sep_hor, dist_ini_inf = sep_vert, cortar_bounding_box = state)
 

    def limpiar_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.limpiar_layout(item.layout())
                
def dibujar_entidades_dxf(self, ruta_archivo, nombre_capa, mostrar_figura=True):
    """
    Dibuja las entidades (líneas y arcos) de una capa en un archivo DXF y devuelve la lista de entidades y el bounding box.
    """
    # Cargar el archivo DXF
    doc = ezdxf.readfile(ruta_archivo)

    if mostrar_figura:
        # Crear una figura y un eje en matplotlib
        fig, ax = plt.subplots()

    # Obtener todos los puntos dibujados para determinar el bounding box
    todos_los_puntos = []

    entidades = []

    # Función para agregar puntos a la lista de todos_los_puntos
    def agregar_puntos(coords):
        nonlocal todos_los_puntos
        todos_los_puntos.extend(coords)

    # Función para actualizar las coordenadas del bounding box
    def actualizar_bounding_box(x, y):
        nonlocal todos_los_puntos
        todos_los_puntos.append((x, y))

    # Función para dibujar una línea y actualizar el bounding box
    def dibujar_linea(linea):
        x_inicio, y_inicio = linea.dxf.start.x, linea.dxf.start.y
        x_fin, y_fin = linea.dxf.end.x, linea.dxf.end.y
        if mostrar_figura:
            ax.plot([x_inicio, x_fin], [y_inicio, y_fin], color='black')
        actualizar_bounding_box(round(x_inicio), round(y_inicio))
        actualizar_bounding_box(round(x_fin), round(y_fin))
        # Añadir la línea a la lista de entidades
        entidades.append(linea)

    # Función para dibujar un arco y actualizar la lista de puntos
    def dibujar_arco(arco):


        # Añadir el arco a la lista de entidades
        entidades.append(arco)


        x_centro, y_centro, _ = arco.dxf.center
        radius = arco.dxf.radius
        start_angle = np.radians(arco.dxf.start_angle)
        end_angle = np.radians(arco.dxf.end_angle)

        # Calcular el sentido del arco
        sentido_horario = start_angle > end_angle

        # Asegurarse de que los ángulos estén en el rango [0, 2*pi)
        start_angle = start_angle % (2 * np.pi)
        end_angle = end_angle % (2 * np.pi)

        # Calcular los puntos del arco
        if sentido_horario:
            arc_points = np.linspace(start_angle, end_angle + 2 * np.pi, num=100)
        else:
            arc_points = np.linspace(start_angle, end_angle, num=100)

        arc_coords = [(x_centro + radius * np.cos(theta), y_centro + radius * np.sin(theta)) for theta in arc_points]

        if mostrar_figura:
            ax.plot(*zip(*arc_coords), color='black')

        agregar_puntos(arc_coords)

    # Función para dibujar un círculo y actualizar la lista de puntos
    def dibujar_circulo(circulo):
        entidades.append(circulo)
        x_centro, y_centro, _ = circulo.dxf.center
        radius = circulo.dxf.radius

        # Calcular los puntos del círculo
        theta = np.linspace(0, 2 * np.pi, num=100)
        circle_coords = [(x_centro + radius * np.cos(t), y_centro + radius * np.sin(t)) for t in theta]

        if mostrar_figura:
            ax.plot(*zip(*circle_coords), color='black')
        agregar_puntos(circle_coords)




    # Dibujar líneas en la capa
    lineas = doc.modelspace().query(f'LINE[layer=="{nombre_capa}"]')
    for linea in lineas:
        dibujar_linea(linea)

    # Dibujar arcos en la capa
    arcos = doc.modelspace().query(f'ARC[layer=="{nombre_capa}"]')
    for arco in arcos:
        dibujar_arco(arco)

    # Dibujar círculos en la capa
    circulos = doc.modelspace().query(f'CIRCLE[layer=="{nombre_capa}"]')
    for circulo in circulos:
        dibujar_circulo(circulo)


    # Obtener los valores máximos y mínimos de las coordenadas
    todos_los_puntos = np.array(todos_los_puntos)
    min_x, min_y = np.min(todos_los_puntos, axis=0)
    max_x, max_y = np.max(todos_los_puntos, axis=0)

    # Ajustar el bounding box para que no tenga valores negativos
    min_x, min_y = max(0, min_x), max(0, min_y)

    # Crear el bounding box
    bounding_box = patches.Rectangle((min_x, min_y), round(max_x - min_x), round(max_y - min_y), linewidth=1, edgecolor='r', facecolor='none')
    if mostrar_figura:
        ax.add_patch(bounding_box)
        lado = max(round(max_x - min_x),round(max_y - min_y))
        ax.set_xlim(-2,lado+2)
        ax.set_ylim(-2,lado+2)
    # Mostrar la figura si se solicita
    #if mostrar_figura:
        #plt.show()
    
    self.limpiar_layout(self.dxf_preview)
    canvas = FigureCanvas(fig)
    self.dxf_preview.addWidget(canvas) # Agrega el canvas al QVBoxLayout

    # Devolver la lista de entidades y el bounding box
    return entidades, bounding_box

def dibujar_entidades(entidades, grados=0, bounding_box_color='red', desplazamiento_x=0, desplazamiento_y=0, mostrar_ejes=False, union=False, fig=None, ax=None):
    if fig is None:
      # Si no se proporcionó un conjunto de ejes, crear uno nuevo
      fig, ax = plt.subplots()
    # Calcular el ángulo de rotación en radianes
    angulo = np.radians(grados)

    # Inicializar las coordenadas mínimas y máximas
    min_x = float('inf')
    min_y = float('inf')
    max_x = float('-inf')
    max_y = float('-inf')

    # Inicializar la lista de entidades dibujadas
    entidades_dibujadas = []

    # Recorrer todas las entidades en la lista
    for entidad in entidades:
        # Si la entidad es una línea
        if entidad.dxftype() == 'LINE':
            # Calcular las nuevas coordenadas de inicio y fin después de la rotación y el desplazamiento
            x_inicio = (entidad.dxf.start[0] + desplazamiento_x)*np.cos(angulo) - (entidad.dxf.start[1] + desplazamiento_y)*np.sin(angulo)
            y_inicio = (entidad.dxf.start[0] + desplazamiento_x)*np.sin(angulo) + (entidad.dxf.start[1] + desplazamiento_y)*np.cos(angulo)
            x_fin = (entidad.dxf.end[0] + desplazamiento_x)*np.cos(angulo) - (entidad.dxf.end[1] + desplazamiento_y)*np.sin(angulo)
            y_fin = (entidad.dxf.end[0] + desplazamiento_x)*np.sin(angulo) + (entidad.dxf.end[1] + desplazamiento_y)*np.cos(angulo)
            # Dibujar la línea
            ax.plot([x_inicio, x_fin], [y_inicio, y_fin], color='black')
            # Actualizar las coordenadas mínimas y máximas
            min_x = min(min_x, x_inicio, x_fin)
            min_y = min(min_y, y_inicio, y_fin)
            max_x = max(max_x, x_inicio, x_fin)
            max_y = max(max_y, y_inicio, y_fin)
            # Añadir la entidad a la lista de entidades dibujadas
            entidades_dibujadas.append(entidad)
        # Si la entidad es un arco
        elif entidad.dxftype() == 'ARC':
            # Calcular las nuevas coordenadas del centro después de la rotación y el desplazamiento
            x_centro = (entidad.dxf.center[0] + desplazamiento_x)*np.cos(angulo) - (entidad.dxf.center[1] + desplazamiento_y)*np.sin(angulo)
            y_centro = (entidad.dxf.center[0] + desplazamiento_x)*np.sin(angulo) + (entidad.dxf.center[1] + desplazamiento_y)*np.cos(angulo)
            # Crear un objeto Arc
            arc_patch = patches.Arc((x_centro, y_centro), 2*entidad.dxf.radius, 2*entidad.dxf.radius, theta1=entidad.dxf.start_angle+grados, theta2=entidad.dxf.end_angle+grados)
            # Añadir el arco al gráfico
            ax.add_patch(arc_patch)
            # Actualizar las coordenadas mínimas y máximas
            min_x = min(min_x, x_centro - entidad.dxf.radius)
            min_y = min(min_y, y_centro - entidad.dxf.radius)
            max_x = max(max_x, x_centro + entidad.dxf.radius)
            max_y = max(max_y, y_centro + entidad.dxf.radius)
            # Añadir la entidad a la lista de entidades dibujadas
            entidades_dibujadas.append(entidad)

        # Si la entidad es un círculo
        elif entidad.dxftype() == 'CIRCLE':
            # Calcular las nuevas coordenadas del centro después de la rotación y el desplazamiento
            x_centro = (entidad.dxf.center[0] + desplazamiento_x)*np.cos(angulo) - (entidad.dxf.center[1] + desplazamiento_y)*np.sin(angulo)
            y_centro = (entidad.dxf.center[0] + desplazamiento_x)*np.sin(angulo) + (entidad.dxf.center[1] + desplazamiento_y)*np.cos(angulo)
            radius = entidad.dxf.radius
            # Crear un objeto Circle
            circle_patch = patches.Circle((x_centro, y_centro), radius, edgecolor='black', facecolor='none')
            # Añadir el círculo al gráfico
            ax.add_patch(circle_patch)
            # Ajustar los ejes para que todos los elementos sean visibles
            ax.autoscale_view()
            # Actualizar las coordenadas mínimas y máximas
            min_x = min(min_x, x_centro - entidad.dxf.radius)
            min_y = min(min_y, y_centro - entidad.dxf.radius)
            max_x = max(max_x, x_centro + entidad.dxf.radius)
            max_y = max(max_y, y_centro + entidad.dxf.radius)
            # Añadir la entidad a la lista de entidades dibujadas
            entidades_dibujadas.append(entidad)

    # Mostrar u ocultar los ejes
    if mostrar_ejes:
        ax.axis('on')
    else:
        ax.axis('off')

    if union is False:
      # Guardar la figura como una imagen
      plt.savefig("imagen.png", bbox_inches='tight', pad_inches=0)
      # Mostrar la gráfica
      plt.show()

    # Devolver la figura, los ejes y la lista de entidades dibujadas
    return fig, ax, entidades_dibujadas


def empaquetar_bounding_boxes(rectangulo_matplotlib, mostrar_resultado_Bounding_Boxes=False, separacion_horizontal=0, separacion_vertical=0, separacion_inicial_izquierda=0, separacion_inicial_inferior=0, ancho_area = 0, alto_area = 0):
    rectangulo = str(rectangulo_matplotlib)
    #print(rectangulo)
    # Extraer el ancho y alto del rectángulo de la cadena de texto
    match = re.search(r'width=(\d+), height=(\d+)', rectangulo)
    #print(match)
    ancho_rect = int(match.group(1))
    alto_rect = int(match.group(2))

    # Calcular cuántos rectángulos caben en el área
    num_rect_horizontal = (ancho_area - separacion_inicial_izquierda) // (ancho_rect + separacion_horizontal)
    num_rect_vertical = (alto_area - separacion_inicial_inferior) // (alto_rect + separacion_vertical)
    #print(num_rect_vertical)

    # Inicializar la lista de orígenes y la lista de vértices
    origenes = []
    vertices = []
    if mostrar_resultado_Bounding_Boxes:
      # Crear una figura y un eje en matplotlib
      fig, ax = plt.subplots(1)

    # Dibujar cada rectángulo en el área
    for i in range(num_rect_horizontal):
        for j in range(num_rect_vertical):
            # Crear un rectángulo (x, y, ancho, alto)
            x = separacion_inicial_izquierda + i*(ancho_rect+separacion_horizontal)
            y = separacion_inicial_inferior + j*(alto_rect+separacion_vertical)
            rect = patches.Rectangle((x, y), ancho_rect, alto_rect, linewidth=1, edgecolor='r', facecolor='none')

            if mostrar_resultado_Bounding_Boxes:
              # Añadir el rectángulo al gráfico
              ax.add_patch(rect)

            # Añadir el origen del rectángulo a la lista
            origenes.append((x, y))

            # Añadir los vértices del rectángulo a la lista
            vertices.append([(x, y), (x+ancho_rect, y), (x+ancho_rect, y+alto_rect), (x, y+alto_rect)])

    # Mostrar el gráfico si se solicita
    if mostrar_resultado_Bounding_Boxes:
        # Establecer los límites del gráfico
        plt.xlim(0, ancho_area)
        plt.ylim(0, alto_area)
        plt.show()

    # Devolver la lista de orígenes y la lista de vértices
    return origenes, vertices, num_rect_vertical




def convertir_y_agregar_clase(lista):
    # Convertir cada elemento a string
    lista_str = [str(elemento) for elemento in lista]

    # Agregar la clase correspondiente antes de cada string
    nueva_lista = []
    for elemento in lista_str:
        if 'LINE' in elemento:
            nueva_lista.append("<class 'ezdxf.entities.line.Line'> " + elemento)
        elif 'ARC' in elemento:
            nueva_lista.append("<class 'ezdxf.entities.arc.Arc'> " + elemento)
        elif 'CIRCLE' in elemento:
            nueva_lista.append("<class 'ezdxf.entities.circle.Circle'> " + elemento)


    return nueva_lista



def dibujar_entidades_multiples(self,origenes, entidades, vertices, ancho_bloque, alto_bloque, contra_moldura):
    # Crear una figura y un conjunto de ejes
    fig, ax = plt.subplots()

    # Inicializar la lista de todas las entidades
    todas_las_entidades = []

    # Recorrer todos los orígenes en la lista
    for i, j in origenes:
        # Llamar a la función dibujar_entidades() para cada origen
        fig, ax, entidades_dibujadas = dibujar_entidades(entidades, grados=0, bounding_box_color='red', desplazamiento_x=i, desplazamiento_y=j, mostrar_ejes=True, union=True, fig=fig, ax=ax)

        # Añadir las entidades dibujadas a la lista de todas las entidades
        todas_las_entidades.append(entidades_dibujadas)

    #Mostrar bounding_box, o contra moldura
    if contra_moldura: 
      for rectangulo in vertices:
        origen = rectangulo[0]
        ancho = rectangulo[1][0]-rectangulo[0][0]
        alto = rectangulo[2][1]-rectangulo[0][1]

        rect = patches.Rectangle(origen,ancho,alto, edgecolor='red', facecolor='none')
        ax.add_patch(rect)
    #Establcer el limite del bloque y dibujarlo 
    bloque = patches.Rectangle((0,0), ancho_bloque, alto_bloque, edgecolor='blue', facecolor='none')
    ax.add_patch(bloque)

    ax.set_xlim(-10, ancho_bloque + 10)
    ax.set_ylim(-10, alto_bloque + 10)
    
    #Limpiar el layout siempre antes de volver a graficar
    self.limpiar_layout(self.dxf2gcode_vizualizer)
    
    # Crear el canvas de Matplotlib y agregarlo al QVBoxLayout
    self.canvas = FigureCanvas(fig)
    self.dxf2gcode_vizualizer.addWidget(self.canvas) # Agrega el canvas al QVBoxLayout



    # Devolver la lista de todas las entidades
    return todas_las_entidades

def create_dxf(entities_list,origins):
    # Crear un nuevo documento DXF
    doc = ezdxf.new('R2010')

    # Obtener el espacio del modelo
    msp = doc.modelspace()

    i = 0
    # Iterar sobre la lista de entidades
    for entity_list in entities_list:
        for entity in entity_list:

            # Verificar el tipo de entidad y agregarla al espacio del modelo
            if isinstance(entity, ezdxf.entities.line.Line):
                #origins[i],entity.dxf.start
                init = origins[i] + entity.dxf.start
                fin = origins[i] + entity.dxf.end
                msp.add_line(init, fin)

            elif isinstance(entity, ezdxf.entities.arc.Arc):
                center = origins[i] + entity.dxf.center
                msp.add_arc(center, entity.dxf.radius, entity.dxf.start_angle, entity.dxf.end_angle)


        i = i+1



    doc.header['$INSUNITS'] = 4
    # Guardar el documento DXF
    global file_name, file_path
    file_name_output = file_name.replace(".dxf", "")
    output = file_path + "/" + file_name_output + "_empaquetado.dxf"
    doc.saveas(output)

def dxf2gcode(dxf_path, gcode_path, origenes, vertices, filas ,dist_ini_izq = 10, dist_ini_inf = 10,cortar_bounding_box = False, separacion_corte_bounding_box = 0, R = 850):
    doc = ezdxf.readfile(dxf_path)
    noultimo = True
    

    with open(gcode_path, 'w') as gcode_file:
        cont = 0

        def escribir_vertices(cont,separacion):
            gcode_file.write(f"G01 X{vertices[cont][0][0] -   separacion} Y{vertices[cont][0][1] -   separacion} F{R}.\n")
            gcode_file.write(f"G01 X{vertices[cont][1][0] +   separacion} Y{vertices[cont][1][1] -   separacion} F{R}.\n")
            gcode_file.write(f"G01 X{vertices[cont][2][0] +   separacion} Y{vertices[cont][2][1] +   separacion} F{R}.\n")
            gcode_file.write(f"G01 X{vertices[cont][3][0] -   separacion} Y{vertices[cont][3][1] +   separacion} F{R}.\n")
            gcode_file.write(f"G01 X{vertices[cont][0][0] -   separacion} Y{vertices[cont][0][1] -   separacion} F{R}.\n")

        for i, origen in enumerate(origenes):
            gcode_file.write(f"G01 X{origen[0]} Y{origen[1]} F{R}.\n")

            for entity in doc.modelspace().query('*'):
                if entity.dxftype() == 'LINE':
                    start_point = entity.dxf.start
                    end_point = entity.dxf.end
                    gcode_file.write(f"G01 X{start_point.x + origen[0]} Y{start_point.y + origen[1]} F{R}.\n")
                    gcode_file.write(f"G01 X{end_point.x + origen[0]} Y{end_point.y + origen[1]} F{R}.\n")

                elif entity.dxftype() == 'CIRCLE':
                    center = entity.dxf.center
                    radius = entity.dxf.radius

                    for i in range(51):  # Genera 101 puntos para incluir el punto de inicio y el de finalización
                        angle = math.radians(180 + i * 360 / 50)  # Comienza en 180 grados y hace una rotación completa
                        x = center.x + radius * math.cos(angle) + origen[0]
                        y = center.y + radius * math.sin(angle) + origen[1]
                        gcode_file.write(f"G01 X{x} Y{y} F{R}. \n")


                elif entity.dxftype() == 'ARC':
                    center = entity.dxf.center
                    radius = entity.dxf.radius
                    start_angle = entity.dxf.start_angle
                    end_angle = entity.dxf.end_angle
                    sentido_horario = False

                    if start_angle <= 180 and start_angle > end_angle:
                        start_angle, end_angle = end_angle, start_angle
                        sentido_horario = False
                    elif start_angle > 180 and start_angle < end_angle:
                        start_angle, end_angle = end_angle, start_angle
                        sentido_horario = False
                    elif start_angle > 180 and start_angle > end_angle and end_angle <= 180:
                        start_angle, end_angle = end_angle, start_angle
                        sentido_horario = True

                    for i in range(51):
                        if sentido_horario:
                            grados = start_angle - (end_angle - start_angle) * i / 50
                            writer = True
                            if grados <= 0:
                                grados = grados+360
                                if grados <= end_angle:
                                    grados =  end_angle
                                    writer = False
                        else:
                            grados = start_angle + (end_angle - start_angle) * i / 50
                            writer = True
                        angle = math.radians(grados)
                        x = center.x + radius * math.cos(angle) + origen[0]
                        y = center.y + radius * math.sin(angle) + origen[1]
                        if writer:
                            gcode_file.write(f"G01 X{x} Y{y} F{R}.\n")


            gcode_file.write(f"G01 X{origen[0]} Y{origen[1]} F{R}.\n")



            if cont < len(origenes) - 1:
              xord = origen[0] - (dist_ini_izq/2)
              yord = origenes[cont+1][1]

            elif cont == len(origenes)-1:
              xord = origen[0] - (dist_ini_izq/2)
              yord = 0

              if cortar_bounding_box:
                escribir_vertices(cont,separacion_corte_bounding_box)

              gcode_file.write(f"G01 X{xord} Y{origen[1]} F{R}.\n")
              gcode_file.write(f"G01 X{xord} Y{yord} F{R}.\n")
              gcode_file.write(f"G01 X{0} Y{0} F{R}.\n")
              noultimo = False

            else:
              xord = origen[0]
              yord = origen[1]



            if noultimo:
              if cortar_bounding_box:
                escribir_vertices(cont,separacion_corte_bounding_box)
              if ((cont + 1) % filas == 0 and cont != 0) or (filas == 1 and cont == 0):
                #print(cont)
                xord = origen[0] - (dist_ini_izq/2)
                yord = origenes[cont+1][1] - (dist_ini_inf/2)
                gcode_file.write(f"G01 X{xord} Y{origen[1]} F{R}.\n")
                gcode_file.write(f"G01 X{xord} Y{yord} F{R}.\n")
                xord = origenes[cont+1][0]
                gcode_file.write(f"G01 X{xord} Y{yord} F{R}.\n")
                #print(xord, yord)
              else:
                gcode_file.write(f"G01 X{xord} Y{origen[1]} F{R}.\n")
                gcode_file.write(f"G01 X{xord} Y{yord} F{R}.\n")

            cont += 1

def main():
    app = QtWidgets.QApplication([])
    window = Ui()
    app.exec()
    


if __name__ == "__main__":
    main()
