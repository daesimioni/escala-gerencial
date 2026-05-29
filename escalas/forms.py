"""
Forms for the Escala de Sobreaviso system.
"""
from django import forms

from .models import BloqueioUsuario, EscalaDia, Feriado, Feriadao, UsuarioEscala


class EscalaDiaForm(forms.ModelForm):
    class Meta:
        model = EscalaDia
        fields = ['s1', 's2', 'observacao', 'manual']
        widgets = {
            'observacao': forms.Textarea(attrs={'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        usuarios = UsuarioEscala.objects.filter(ativo=True).select_related('grupo')
        choices = [('', '— Nenhum —')]
        for u in usuarios:
            choices.append((u.id, f'{u.nome} (Grupo {u.grupo.nome})'))
        self.fields['s1'].choices = choices
        self.fields['s2'].choices = choices
        self.fields['s1'].required = False
        self.fields['s2'].required = False

    def clean(self):
        cleaned = super().clean()
        s1 = cleaned.get('s1')
        s2 = cleaned.get('s2')
        if s1 and s2 and s1.grupo_id == s2.grupo_id:
            raise forms.ValidationError(
                'Dupla inválida! S1 e S2 devem ser de grupos diferentes (A + B).'
            )
        return cleaned


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
    """Form for swapping assignments between two users."""
    data = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    usuario_origem = forms.ModelChoiceField(
        queryset=UsuarioEscala.objects.filter(ativo=True),
        label='Usuário de origem'
    )
    usuario_destino = forms.ModelChoiceField(
        queryset=UsuarioEscala.objects.filter(ativo=True),
        label='Usuário de destino'
    )
    role_origem = forms.ChoiceField(choices=[('S1', 'S1'), ('S2', 'S2')], label='Função origem')
    role_destino = forms.ChoiceField(choices=[('S1', 'S1'), ('S2', 'S2')], label='Função destino')
    motivo = forms.CharField(widget=forms.Textarea(attrs={'rows': 2}), required=False)


class GeracaoEscalaForm(forms.Form):
    """Form to trigger scale generation."""
    ano = forms.IntegerField(min_value=2024, max_value=2035, initial=2026)
    mes = forms.IntegerField(min_value=1, max_value=12)
    preservar_manuais = forms.BooleanField(required=False, initial=True,
                                           label='Preservar edições manuais')
