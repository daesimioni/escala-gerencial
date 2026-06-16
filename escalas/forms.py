"""
Forms for the Escala de Sobreaviso system.
"""
from django import forms

from .models import BloqueioUsuario, EscalaDia, Feriado, Feriadao, UsuarioEscala


class EscalaDiaForm(forms.ModelForm):
    class Meta:
        model = EscalaDia
        fields = ['s1', 'observacao', 'manual']
        labels = {
            's1': 'Gerente de sobreaviso',
            'manual': 'Edicao manual',
        }
        widgets = {
            'observacao': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        usuarios = UsuarioEscala.objects.filter(ativo=True).select_related('grupo')
        choices = [('', '--- Nenhum ---')]
        for u in usuarios:
            choices.append((u.id, f'{u.nome} (Grupo {u.grupo.nome})'))
        self.fields['s1'].choices = choices
        self.fields['s1'].required = False


class BloqueioUsuarioForm(forms.ModelForm):
    class Meta:
        model = BloqueioUsuario
        fields = ['usuario', 'tipo', 'data_inicio', 'data_fim', 'motivo']
        widgets = {
            'data_inicio': forms.DateInput(attrs={'type': 'date'}),
            'data_fim': forms.DateInput(attrs={'type': 'date'}),
            'motivo': forms.Textarea(attrs={'rows': 2}),
        }


class FeriadoForm(forms.ModelForm):
    class Meta:
        model = Feriado
        fields = ['nome', 'data', 'tipo', 'ativo', 'recorrente', 'descricao']
        widgets = {
            'data': forms.DateInput(attrs={'type': 'date'}),
            'descricao': forms.Textarea(attrs={'rows': 2}),
        }


class FeriadaoForm(forms.ModelForm):
    class Meta:
        model = Feriadao
        fields = ['nome', 'data_inicio', 'data_fim', 'manual', 'observacao']
        widgets = {
            'data_inicio': forms.DateInput(attrs={'type': 'date'}),
            'data_fim': forms.DateInput(attrs={'type': 'date'}),
            'observacao': forms.Textarea(attrs={'rows': 2}),
        }


class TrocaEscalaForm(forms.Form):
    """Form for replacing the on-call manager on a date."""
    data = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    usuario_destino = forms.ModelChoiceField(
        queryset=UsuarioEscala.objects.filter(ativo=True),
        label='Novo gerente de sobreaviso'
    )
    motivo = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}), required=False)


class GeracaoEscalaForm(forms.Form):
    """Form to trigger scale generation."""
    ano = forms.IntegerField(min_value=2024, max_value=2035, initial=2026)
    mes = forms.IntegerField(min_value=1, max_value=12)
    preservar_manuais = forms.BooleanField(
        required=False,
        initial=True,
        label='Preservar edicoes manuais',
    )
