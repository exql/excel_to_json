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
from .models import RegistroExcel, DatosLab, Motivo, SubMotivo, Especie, Categoria, Tecnica, Sexo
import unicodedata
import fitz
import logging
from .service import * 
from .forms import *
import pandas as pd

"""
#trae los codigos del rubro basado en eanalito_ID
    dataLab= LabDataService(request.user)
    rubroTriqui= dataLab.rubrosLab(analito_id)
    rubroTriqui= rubroTriqui[['codigo_rubro']]
    rubroTriqui = int(rubroTriqui.iloc[0]) if not rubroTriqui.empty else None
"""

class PlantillaService:
    """
    Servicio para generar plantillas Excel dinámicas según la enfermedad.
    
    Cada método genera un archivo Excel con columnas específicas y lo devuelve
    como respuesta HTTP para descarga desde el frontend.
    
    Uso típico:
        service = PlantillaService(request)
        response = service.crearPlantillas_triqui()
    """

    def __init__(self, request):
        """
        Inicializa el servicio con el request del usuario.
        
        Parámetros:
        - request: objeto HttpRequest de Django, usado para obtener el usuario.
        """
        self.request = request

    def _exportar_excel(self, df: pd.DataFrame, nombre_archivo: str) -> HttpResponse:
        """
        Método interno para exportar un DataFrame a Excel y devolverlo como HttpResponse.
        
        Parámetros:
        - df: DataFrame de pandas con los datos a exportar.
        - nombre_archivo: nombre del archivo Excel a descargar.
        
        Retorna:
        - HttpResponse con el archivo Excel.
        """
        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{nombre_archivo}"'

        with pd.ExcelWriter(response, engine='openpyxl', datetime_format='DD/MM/YYYY') as writer:
            df.to_excel(writer, index=False, header=True)

        return response

    def triqui_negativos(self) -> HttpResponse:
        """
        Genera una plantilla Excel para la enfermedad 'Triqui'.
        
        Retorna:
        - HttpResponse con el archivo Excel descargable.
        
        Columnas de la plantilla:
        - Nro Informe
        - Nro Autorizacion
        - Nro Tropa
        - CUIT Funcionario
        - Cantidad Animales
        - Fecha de Toma
        - Cantidad de Pool
        - Identificacion Pool
        - Resultado Letra
        - Observacion Pool
        - Conclusion Protocolo
        """
        # DataFrame con datos de ejemplo (sin lista de columnas explícita)
        df_acta = pd.DataFrame([{
            "Nro Informe":"3333333",
            "Nro Autorizacion":"12345",
            "Nro Tropa":"555",
            "CUIT Funcionario": "20-34123029-3",
            "Cantidad Animales": 40,
            "Fecha de Toma": pd.to_datetime("2025-03-12 03:00"),
            "Cantidad de Pool": 2,
            "Identificacion Pool":"pool 1",
            "Resultado Letra": 81,
            "Observacion Pool":"Garron del 1 al 20",
            "Conclusion Protocolo":"Todos los resultados fueron NO DETECTADO"
        }])

        # Conversión de columnas numéricas a enteros
        columnas_enteros = ["Cantidad Animales","Cantidad de Pool","Resultado Letra"]
        for columna in columnas_enteros:
            if columna in df_acta.columns:
                df_acta[columna] = pd.to_numeric(df_acta[columna], errors="coerce").astype("Int64")

        return self._exportar_excel(df_acta, "Plantilla_Triqui.xlsx")
