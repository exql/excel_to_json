from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.forms import formset_factory
from .models import DatosLab, PerfilUsuario, Ensayo, LabEnsayo

# 🔐 Registro de usuario
class RegistroUsuarioForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["username", "password1", "password2", "email"]

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
        return user

# 🧪 Formulario de laboratorio
class AsignarLaboratorioForm(forms.ModelForm):
    class Meta:
        model = DatosLab
        fields = [
            "numLab", "nombreLab", "email", "cuit",
            "telefono", "directorTecnico"
        ]

# 🧩 Formulario para asignar/editar ensayos
class EnsayoAsignadoForm(forms.Form):
    ensayo = forms.ModelChoiceField(
        queryset=Ensayo.objects.select_related('analito', 'matriz', 'tecnica'),
        label="Ensayo",
        required=True
    )
    codigo_ensayo = forms.IntegerField(label="Código del Ensayo", required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["ensayo"].label_from_instance = lambda e: f"{e.analito.analito} | {e.matriz.nombreMatriz} | {e.tecnica.tecnica}"

# 🧪 Formset para creación
AsignarEnsayoFormSet = formset_factory(EnsayoAsignadoForm, extra=1, can_delete=True)

# 🧪 Formset para edición
EditarEnsayosFormSet = formset_factory(EnsayoAsignadoForm, extra=1, can_delete=True)