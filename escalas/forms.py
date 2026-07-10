"""
Forms for the Escala de Sobreaviso system.
"""
from datetime import date

from django import forms
from django.db.models import Q

from .models import (
    BloqueioUsuario, EscalaDia, Feriado, Feriadao, SolicitacaoTroca,
    UsuarioEscala,
)


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
            lotacao = f' - {u.lotacao}' if u.lotacao else ''
            choices.append((u.id, f'{u.nome}{lotacao} (Grupo {u.grupo.nome})'))
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


class EscalaDestinoSelect(forms.Select):
    """Select that exposes the assigned manager id for client-side filtering."""

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        instance = getattr(value, 'instance', None)
        if instance is not None:
            option['attrs']['data-manager-id'] = str(instance.s1_id)
        return option


class SolicitacaoTrocaForm(forms.Form):
    """Form for requesting a two-manager on-call swap."""

    escala_origem = forms.ModelChoiceField(
        queryset=EscalaDia.objects.none(),
        label='Minha escala',
        empty_label='Selecione sua data',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    gerente_destino = forms.ModelChoiceField(
        queryset=UsuarioEscala.objects.none(),
        label='Gerente para troca',
        empty_label='Selecione o gerente',
        widget=forms.Select(attrs={'class': 'form-select', 'data-role': 'swap-manager'}),
    )
    escala_destino = forms.ModelChoiceField(
        queryset=EscalaDia.objects.none(),
        label='Escala que vou assumir',
        empty_label='Selecione a data do outro gerente',
        widget=EscalaDestinoSelect(attrs={'class': 'form-select', 'data-role': 'swap-target'}),
    )
    motivo = forms.CharField(
        label='Motivo',
        required=False,
        widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
    )

    def __init__(self, *args, gerente_atual=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.gerente_atual = gerente_atual
        hoje = date.today()

        if gerente_atual:
            origem_qs = EscalaDia.objects.filter(
                data__gte=hoje,
                s1=gerente_atual,
            ).select_related('s1').order_by('data')
            destino_qs = EscalaDia.objects.filter(
                data__gte=hoje,
                s1__isnull=False,
            ).exclude(s1=gerente_atual).select_related('s1').order_by('s1__nome', 'data')
            gerentes_qs = UsuarioEscala.objects.filter(ativo=True).exclude(pk=gerente_atual.pk)
        else:
            origem_qs = EscalaDia.objects.none()
            destino_qs = EscalaDia.objects.none()
            gerentes_qs = UsuarioEscala.objects.none()

        self.fields['escala_origem'].queryset = origem_qs
        self.fields['escala_destino'].queryset = destino_qs
        self.fields['gerente_destino'].queryset = gerentes_qs
        self.fields['escala_origem'].label_from_instance = self._label_origem
        self.fields['escala_destino'].label_from_instance = self._label_destino

    @staticmethod
    def _label_origem(escala):
        return f'{escala.data:%d/%m/%Y} - {escala.s1.nome}'

    @staticmethod
    def _label_destino(escala):
        return f'{escala.s1.nome} - {escala.data:%d/%m/%Y}'

    def clean(self):
        cleaned = super().clean()
        origem = cleaned.get('escala_origem')
        destino = cleaned.get('escala_destino')
        gerente_destino = cleaned.get('gerente_destino')

        if not self.gerente_atual:
            raise forms.ValidationError('Seu login nao esta vinculado a um gerente ativo.')
        if not origem or not destino or not gerente_destino:
            return cleaned
        if origem.pk == destino.pk:
            raise forms.ValidationError('Escolha duas datas diferentes para a troca.')
        if origem.s1_id != self.gerente_atual.id:
            raise forms.ValidationError('A escala de origem precisa estar atribuida a voce.')
        if destino.s1_id != gerente_destino.id:
            raise forms.ValidationError('A data escolhida nao pertence ao gerente selecionado.')

        pendentes = SolicitacaoTroca.objects.filter(
            status__in=[
                SolicitacaoTroca.STATUS_PENDENTE_DESTINO,
                SolicitacaoTroca.STATUS_PENDENTE_ADMIN,
            ],
        ).filter(
            Q(escala_origem=origem) | Q(escala_destino=origem) |
            Q(escala_origem=destino) | Q(escala_destino=destino)
        )
        if pendentes.exists():
            raise forms.ValidationError('Uma das datas ja possui solicitacao de troca pendente.')

        return cleaned


class GeracaoEscalaForm(forms.Form):
    """Form to trigger scale generation."""
    ano = forms.IntegerField(min_value=2024, max_value=2035, initial=2026)
    mes = forms.IntegerField(min_value=1, max_value=12)
    preservar_manuais = forms.BooleanField(
        required=False,
        initial=True,
        label='Preservar edicoes manuais',
    )
