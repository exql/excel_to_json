from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import authenticate, login
import os
import pandas as pd
import io
import json
from datetime import datetime, timedelta
from django.views.decorators.csrf import csrf_exempt
from tempfile import NamedTemporaryFile
from django.db import connection
from excel.models import PerfilUsuario
import pdfplumber
import re
from django.utils import timezone
from .models import RegistroExcel, DatosLab


# Se conecta a la Base de datos y trae los datos de la vista laboratorio_codigo_ensayos que contiene el codigo del rubro
# y su respectivo analito, matríz y técnica.

def rubros_lab(request):
    perfil = PerfilUsuario.objects.select_related("datos_lab").get(usuario=request.user)
    laboratorio_id = perfil.datos_lab.id

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                laboratorio_id,
                Nro_laboratorio,
                codigoEnsayo,
                ensayo_id,
                codigoAnalito,
                codigoMatriz,
                codigoTecnica
            FROM vista_laboratorio_codigo_ensayos
            WHERE laboratorio_id = %s
        """, [laboratorio_id])

        columns = [col[0] for col in cursor.description]
        results = cursor.fetchall()

    rubrosLab = pd.DataFrame(results, columns=columns)

    print(rubrosLab)  # Solo para pruebas temporales en consola

    return rubrosLab

# Da formato fecha a los datos de las actas digitales para generar la plantila del acta digital.
def formatear_fecha_actas(fecha):
    if pd.isna(fecha):  # Si el valor es NaN, lo dejamos como está
        return None
    try:
        return pd.to_datetime(fecha).date()  # devuelve solo la fecha (sin hora)
    except Exception:
        return None


########## probando un nuevo formato fecha

def formatear_fecha(fecha):
    if pd.isna(fecha):
        return None

    # Si ya es datetime, lo formateamos directo
    if isinstance(fecha, datetime):
        return fecha.strftime("%d/%m/%Y %H:%M")

    # Si viene como número (serial de Excel)
    if isinstance(fecha, (int, float)):
        base_date = datetime(1899, 12, 30)
        fecha_convertida = base_date + timedelta(days=float(fecha))
        return fecha_convertida.strftime("%d/%m/%Y %H:%M")

    # Si viene como string, intentamos parsear con varios formatos
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            fecha_convertida = datetime.strptime(str(fecha), fmt)
            return fecha_convertida.strftime("%d/%m/%Y %H:%M")
        except ValueError:
            continue

    return str(fecha)





# Registro de analisis

def registrar_excel_aie(request, excel):
    # Obtener datos del laboratorio
    datolab = codigoRubro(request)
    laboratorio_id = int(datolab["laboratorio_id"].iloc[0])
    laboratorio = DatosLab.objects.filter(id=laboratorio_id).first()

    if not laboratorio:
        raise ValueError(f"Laboratorio con id {laboratorio_id} no encontrado")

    # Filtrar columnas relevantes
    excel_aie = excel[[
        "Nro Informe", "RENSPA", "SubMotivo", "CUIT Funcionario",
        "Fecha de Toma", "Fecha de Recepcion", "Cantidad Muestras",
        "Rubro", "Fecha Inicio", "Fecha Fin", "Resultado Letra",
        "Identificacion Muestra", "Identificacion Interna Laboratorio", "Tipo Identificacion",
        "Categoria", "Sexo", "Antigeno/Kit", "Marca Antigeno/Kit", "Lote",
        "Fecha Vencimiento Antigeno/Kit", "Estampilla"
    ]]

    # Agrupar por Nro Informe y Rubro
    excel_aie = excel_aie.groupby(['Nro Informe', 'Rubro']).agg(
        lambda x: ', '.join(pd.unique(x.astype(str)))
    ).reset_index()

    # Obtener usuario y horario
    usuario = request.user if request.user.is_authenticated else None
    horario_sesion = timezone.now()
    print(f"Horario de la Sesion: {horario_sesion.strftime("%d/%m/%Y %H:%M:%S")}")



    registros = []
    for _, row in excel_aie.iterrows():
        # Conversión de fechas (si existen)
        def parse_fecha(valor):
            if pd.isna(valor) or valor is None or valor == "":
                return None
            try:
                return pd.to_datetime(valor).date()
            except Exception:
                return None

        registros.append(RegistroExcel(
            usuario=usuario,
            laboratorio=laboratorio,
            numlab=laboratorio.numLab,
            horario_sesion=horario_sesion,

            nro_informe=row["Nro Informe"],
            renspa=row.get("RENSPA"),
            submotivo=row.get("SubMotivo"),
            fecha_toma=parse_fecha(row.get("Fecha de Toma")),
            fecha_recepcion=parse_fecha(row.get("Fecha de Recepcion")),
            cantidad_muestras=row.get("Cantidad Muestras"),
            unidad_medida=row.get("Unidad de Medida"),
            rubro=row["Rubro"],
            fecha_inicio=parse_fecha(row.get("Fecha Inicio")),
            fecha_fin=parse_fecha(row.get("Fecha Fin")),
            resultado_letra=row.get("Resultado Letra"),
            identificacion_muestra=row.get("Identificacion Muestra"),
            identificacion_interna_lab=row.get("Identificacion Interna Laboratorio"),
            tipo_identificacion=row.get("Tipo Identificacion"),
            categoria=row.get("Categoria"),
            sexo=row.get("Sexo"),
            antigeno_kit=row.get("Antigeno/Kit"),
            marca_antigeno_kit=row.get("Marca Antigeno/Kit"),
            lote=row.get("Lote"),
            fecha_vencimiento_antigeno_kit=parse_fecha(row.get("Fecha Vencimiento Antigeno/Kit")),
            estampilla=row.get("Estampilla"),
        ))

    # Inserción en bloques para Excel grandes
    batch_size = 1000
    for i in range(0, len(registros), batch_size):
        RegistroExcel.objects.bulk_create(registros[i:i+batch_size])




#convertir_AIE

    
# Agrupar solo las columnas generales, evitando afectar las submuestras
def agrupar_por_numero_informe_aie(plantilla):
    columnas_a_agrupar = [
        "Nro Informe", "RENSPA", "SubMotivo", "CUIT Funcionario", "Fecha de Toma", "Fecha de Recepcion", "Cantidad Muestras", 
        "Unidad de Medida", "Rubro", "Fecha Inicio", "Fecha Fin", "Codigo DT", "Observacion del Protocolo", "Conclusion Protocolo"
    ]
    return plantilla.groupby("Nro Informe", as_index=False)[columnas_a_agrupar].first()

# Procesar las submuestras correctamente
def procesar_submuestras(df):
    submuestras = []
    
    # Iterar sobre cada fila del DataFrame y descomponer los valores correctamente
    for _, row in df.iterrows():
    
        identificaciones = row.get("Identificacion Muestra", "").split(', ')
        identificaciones_internas = str(row["Identificacion Interna Laboratorio"]).split(', ') if pd.notna(row["Identificacion Interna Laboratorio"]) else ['-']
        categorias = str(row.get("Categoria", "")).split(', ')
        sexos = str(row.get("Sexo", "")).split(', ')
        antigenos = str(row.get("Antigeno/Kit", "")).split(', ')
        marcas = str(row.get("Marca Antigeno/Kit", "")).split(', ')
        lotes = str(row.get("Lote", "")).split(', ')
        estampillas = str(row.get("Estampilla", "")).split(', ')
        observaciones = str(row["Observacion Muestra"]).split(', ') if pd.notna(row["Observacion Muestra"]) else ['']

        num_submuestras = len(identificaciones)

        # Asegurar que todas las listas tengan la misma longitud
        identificaciones_internas += [''] * (num_submuestras - len(identificaciones_internas))
        categorias += [''] * (num_submuestras - len(categorias))
        sexos += [''] * (num_submuestras - len(sexos))
        antigenos += [''] * (num_submuestras - len(antigenos))
        marcas += [''] * (num_submuestras - len(marcas))
        lotes += [''] * (num_submuestras - len(lotes))
        estampillas += [''] * (num_submuestras - len(estampillas))
        observaciones += [''] * (num_submuestras - len(observaciones))

        # Construir cada submuestra individualmente
        for i in range(num_submuestras):
            submuestras.append({
                "codigoResultadoLetra": row["Resultado Letra"],
                "identificacion": identificaciones[i],
                "identificacionInternaDeLaboratorio": identificaciones_internas[i],
                "codigoTipoIdentificacion": row["Tipo Identificacion"],
                "observacion": observaciones[i],
                "codigoDeCategoria": int(categorias[i]) if categorias[i].strip() else 0,
                "sexo": sexos[i],
                "antigeno": antigenos[i],
                "marcaDeAntigeno": marcas[i],
                "lote": lotes[i],
                "fechaDeVencimientoDeAnalisis": row["Fecha Vencimiento Antigeno/Kit"],
                "estampilla": estampillas[i]
            })

    return submuestras

# Construcción del JSON final
def construir_json_aie(row,rubrosLab):
    codigoRubro= row['Rubro']
    datosRubros= rubrosLab[rubrosLab['codigoEnsayo']== codigoRubro]

    if datosRubros.empty:
        datosRubros = pd.Series({
            'codigoAnalito': None,
            'codigoMatriz': None,
            'codigoTecnica': None,
            'Nro_laboratorio': None
        })
    else:
        datosRubros = datosRubros.iloc[0]

    observacion = (
        str(row.get("Observacion del Protocolo"))
        if pd.notna(row.get("Observacion del Protocolo")) else "--"
    )
    conclusion_protocolo = (
        str(row.get("Conclusion Protocolo"))
        if pd.notna(row.get("Conclusion Protocolo")) else "--"
    )

    return {
        'numeroInforme': row['Nro Informe'],
        'codigoLaboratorio': datosRubros['Nro_laboratorio'],
        'renspaUnidadProductiva': row['RENSPA'],
        'codigoMotivo': 463,
        'codigoSubMotivo': row['SubMotivo'],
        'codigotipoDocumentoUno': 21,
        'numeroDocumentoUno': row['Nro Informe'],
        'cuitDeFuncionario': row['CUIT Funcionario'],
        'muestra': {
            'fechaDeToma': row['Fecha de Toma'],
            'fechaDeRecepcion': row['Fecha de Recepcion'],
            'codigoDeProducto': "E17",
            'cantidadDeLote': row['Cantidad Muestras'],
            'codigoUnidadDeMedidaDeLote': row['Unidad de Medida'],
            'analisis': [
                {
                    
                    'codigoEnsayo': row['Rubro'],
                    'resultadoUnico': 'False',
                    'fechaInicio': row['Fecha Inicio'],
                    'fechaFin': row['Fecha Fin'],
                    'subMuestras': row["subMuestras"]
                }
            ],
            'codigoDirectorTecnico': row['Codigo DT'],
            'observaciones': observacion, #row['Observacion del Protocolo'],
            "conclusionTramite": conclusion_protocolo, #'--',
        },
        'codigoTipoDeTramite': "3"
    }



# Convertir_Bru
# Función para generar análisis agrupados por Rubro con 'id': 1

# Agrupar solo las columnas generales, evitando afectar las submuestras
def agrupar_por_numero_informe_bru(plantilla):
    columnas_a_agrupar = [
        "Nro Informe", "RENSPA", "Motivo", "SubMotivo", "CUIT Funcionario", "Fecha de Toma", "Fecha de Recepcion", "Especie", "Cantidad Muestras", 
        "Unidad de Medida", "Rubro", "Fecha Inicio", "Fecha Fin", "Codigo DT", "Observacion del Protocolo", "Conclusion Protocolo"
    ]
    return plantilla.groupby("Nro Informe", as_index=False)[columnas_a_agrupar].first()

def generar_analisis_bru(df,rubrosLab):
    analisis_agrupados = {}

    for nro_informe, sub_df in df.groupby("Nro Informe"):
        analisis_agrupados[nro_informe] = []

        for codigo_ensayo, grupo in sub_df.groupby("Rubro"):  # Agrupar por códigoEnsayo
            
            datosRubros= rubrosLab[rubrosLab['codigoEnsayo']== codigo_ensayo]
            if datosRubros.empty:
                datosRubros = pd.Series({
                    'codigoAnalito': None,
                    'codigoMatriz': None,
                    'codigoTecnica': None,
                    'Nro_laboratorio': None
                    })
            else: datosRubros = datosRubros.iloc[0]
                      
            analisis_agrupados[nro_informe].append({
                
                "codigoEnsayo": int(codigo_ensayo),
                #"codigoAnalito": int(datosRubros['codigoAnalito']),  # Asociado correctamente al ensayo
                #"codigoMatriz": int(datosRubros['codigoMatriz']),
                #"codigoTecnica": int(datosRubros['codigoTecnica']),  # Cada ensayo tiene su técnica correcta
                "resultadoUnico": False,
                "fechaInicio": grupo["Fecha Inicio"].iloc[0],
                "fechaFin": grupo["Fecha Fin"].iloc[0],
                "subMuestras": procesar_submuestras_bru(grupo)  # Ahora toma solo las submuestras correctas
            })

    return analisis_agrupados


# Función para procesar submuestras de Brucelosis
def procesar_submuestras_bru(df):
    submuestras = []
    for _, row in df.iterrows():
        identificaciones = row["Identificacion Muestra"].split(', ')
        identificaciones_internas = str(row["Identificacion Interna Laboratorio"]).split(', ') if pd.notna(row["Identificacion Interna Laboratorio"]) else ['-']
        
        # Convertir 'Categoria' a string antes de hacer split()
        categorias = str(row["Categoria"]).split(', ') if "Categoria" in row and pd.notna(row["Categoria"]) else ['-']
        
        sexos = row["Sexo"].split(', ')
        antigenos = row["Antigeno/Kit"].split(', ')
        marcas = row["Marca Antigeno/Kit"].split(', ')
        lotes = row["Lote"].split(', ')
        estampillas = row["Estampilla"].split(', ')
        observaciones = str(row["Observacion Muestra"]).split(', ') if pd.notna(row["Observacion Muestra"]) else ['']

        num_submuestras = len(identificaciones)

        identificaciones_internas += [''] * (num_submuestras - len(identificaciones_internas))
        categorias += [''] * (num_submuestras - len(categorias))
        sexos += [''] * (num_submuestras - len(sexos))
        antigenos += [''] * (num_submuestras - len(antigenos))
        marcas += [''] * (num_submuestras - len(marcas))
        lotes += [''] * (num_submuestras - len(lotes))
        estampillas += [''] * (num_submuestras - len(estampillas))
        observaciones += [''] * (num_submuestras - len(observaciones))

        for i in range(num_submuestras):
            submuestras.append({
                "codigoResultadoLetra": int(row["Resultado Letra"]),
                "identificacion": identificaciones[i],
                "identificacionInternaDeLaboratorio": identificaciones_internas[i],
                "codigoTipoIdentificacion": int(row["Tipo Identificacion"]),
                "observacion": observaciones[i],
                "codigoDeCategoria": int(categorias[i]) if categorias[i].strip() else 0,
                "sexo": sexos[i],
                "antigeno": antigenos[i],
                "marcaDeAntigeno": marcas[i],
                "lote": lotes[i],
                "fechaDeVencimientoDeAnalisis": row["Fecha Vencimiento Antigeno/Kit"],
                "estampilla": estampillas[i]
            })

    return submuestras


# Función para construir el JSON final por fila
def construir_json_bru(row, codigoLaboratorio):

    observacion = (
        str(row.get("Observacion del Protocolo"))
        if pd.notna(row.get("Observacion del Protocolo")) else "--"
    )
    conclusion_protocolo = (
        str(row.get("Conclusion Protocolo"))
        if pd.notna(row.get("Conclusion Protocolo")) else "--"
    )
    
    return {
        "numeroInforme": row["Nro Informe"],
        "codigoLaboratorio": str(codigoLaboratorio),
        "renspaUnidadProductiva": row["RENSPA"],
        "codigoMotivo": row["Motivo"],
        "codigoSubMotivo": row["SubMotivo"],
        "codigotipoDocumentoUno": 21,
        "numeroDocumentoUno": row["Nro Informe"],
        "cuitDeFuncionario": row["CUIT Funcionario"],
        "muestra": {
            "fechaDeToma": row["Fecha de Toma"],
            "fechaDeRecepcion": row["Fecha de Recepcion"],
            "codigoDeProducto": row["Especie"],
            "cantidadDeLote": row["Cantidad Muestras"],
            "codigoUnidadDeMedidaDeLote": row["Unidad de Medida"],
            "analisis": row["analisis"],
            "codigoDirectorTecnico": row["Codigo DT"],
            "observaciones": observacion,    #row["Observacion del Protocolo"],
            "conclusionTramite": conclusion_protocolo, #'--',

        },
        "codigoTipoDeTramite": 3
    }


# Convertir Triqui 

def agrupar_por_informe_Triqui(plantilla):
    columnas_a_agrupar = [
        "Nro Informe", "Nro Laboratorio", "Establecimiento", "Nro Documento", "CUIT Funcionario",'Unidad de Medida de la Cantidad',
        "Cantidad Animales", "Numero Tropa", "Fecha de Toma", "Fecha de Recepcion",
        "Tamaño Muestra", "Cantidad de Muestra", "Rubro",
        "Fecha Inicio", "Fecha conclusion", "Codigo DT", "Observacion del Protocolo", "Conclusion Protocolo"
    ]
    return plantilla.groupby(["Nro Informe"], as_index=False)[columnas_a_agrupar].first()


def procesar_submuestras_triqui(df):
    submuestras = []
    for _, row in df.iterrows():
        identificaciones = str(row.get("Identificacion Muestra", "-")).split(', ') if pd.notna(row.get("Identificacion Muestra")) else '-'
        observaciones = str(row.get("Observacion Muestra", "")).split(', ')
        limiteDeteccion = str(row.get("Limite Deteccion", "")).split(', ') if pd.notna(row.get("Limite Deteccion")) else [None]
        resultado_valores = str(row.get("Resultado Número", "")).split(', ') if pd.notna(row.get("Resultado Número")) else [None]

        num_submuestras = len(identificaciones)
        observaciones += [''] * (num_submuestras - len(observaciones))
        limiteDeteccion += [''] * (num_submuestras - len(limiteDeteccion))

        for i in range(num_submuestras):
            submuestras.append({
                "valorComunicacionSenasa": None,
                "limiteDeteccion": limiteDeteccion[i],
                "rec": None,
                "incertidumbre": None,
                "resultadoNumero": resultado_valores[i],
                "codigoUnidadDeMedida": 174,
                "codigoResultadoLetra": row.get("Resultado Letra"),
                "identificacion": identificaciones[i],
                "identificacionInternaDeLaboratorio": None,
                "codigoTipoIdentificacion": None,
                "observacion": observaciones[i],
                "codigoDeEdad": None,
                "codigoDeCategoria": None,
                "sexo": None,
                "fechaDeVacunacion": None,
                "antigeno": None,
                "marcaDeAntigeno": None,
                "lote": None,
                "fechaDeVencimientoDeAnalisis": None,
                "codigoDatoAdicional": None,
                "estampilla": None
            })
    return submuestras

def construir_json_triqui(row):
   
    observacion = (
        str(row.get("Observacion del Protocolo"))
        if pd.notna(row.get("Observacion del Protocolo")) else "--"
    )
    conclusion_protocolo = (
        str(row.get("Conclusion Protocolo"))
        if pd.notna(row.get("Conclusion Protocolo")) else "--"
    )

    return {
        'numeroInforme': row['Nro Informe'],
        "fechaCarga": None,
        "fechaEmision": None,
        'codigoLaboratorio': row['Nro Laboratorio'],
        'renspaUnidadProductiva': row.get('RENSPA'),
        "nroOficialEstablecimiento": int(row["Establecimiento"]) if pd.notna(row['Establecimiento']) else None,
        "numTipoEstablecimiento": 7073,
        'codigoMotivo': 1081,
        'codigoSubMotivo': None,
        'codigotipoDocumentoUno': 81,
        'numeroDocumentoUno': row['Nro Documento'],
        "identificacionOm": None,
        "codigoTipoDocumentoDos": None,
        "numeroDocumentoDos": None,
        "codigoTipoDestino": None,
        "codigoPaisOrigen": None,
        "codigoPaisDestino": None,
        "codigoBloqueOrigen": None,
        "codigoBloqueDestino": None,
        "cuitImportadorOExportador": None,
        'cuitDeFuncionario': row['CUIT Funcionario'],
        'muestra': {
            'fechaDeToma': row['Fecha de Toma'],
            'fechaDeRecepcion': row['Fecha de Recepcion'],
            "fechaDeElaboracion": None,
            "fechaDeVencimiento": None,
            "codigoDeProducto": None,
            "marcaDeProducto": None,
            "idProductoAlimento": 468,
            "tipoProductoAlimento": "SC",
            "cantidadDeEnvases": None,
            "codigoPresentacion": None,
            "codigoProceso": None,
            "precinto": "-",
            "precintoCM1": None,
            "cantidadCM1": None,
            "codigoUnidadDeMedidaCM1": None,
            "precintoCM2": None,
            "cantidadCM2": None,
            "codigoUnidadDeMedidaCM2": None,
            "cantidadDeMuestra": int(row["Tamaño Muestra"]) if pd.notna(row["Tamaño Muestra"]) else None,
            "codigoUnidadDeMedidaDeMuestra": 178,
            "cantidadDeLote": int(row["Cantidad de Muestra"]) if pd.notna(row["Cantidad de Muestra"]) else None,
            "codigoUnidadDeMedidaDeLote": int(row['Unidad de Medida de la Cantidad']) if pd.notna(row['Unidad de Medida de la Cantidad']) else None,
            'analisis': [
                {
                    'id': 1,
                    "codigoDeEdad": None,
                    "codigoDeCategoria": None,
                    "sexo": None,
                    "antigeno": None,
                    "marcaDeAntigeno": None,
                    "lote": None,
                    "fechaDeVencimientoDeAnalisis": None,
                    "fechaDeVacunacion": None,
                    "observacionDeAnalisis": None,
                    'codigoEnsayo': int(row["Rubro"]) if pd.notna(row["Rubro"]) else None,
                    "idSustancia": None,
                    'resultadoUnico': False,
                    "hembrasNoPreniadas": None,
                    "codigoDatoAdicional": None,
                    "estampilla": None,
                    'fechaInicio': row["Fecha Inicio"],
                    'fechaFin': row["Fecha conclusion"],
                    'subMuestras': row["subMuestras"]
                }
            ],
            'codigoDirectorTecnico': int(row["Codigo DT"]) if pd.notna(row["Codigo DT"]) else None,
            'observaciones': observacion,                         #row["Observacion del Protocolo"],
            "conclusionTramite": conclusion_protocolo, #"--",
            "codigoConclusionTramite": None,
            "codigoResultadoSigcer": None
        },
        "origenLote": None,
        "datosProduccionLote": {
            "cantidad": int(row["Cantidad Animales"]) if pd.notna(row["Cantidad Animales"]) else None,
            "itemCantidad": "De Animales",
            "descripcionCantidad": None,
            "unidadesProduccion": None,
            "codigoUnidadDeMedida": None,
            "itemOtroCantidad": None,
            "fecha": None,
            "stringFecha": None,
            "itemFecha": None,
            "itemOtroFecha": None,
            "numero1": int(row["Numero Tropa"]) if pd.notna(row["Numero Tropa"]) else None,
            "itemNumero1": "De Tropa",
            "itemOtroNro1": None,
            "numero2": None,
            "itemNumero2": None,
            "itemOtroNro2": None
        },
        "solicitanteDeEnsayo": None,
        "codigoTipoDeTramite": 4
    }


############################ ACTAS DIGITALES - CONVERTIR PDF A EXCEL ##############################

# Extraccion de datos del PDF

#Extraigo las tablas y las identificaciones del los animales
def extraer_tablas(acta):
    tablas = []
    with pdfplumber.open(acta) as pdf:
        for pagina in pdf.pages:
            for tabla in pagina.extract_tables():
                tablas.append(tabla)

    print(f"Cantidad de tablas encontradas: {len(tablas)}")

    # --- Procesar tabla[2] como cabecera ---
    tabla_base = pd.DataFrame(tablas[2])
    tabla_base.columns = tabla_base.iloc[2]   # fila 2 como cabecera
    tabla_base = tabla_base.drop([0,1,2])     # quitamos filas de títulos
    tabla_base = tabla_base.rename(columns={
        "Nro. Tubo\n/Muestra": "Nro_Tubo",
        "Identificación": "Identificacion"
    })

    # Nos quedamos solo con la columna Identificacion
    df_final = tabla_base[["Identificacion","Nro_Tubo"]].copy()

    # --- Procesar tablas siguientes ---
    for i in range(3, len(tablas)):
        df_temp = pd.DataFrame(tablas[i])
        df_temp.columns = ["Nro_Tubo", "Identificacion", "Animal", "Categoria", "Fec_vacuna", "Observaciones"]
        df_temp = df_temp[["Identificacion","Nro_Tubo"]]
        df_final = pd.concat([df_final, df_temp], ignore_index=True)

    # --- Limpieza ---
    df_final["Identificacion"] = df_final["Identificacion"].astype(str).str.replace("\n", "").str.strip()
    df_final["Nro_Tubo"] = df_final["Nro_Tubo"].astype(str).str.strip()
  

    #  En lugar de devolver un DataFrame, devolvemos una lista de identificaciones
    return df_final

# Nuevo extraer tabalas.

def extraer_tablas2(acta):
    # Diccionario de categorías → códigos
    categorias = {
        "BUEYES": 101,
        "NOVILLITO": 8,
        "NOVILLO": 50,
        "TERNERA": 351,
        "TERNERO": 350,
        "TORITO/MEJ": 470,
        "TORO": 100,
        "VACA": 7,
        "VAQUILLONA": 200,
        "CABRA": 20,
        "CABRILLAS/CHIVITOS": 418,
        "CABRITO": 21,
        "CAPÓN": 12,
        "CHIVO": 19,
        "CIERVO DE CRÍA": 1181,
        "CIERVOS": 419,
        "CONEJOS": 409,
        "BORREGO/A": 11,
        "CARNERO": 9,
        "CORDERO/A": 13,
        "OVEJA": 10,
        "CACHORRO": 18,
        "CACHORRA": 476,
        "CAPÓN/ HEMBRA SIN SERVICIO": 17,
        "CERDA": 15,
        "LECHON": 16,
        "M.E.I.": 473,
        "PADRILLO": 14,
        "SIN ESPECIFICAR": 11402,
        "LLAMA MACHO": 411,
        "LLAMA HEMBRA": 412,
        "ASNO": 28,
        "BURRO": 27,
        "CABALLO": 23,
        "MULA": 26,
        "POTRILLO/A": 25,
        "YEGUA": 24
    }

    # Diccionario de categorías → sexo
    sexo_dict = {
        "BUEYES": "M",
        "NOVILLITO": "M",
        "NOVILLO": "M",
        "TERNERA": "H",
        "TERNERO": "M",
        "TORITO/MEJ": "M",
        "TORO": "M",
        "VACA": "H",
        "VAQUILLONA": "H",
        "CABRA": "H",
        "CABRILLAS/CHIVITOS": "H",
        "CABRITO": "M",
        "CAPÓN": "M",
        "CHIVO": "M",
        "CIERVO DE CRÍA": "H",
        "CIERVOS": "M",
        "CONEJOS": "M",
        "BORREGO/A": "M",
        "CARNERO": "M",
        "CORDERO/A": "M",
        "OVEJA": "H",
        "CACHORRO": "M",
        "CACHORRA": "H",
        "CAPÓN/ HEMBRA SIN SERVICIO": "H",
        "CERDA": "H",
        "LECHON": "M",
        "M.E.I.": "M",
        "PADRILLO": "M",
        "SIN ESPECIFICAR": "M",
        "LLAMA MACHO": "M",
        "LLAMA HEMBRA": "H",
        "ASNO": "M",
        "BURRO": "M",
        "CABALLO": "M",
        "MULA": "H",
        "POTRILLO/A": "M",
        "YEGUA": "H"
    }

    tablas = []
    with pdfplumber.open(acta) as pdf:
        for pagina in pdf.pages:
            for tabla in pagina.extract_tables():
                tablas.append(tabla)

    print(f"Cantidad de tablas encontradas: {len(tablas)}")

    # --- Procesar tabla[2] como cabecera ---
    tabla_base = pd.DataFrame(tablas[2])
    tabla_base.columns = tabla_base.iloc[2]   # fila 2 como cabecera
    tabla_base = tabla_base.drop([0,1,2])     # quitamos filas de títulos
    tabla_base = tabla_base.rename(columns={
        "Nro. Tubo\n/Muestra": "Nro_Tubo",
        "Identificación": "Identificacion",
        "Categoría/edad": "Categoria"
    })

    df_final = tabla_base[["Identificacion","Nro_Tubo","Categoria"]].copy()

    # --- Procesar tablas siguientes ---
    for i in range(3, len(tablas)):
        df_temp = pd.DataFrame(tablas[i])
        df_temp.columns = ["Nro_Tubo", "Identificacion", "Animal", "Categoria", "Fec_vacuna", "Observaciones"]
        df_temp = df_temp[["Identificacion","Nro_Tubo","Categoria"]]
        df_final = pd.concat([df_final, df_temp], ignore_index=True)

    # --- Limpieza ---
    df_final["Identificacion"] = df_final["Identificacion"].astype(str).str.replace("\n", "").str.strip()
    df_final["Nro_Tubo"] = df_final["Nro_Tubo"].astype(str).str.strip()

    # Normalizar Categoria: tomar solo lo que está antes de la primera barra
    df_final["Categoria_texto"] = df_final["Categoria"].astype(str).str.split("/").str[0].str.strip().str.upper()

    # Mapear al código numérico usando el diccionario
    df_final["Categoria"] = df_final["Categoria_texto"].map(categorias).fillna(categorias["SIN ESPECIFICAR"])

    # Mapear al sexo usando el diccionario
    df_final["Sexo"] = df_final["Categoria_texto"].map(sexo_dict).fillna(sexo_dict["SIN ESPECIFICAR"])

    return df_final

# Extraigo los datos de la cabecera de las actas digitales.

def extraer_datos_pdf(ruta_pdf):
    """
    Extrae del PDF:
    - Número de acta
    - CUIT del funcionario (formateado xx-yyyyyyyy-zz)
    - Nro. Oficial Senasa (formato original)
    - Motivo (mapeado contra dict motivos)
    - Submotivo (mapeado contra dict submotivos)
    - Fecha Toma (desde 'Fecha Muestra')
    - Especie (mapeado contra dict especies)
    """

    motivos = {
        "MUESTREO BRUCELOSIS": 465,
        "MUESTREO BRUCELOSIS MELITENSIS": 3,
        "MUESTREO BRUCELOSIS OVINA": 2,
        "MUESTREO EQUINO": 463
    }

    submotivos = {
        "CONTROL DE SERONEGATIVIDAD PARA EL MOVIMIENTO (CSM)": 9,
        "CONTROL INTERNO (BRC)": 30,
        "DETERMINACIÓN OBLIGATORIA DE ESTATUS SANITARIO (DOES PREDIO LIBRE))": 69,
        "DETERMINACIÓN OBLIGATORIA DE ESTATUS SANITARIO (DOES PREDIO NEGATIVO)": 23,
        "PLAN DE SANEAMIENTO (BRC)": 16,
        "RECERTIFICACIÓN DE LIBRE": 45,
        "REMUESTREO DE ANIMALES SOSPECHOSOS": 21,
        "REMUESTREO POR ANALISIS EPIDEMIOLOGICO": 31,
        "CERTIFICACION DE ESTABLECIMIENTO LIBRE": 33,
        "MOVIMIENTO": 32,
        "SANEAMIENTO": 5,
        "VIGILANCIA EPIDEMIOLÓGICA": 90,
        "CERTIFICACIÓN": 68,
        "RELEVAMIENTO SANITARIO": 4,
        "REPETICIÓN DE PRUEBA": 7,
        "TRASLADO / EXPOSICIÓN": 34,
        "VIGILANCIA": 11,
        "VIGILANCIA OFICIAL EN ESTABLECIMIENTO":63,
        "REMATE FERIA": 47,
        "AGRICULTURA FAMILIAR":22
    }

    especies = {
        "BOVINO": "E21",
        "BUBALO": "E22",
        "CAMÉLIDO": "E16",
        "CAPRINO": "E24",
        "CIERVO COMÚN": "E83",
        "CONEJO": "E70",
        "LIEBRE": "E71",
        "OVINO": "E25",
        "PORCINO": "E79",
        "EQUIDO": "E17",
        "LAMA": "E37"
    }

    datos = {}
    with pdfplumber.open(ruta_pdf) as pdf:
        for pagina in pdf.pages:
            contenido = pagina.extract_text()
            if contenido:
                # Número de acta
                match_acta = re.search(r"ACTA DE TOMA DE MUESTRAS Nº\s*(\d+)", contenido)
                if match_acta:
                    datos["numeroActa"] = match_acta.group(1)

                # CUIT del funcionario
                match_cuit = re.search(r"Funcionario:\s*(\d+)", contenido)
                if match_cuit:
                    cuit_raw = match_cuit.group(1)
                    if len(cuit_raw) >= 10:
                        datos["cuitDeFuncionario"] = f"{cuit_raw[:2]}-{cuit_raw[2:-1]}-{cuit_raw[-1]}"
                    else:
                        datos["cuitDeFuncionario"] = cuit_raw

                # Nro. Oficial Senasa
                match_senasa = re.search(r"Nro\. Oficial Senasa:\s*([\d./]+)", contenido)
                if match_senasa:
                    datos["RENSPA"] = match_senasa.group(1)

                # Fecha Muestra → Fecha Toma (corta antes de Funcionario)
                match_fecha = re.search(r"Fecha Muestra:\s*([^\n]+?)(?=\s*Funcionario:)", contenido)
                if match_fecha:
                    datos["FechaToma"] = match_fecha.group(1).strip()
                else:
                    datos["FechaToma"] = None

                # Motivo (corta antes de Submotivo)
                match_motivo = re.search(r"Motivo:\s*(.*?)(?=\s*Submotivo:)", contenido, re.DOTALL)
                if match_motivo:
                    motivo_texto = match_motivo.group(1).strip()
                    datos["Motivo"] = motivos.get(motivo_texto, None)
                    print(f"match motivo: {motivo_texto}")
                else:
                    datos["Motivo"] = None
                    print("No se encontró motivo")

                # Submotivo (corta antes de Expediente)
                match_submotivo = re.search(r"Submotivo:\s*(.*?)(?=\s*Expediente)", contenido, re.DOTALL)
                if match_submotivo:
                    submotivo_texto = match_submotivo.group(1).replace("\n", " ").strip()
                    datos["SubMotivo"] = submotivos.get(submotivo_texto, None)
                    print(f"match submotivo: {submotivo_texto}")
                else:
                    datos["SubMotivo"] = None
                    print("No se encontró submotivo")

                # Especie (corta antes de Matriz)
                match_especie = re.search(r"Especie:\s*(.*?)(?=\s*Matriz)", contenido, re.DOTALL)
                if match_especie:
                    especie_texto = match_especie.group(1).strip()
                    datos["Especie"] = especies.get(especie_texto, None)
                    print(f"match especie: {especie_texto}")
                else:
                    datos["Especie"] = None
                    print("No se encontró especie")

                # Si ya encontramos todo lo que necesitamos, podemos cortar
                if all(k in datos for k in ["numeroActa", "cuitDeFuncionario", "RENSPA", "Motivo", "SubMotivo", "FechaToma", "Especie"]):
                    return datos
    return datos


def codigoRubro(request, analito_id: int = None):
    perfil = PerfilUsuario.objects.select_related("datos_lab").get(usuario=request.user)
    laboratorio_id = perfil.datos_lab.id

    query = """
        SELECT 
            laboratorio_id,
            laboratorio_numero,
            codigo_rubro,
            analito,
            analito_id,
            tecnica
        FROM vista_laboratorio_ensayos
        WHERE laboratorio_id = %s
    """
    params = [laboratorio_id]

    if analito_id is not None:
        query += " AND analito_id = %s"
        params.append(analito_id)

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        columns = [col[0] for col in cursor.description]
        results = cursor.fetchall()

    return pd.DataFrame(results, columns=columns)


# Funciones para procesar el excel del acta digital - BRUCELOSIS

def agrupar_columnas_aie(plantilla):
    columnas_a_agrupar = ["Nro Informe", "Nro Acta", "RENSPA",
                          "SubMotivo", "CUIT Funcionario", "Fecha de Toma",
                          "Fecha de Recepcion", "Cantidad Muestras", "Rubro",
                           "Fecha Inicio", "Fecha Fin", "Codigo DT", 
                           "Observacion del Protocolo", "Conclusion Protocolo"
                           ]
    return plantilla.groupby("Nro Informe", as_index=False)[columnas_a_agrupar].first()

def agrupar_columnas_bru(plantilla):
    columnas_a_agrupar = ["Nro Informe", "Nro Acta", "RENSPA",
                          "Motivo", "SubMotivo", "CUIT Funcionario",
                          "Fecha de Toma", "Fecha de Recepcion", "Especie",
                          "Cantidad Muestras", "Rubro", "Fecha Inicio",
                          "Fecha Fin", "Codigo DT", "Observacion del Protocolo",
                          "Conclusion Protocolo"
                          ]
    return plantilla.groupby("Nro Informe", as_index=False)[columnas_a_agrupar].first()

def analisis_bru_digital(df):
    analisis_agrupados = {}

    for nro_informe, sub_df in df.groupby("Nro Informe"):
        analisis_agrupados[nro_informe] = []

        for codigo_ensayo, grupo in sub_df.groupby("Rubro"):  # Agrupar por códigoEnsayo
            
            
            analisis_agrupados[nro_informe].append({
                "id": 1,
                "codigoEnsayo": int(codigo_ensayo),
                "resultadoUnico": False,
                "fechaInicio": grupo["Fecha Inicio"].iloc[0],
                "fechaFin": grupo["Fecha Fin"].iloc[0],
                "subMuestras": submuestras(grupo)  # Ahora toma solo las submuestras correctas
            })

    return analisis_agrupados

# Procesa las Submuestras
def submuestras(df):
    submuestras = []
    for _, row in df.iterrows():

        identificaciones = row["Identificacion Muestra"].split(', ')
        valor = row.get("Identificacion Interna Laboratorio", "")
        if pd.isna(valor) or str(valor).lower() == "nan":
            identificaciones_internas = ['']
        else:
            identificaciones_internas = str(valor).split(', ')

        # --- Procesar categorías como enteros ---
        if "Categoria" in row and pd.notna(row["Categoria"]):
            if isinstance(row["Categoria"], (int, float)):
                categorias = [int(row["Categoria"])]
            else:
                categorias = [int(x) if x.isdigit() else None for x in str(row["Categoria"]).split(', ')]
        else:
            categorias = [None]

        sexos = row["Sexo"].split(', ')
        antigenos = row["Antigeno/Kit"].split(', ')
        marcas = row["Marca Antigeno/Kit"].split(', ')
        lotes = row["Lote"].split(', ')
        estampillas = row["Estampilla"].split(', ')
        observaciones = str(row["Observacion Muestra"]).split(', ') if pd.notna(row["Observacion Muestra"]) else ['']

        num_submuestras = len(identificaciones)

        identificaciones_internas += [''] * (num_submuestras - len(identificaciones_internas))
        categorias += [None] * (num_submuestras - len(categorias))
        sexos += [''] * (num_submuestras - len(sexos))
        antigenos += [''] * (num_submuestras - len(antigenos))
        marcas += [''] * (num_submuestras - len(marcas))
        lotes += [''] * (num_submuestras - len(lotes))
        estampillas += [''] * (num_submuestras - len(estampillas))
        observaciones += [''] * (num_submuestras - len(observaciones))

        for i in range(num_submuestras):
            submuestras.append({
                "codigoResultadoLetra": int(row["Resultado Letra"]) if pd.notna(row["Resultado Letra"]) else None,
                "identificacion": identificaciones[i],
                "identificacionInternaDeLaboratorio": identificaciones_internas[i],
                "codigoTipoIdentificacion": row["Tipo Identificacion"],
                "observacion": observaciones[i],
                "codigoDeCategoria": categorias[i] if categorias[i] is not None else None,
                "sexo": sexos[i],
                "antigeno": antigenos[i],
                "marcaDeAntigeno": marcas[i],
                "lote": lotes[i],
                "fechaDeVencimientoDeAnalisis": row["Fecha Vencimiento Antigeno/Kit"],
                "estampilla": estampillas[i]
            })

    return submuestras


# Función para construir el JSON final por fila
def json_bru(row, codigoLaboratorio):

    observacion = (
        str(row.get("Observacion del Protocolo"))
        if pd.notna(row.get("Observacion del Protocolo")) else "--"
    )
    conclusion_protocolo = (
        str(row.get("Conclusion Protocolo"))
        if pd.notna(row.get("Conclusion Protocolo")) else "--"
    )
    
    return {
        "numeroInforme": row["Nro Informe"],
        "codigoLaboratorio": str(codigoLaboratorio),
        "renspaUnidadProductiva": row['RENSPA'],
        "codigoMotivo": row["Motivo"],
        "codigoSubMotivo": row["SubMotivo"],
        "codigotipoDocumentoUno": 21,
        "numeroDocumentoUno": row["Nro Acta"],
        "cuitDeFuncionario": row['CUIT Funcionario'],
        "muestra": {
            "fechaDeToma": row["Fecha de Toma"], # fecha fija
            "fechaDeRecepcion": row["Fecha de Recepcion"], # fecha fija
            "codigoDeProducto": row["Especie"],
            "cantidadDeLote": row["Cantidad Muestras"],
            "codigoUnidadDeMedidaDeLote": 326, #int fijo
            "analisis": row["analisis"],
            "codigoDirectorTecnico": row["Codigo DT"],
            "observaciones": observacion,    #row["Observacion del Protocolo"],
            "conclusionTramite": conclusion_protocolo, #'--',

        },
        "codigoTipoDeTramite": 3
    }



# Construcción del JSON final
def json_aie_digital(row,codigoLaboratorio):
 
    observacion = (
        str(row.get("Observacion del Protocolo"))
        if pd.notna(row.get("Observacion del Protocolo")) else "--"
    )
    conclusion_protocolo = (
        str(row.get("Conclusion Protocolo"))
        if pd.notna(row.get("Conclusion Protocolo")) else "--"
    )

    return {
        'numeroInforme': row['Nro Informe'],
        'codigoLaboratorio': str(codigoLaboratorio),
        'renspaUnidadProductiva': row['RENSPA'],
        'codigoMotivo': 463,
        'codigoSubMotivo': row["SubMotivo"], # traerlo del excel
        'codigotipoDocumentoUno': 21,
        'numeroDocumentoUno': row['Nro Acta'],
        'cuitDeFuncionario': row['CUIT Funcionario'],
        'muestra': {
            'fechaDeToma': row["Fecha de Toma"],
            'fechaDeRecepcion': row["Fecha de Recepcion"],
            'codigoDeProducto': "E17", #Traerlo del acta
            'cantidadDeLote': row["Cantidad Muestras"],
            'codigoUnidadDeMedidaDeLote': 326,
            'analisis': [
                {
                    'id': 1,
                    'codigoEnsayo': row['Rubro'],
                    'resultadoUnico': 'False',
                    'fechaInicio': row['Fecha Inicio'],
                    'fechaFin': row['Fecha Fin'],
                    'subMuestras': row["subMuestras"]
                }
            ],
            'codigoDirectorTecnico': row['Codigo DT'],
            'observaciones': observacion, 
            "conclusionTramite": conclusion_protocolo, #'--',
        },
        'codigoTipoDeTramite': "3"
    }

# Esta función sirve de nexo entre el df que se obtiene del acta digital y lo convierte a JSON

def nexo_acta_json_bru(df_acta, request):
    # Convertir columnas específicas a tipo string
    columns_to_str = [
        "Nro Informe","Nro Acta", "RENSPA", "CUIT Funcionario", "Especie",
        "Identificacion Muestra", "Identificacion Interna Laboratorio", "Sexo",
        "Antigeno/Kit", "Marca Antigeno/Kit", "Lote", "Estampilla"
    ]
    for column in columns_to_str:
        if column in df_acta.columns:
            df_acta[column] = df_acta[column].astype(str)

    # Aplicar el formato de fecha a las columnas correspondientes
    columnas_de_fecha = ["Fecha de Toma", "Fecha de Recepcion", "Fecha Inicio", "Fecha Fin", "Fecha Vencimiento Antigeno/Kit"]
    for columna in columnas_de_fecha:
        if columna in df_acta.columns:
            df_acta[columna] = df_acta[columna].apply(formatear_fecha)

    # Agrupar solo las columnas generales por número de informe
    plantilla_agrupada = agrupar_columnas_bru(df_acta)

    # Convertir columnas numéricas explícitamente y mantener NaN sin modificar
    numeric_columns = ["Motivo", "SubMotivo","Cantidad Muestras","Codigo DT","Resultado Letra", "Categoria"]
    for col in numeric_columns:
        if col in plantilla_agrupada.columns:
            plantilla_agrupada[col] = pd.to_numeric(plantilla_agrupada[col], errors='coerce')

    # Generar el análisis y submuestras correctamente agrupadas
    rubrosLab = rubros_lab(request)
    analisis_dict = analisis_bru_digital(df_acta)

    # Asignar correctamente cada informe con sus análisis y submuestras
    plantilla_agrupada["analisis"] = plantilla_agrupada["Nro Informe"].map(lambda x: analisis_dict.get(x, []))

    # Construcción del JSON final
    codigoLaboratorio = rubrosLab["Nro_Laboratorio"].iloc[0] if not rubrosLab.empty else None
    json_data = plantilla_agrupada.apply(lambda row: json_bru(row, codigoLaboratorio), axis=1).tolist()

    return json_data


def nexo_acta_json_aie(df_acta, request):
    # Convertir columnas específicas a tipo string
    columns_to_str = [
        "Nro Informe","Nro Acta", "RENSPA", "CUIT Funcionario", "Especie",
        "Identificacion Muestra", "Identificacion Interna Laboratorio", "Sexo",
        "Antigeno/Kit", "Marca Antigeno/Kit", "Lote", "Estampilla"
    ]
    for column in columns_to_str:
        if column in df_acta.columns:
            df_acta[column] = df_acta[column].astype(str)

    # Agrupar solo las columnas generales por número de informe
    plantilla_agrupada = agrupar_columnas_aie(df_acta)

    # Convertir columnas numéricas explícitamente y mantener NaN sin modificar
    numeric_columns = ["Motivo", "SubMotivo","Cantidad Muestras","Codigo DT","Resultado Letra", "Categoria"]
    for col in numeric_columns:
        if col in plantilla_agrupada.columns:
            plantilla_agrupada[col] = pd.to_numeric(plantilla_agrupada[col], errors='coerce')

    # Generar el análisis y submuestras correctamente agrupadas
    rubrosLab = rubros_lab(request)
    analisis_dict = df_acta.groupby("Nro Informe").apply(submuestras).to_dict()

    # Asignar correctamente cada informe con sus análisis y submuestras
    plantilla_agrupada["subMuestras"] = plantilla_agrupada["Nro Informe"].map(analisis_dict)

    # Construcción del JSON final
    codigoLaboratorio = rubrosLab["Nro_Laboratorio"].iloc[0] if not rubrosLab.empty else None
    json_data = plantilla_agrupada.apply(lambda row: json_aie_digital(row, codigoLaboratorio), axis=1).tolist()

    return json_data