from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import authenticate, login
import os
import pandas as pd
import io
import json
from datetime import datetime
from django.views.decorators.csrf import csrf_exempt
from tempfile import NamedTemporaryFile
from django.db import connection
import django

# ACTAS DIGITALES - CONVERTIR PDF A EXCEL

# Consultar en la BD el "codigoEnsayo/ Codigo Rubro" del laboratorio.
# 1. Indicar el módulo de settings de tu proyecto
os.environ.setdefault("djangoserver", "excel.settings")

# 2. Inicializar Django
django.setup()

def get_rubros_lab(laboratorio_id: int, analito_id: int = None):
    query = """
        SELECT 
            laboratorio_id,
            laboratorio_numero,
            codigo_rubro,
            analito_id
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


if __name__ == "__main__":
    df = get_rubros_lab(11, 1)  # laboratorio_id=11 y analito_id=1
    print(df)




