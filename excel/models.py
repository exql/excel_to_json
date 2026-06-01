from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


# Create your models here.

class Tecnica(models.Model):
    tecnica = models.CharField(max_length=255)
    cod_técnica = models.IntegerField(unique=True)

    def __str__(self):
        return f"{self.tecnica} ({self.cod_técnica})"

class Matriz(models.Model):
    nombreMatriz = models.CharField(max_length=255)
    cod_Matriz = models.IntegerField(unique=True)

    def __str__(self):
        return f"{self.nombreMatriz} ({self.cod_Matriz})"

class Analito(models.Model):
    analito = models.CharField(max_length=255)
    cod_analito = models.IntegerField(unique=True)

    def __str__(self):
        return f"{self.analito} ({self.cod_analito})"

class Rubro(models.Model):
    id = models.AutoField(primary_key=True)  # ID incremental automático
    rubro = models.CharField(max_length=255, unique=True) 

    def __str__(self):
        return self.rubro
    
class Ensayo(models.Model):
    id = models.AutoField(primary_key=True)  
    
    # Relaciones foráneas con ID
    rubro = models.ForeignKey("Rubro", on_delete=models.SET_NULL, null=True, blank=True)
    analito = models.ForeignKey("Analito", on_delete=models.CASCADE, null=True, blank=True)
    matriz = models.ForeignKey("Matriz", on_delete=models.CASCADE, null=True, blank=True)
    tecnica = models.ForeignKey("Tecnica", on_delete=models.CASCADE, null=True, blank=True)
    
    def __str__(self):
        return f"{self.ensayo} ({self.codigo_ensayo})"
  

class Motivo(models.Model):
    codigo = models.IntegerField(unique=True)
    descripcion = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.descripcion} ({self.codigo})"


class SubMotivo(models.Model):
    codigo = models.IntegerField(unique=True)
    descripcion = models.CharField(max_length=255)
    motivo = models.ForeignKey(Motivo, on_delete=models.CASCADE, related_name="submotivos")

    def __str__(self):
        return f"{self.descripcion} ({self.codigo})"


class Especie(models.Model):
    codigo = models.CharField(max_length=10, unique=True)  # Ej: "E21"
    descripcion = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.descripcion} ({self.codigo})"


class Sexo(models.Model):
    codigo = models.CharField(max_length=1, unique=True)  # Ej: "M", "H"
    descripcion = models.CharField(max_length=50)

    def __str__(self):
        return self.descripcion


class Categoria(models.Model):
    codigo = models.IntegerField(unique=True)
    descripcion = models.CharField(max_length=100)
    especie = models.ForeignKey(Especie, on_delete=models.SET_NULL, null=True, blank=True)
    sexo = models.ForeignKey(Sexo, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.descripcion} ({self.codigo})"



class DatosLab(models.Model):
    numLab = models.CharField(max_length=20, unique=True)
    nombreLab = models.CharField(max_length=255)
    email = models.EmailField(unique=True, blank=True, null=True)
    cuit = models.CharField(max_length=15, unique=True)
    telefono = models.CharField(max_length=15)
    directorTecnico = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.nombreLab} ({self.numLab})"
    
class LabEnsayo(models.Model):
    laboratorio = models.ForeignKey(DatosLab, on_delete=models.CASCADE)
    ensayo = models.ForeignKey(Ensayo, on_delete=models.CASCADE)
    codigo_ensayo = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        unique_together = ("laboratorio", "ensayo")  # Evita duplicados
        verbose_name = "Ensayo asignado a laboratorio"
        verbose_name_plural = "Ensayos asignados a laboratorios"

    def __str__(self):
        return f"{self.laboratorio.nombreLab} → {self.ensayo.id} (Código {self.codigo_ensayo})"
      

class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    datos_lab = models.ForeignKey(DatosLab, on_delete=models.SET_NULL, null=True)
    password_visible = models.CharField(max_length=255, blank=True, null=True)  # ✅ Campo para guardar la clave temporal

    def __str__(self):
        return f"Perfil de {self.usuario.username}"
    


@receiver(post_save, sender=User)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    if created:
        perfil_usuario = PerfilUsuario.objects.create(usuario=instance)

        # 📌 Asignar un laboratorio si existe buscando por nombre de usuario
        laboratorio = DatosLab.objects.filter(numLab=instance.username).first()  # Reemplaza con el campo correcto

        if laboratorio:
            perfil_usuario.datos_lab = laboratorio
            perfil_usuario.save()
            print(f"✅ Perfil actualizado: {perfil_usuario.usuario.username} asignado a {perfil_usuario.datos_lab.nombreLab}")


# Almacenar contenido de Excel
class RegistroExcel(models.Model):
    # Metadatos del request
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    laboratorio = models.ForeignKey(DatosLab, on_delete=models.SET_NULL, null=True, blank=True)
    numlab = models.CharField(max_length=50, null=True, blank=True)

    horario_sesion = models.DateTimeField(null=True, blank=True)

     # Campos del Excel
    nro_informe = models.CharField(max_length=50, blank=True, null=True)
    nro_acta = models.CharField(max_length=50, blank=True, null=True)  # Puede ser str/int
    renspa = models.CharField(max_length=50, blank=True, null=True)
    motivo = models.IntegerField(blank=True, null=True)
    submotivo = models.IntegerField(blank=True, null=True)
    fecha_toma = models.DateField(blank=True, null=True)
    fecha_recepcion = models.DateField(blank=True, null=True)
    especie = models.CharField(max_length=100, blank=True, null=True)
    cantidad_muestras = models.IntegerField(blank=True, null=True)
    unidad_medida = models.IntegerField(blank=True, null=True)
    rubro = models.IntegerField(blank=True, null=True)
    fecha_inicio = models.DateField(blank=True, null=True)
    fecha_fin = models.DateField(blank=True, null=True)
    resultado_letra = models.CharField(max_length=100, null=True, blank=True)
    identificacion_muestra = models.TextField(null=True, blank=True)
    identificacion_interna_lab = models.TextField(null=True, blank=True)
    tipo_identificacion = models.CharField(max_length=100, blank=True, null=True)
    categoria = models.CharField(max_length=100, blank=True, null=True)
    sexo = models.CharField(max_length=20, blank=True, null=True)
    antigeno_kit = models.CharField(max_length=255, blank=True, null=True)
    marca_antigeno_kit = models.CharField(max_length=255, blank=True, null=True)
    lote = models.CharField(max_length=100, blank=True, null=True)
    fecha_vencimiento_antigeno_kit = models.DateField(blank=True, null=True)
    estampilla = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Registro {self.nro_informe or 'sin informe'} - Usuario {self.usuario_id}"