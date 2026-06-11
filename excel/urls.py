from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView,LoginView



urlpatterns = [
    
    path('', views.login_view, name='login'),
    path('index/', views.index, name='index'),
    path('planes/', views.planes, name='planes'),
    path('aie/', views.aie, name='aie'),
    path('brucelosis/', views.brucelosis, name='brucelosis'),
    path('triqui/', views.triqui, name='triqui'),
    path('contacto/', views.contacto, name='contacto'),
    path('nosotros/', views.nosotros, name='nosotros'),
    path('preguntas/', views.preguntas, name='preguntas'),
    path('instructivos/', views.instructivos, name='instructivos'),
    path('logout/', LogoutView.as_view(next_page=''), name='logout'),
    #path('altausuario/', views.altausuario, name='altausuario'),
    path("registrar_usuario/", views.registrar_usuario, name="registrar_usuario"),
    path("asignar_laboratorio/<int:user_id>/", views.asignar_laboratorio, name="asignar_laboratorio"),
    path("usuarios_lista/", views.usuarios_lista, name="usuarios_lista"),
    path('tutoriales/', views.tutoriales, name='tutoriales'),
    path('convertir_aie/', views.convertir_aie, name='convertir_aie'),
    path('convertir_bru/', views.convertir_bru, name='convertir_bru'),
    path('convertir_Triqui/', views.convertir_Triqui, name='convertir_Triqui'),
    path("cambiar_contraseña/<int:user_id>/", views.cambiar_contraseña, name="cambiar_contraseña"),
    path("editar_ensayos/<int:lab_id>/", views.editar_ensayos_laboratorio, name="editar_ensayos"),

    path('actadigital_AIE/', views.actadigital_AIE, name='actadigital_AIE'), # Hoja Pasa el pdf a Excel de AIE
    path('convertir_Acta_AIE/', views.convertir_Acta_AIE, name='convertir_Acta_AIE'), # Funcion convierte pdf a excel
    path('crear_json_AIE_digital/', views.crear_json_AIE_digital, name='crear_json_AIE_digital'),
    path('actadigital_bru/', views.actadigital_bru, name='actadigital_bru'),    
    path('convertir_Acta_bru/', views.convertir_Acta_bru, name='convertir_Acta_bru'),
    path('crear_json_bru_digital/', views.crear_json_bru_digital, name='crear_json_bru_digital'),
    path('excel_GRECERT/', views.excel_GRECERT, name='excel_GRECERT'),
    path('Actadigital_Aujeszky/', views.Actadigital_Aujeszky, name='Actadigital_Aujeszky'),

    path('actadigital_AIE2/', views.actadigital_AIE2, name='actadigital_AIE2'), # Hoja Pasa el pdf a Excel de AIE
    path('actadigital_bru2/', views.actadigital_bru2, name='actadigital_bru2'),

    path('actaBru_JSON/', views.actaBru_JSON, name='actaBru_JSON'),
    path('actaAIE_JSON/', views.actaAIE_JSON, name='actaAIE_JSON'),
    path('excel_GRECERT/', views.excel_GRECERT, name='excel_GRECERT'),

    path('actadigital_bru3/', views.actadigital_bru3, name='actadigital_bru3'),

]