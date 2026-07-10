"""
Models for the Escala de Sobreaviso system.
"""
from datetime import timedelta

from django.conf import settings
from django.db import models


class GrupoEscala(models.Model):
    nome = models.CharField(max_length=50, unique=True)
    descricao = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Grupo de Escala'
        verbose_name_plural = 'Grupos de Escala'
        ordering = ['nome']

    def __str__(self):
        return f'Grupo {self.nome}'


class UsuarioEscala(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='usuario_escala', verbose_name='Usuário Django'
    )
    nome = models.CharField(max_length=120)
    codigo_legado = models.CharField(max_length=30, blank=True, verbose_name='Codigo legado')
    lotacao = models.CharField(max_length=40, blank=True, verbose_name='Lotacao')
    telefone = models.CharField(max_length=30, blank=True)
    grupo = models.ForeignKey(GrupoEscala, on_delete=models.PROTECT, related_name='usuarios')
    ativo = models.BooleanField(default=True)
    fer_inicial = models.PositiveIntegerField(default=0, verbose_name='FER inicial')
    pl_inicial = models.PositiveIntegerField(default=0, verbose_name='PL ate o corte')
    oportunidades_iniciais = models.PositiveIntegerField(
        default=0,
        verbose_name='Oportunidades ate o corte',
    )
    total_s1 = models.PositiveIntegerField(default=0)
    total_s2 = models.PositiveIntegerField(default=0)
    total_dias_trabalhados = models.PositiveIntegerField(default=0)
    total_dias_sobreaviso = models.PositiveIntegerField(default=0)
    total_feriados = models.PositiveIntegerField(default=0)
    total_feriadoes = models.PositiveIntegerField(default=0)
    feriadao_s1_count = models.PositiveIntegerField(default=0)
    feriadao_s2_count = models.PositiveIntegerField(default=0)
    ultima_escala = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Usuário da Escala'
        verbose_name_plural = 'Usuários da Escala'
        ordering = ['grupo__nome', 'nome']

    def __str__(self):
        return self.nome

    @property
    def plantoes_total(self):
        return self.total_s1 + self.total_s2


class BloqueioUsuario(models.Model):
    TIPO_CHOICES = [
        ('FERIAS', 'Férias'),
        ('FALTA', 'Falta'),
        ('TREINAMENTO', 'Treinamento'),
        ('LICENCA', 'Licença'),
        ('AFASTAMENTO', 'Afastamento'),
        ('INDISPONIBILIDADE', 'Indisponibilidade'),
        ('OUTRO', 'Outro'),
    ]
    usuario = models.ForeignKey(UsuarioEscala, on_delete=models.CASCADE, related_name='bloqueios')
    tipo = models.CharField(max_length=25, choices=TIPO_CHOICES, default='FERIAS')
    data_inicio = models.DateField()
    data_fim = models.DateField()
    motivo = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Bloqueio de Usuário'
        verbose_name_plural = 'Bloqueios de Usuários'
        ordering = ['-data_inicio']

    def __str__(self):
        return f'{self.usuario.nome} — {self.get_tipo_display()} ({self.data_inicio} a {self.data_fim})'


class Feriado(models.Model):
    TIPO_CHOICES = [
        ('NACIONAL', 'Nacional'),
        ('ESTADUAL', 'Estadual (Paraná)'),
        ('MUNICIPAL', 'Municipal (Curitiba)'),
        ('FACULTATIVO', 'Ponto Facultativo'),
        ('MANUAL', 'Manual / Empresa'),
    ]
    nome = models.CharField(max_length=200)
    data = models.DateField()
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='NACIONAL')
    ativo = models.BooleanField(default=True)
    recorrente = models.BooleanField(default=True, help_text='Repete todo ano')
    descricao = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Feriado'
        verbose_name_plural = 'Feriados'
        ordering = ['data']

    def __str__(self):
        return f'{self.nome} ({self.data})'


class Feriadao(models.Model):
    nome = models.CharField(max_length=200)
    data_inicio = models.DateField()
    data_fim = models.DateField()
    manual = models.BooleanField(default=False)
    observacao = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Feriadão'
        verbose_name_plural = 'Feriadões'
        ordering = ['data_inicio']

    def __str__(self):
        return f'{self.nome} ({self.data_inicio} a {self.data_fim})'

    @property
    def total_dias(self):
        return (self.data_fim - self.data_inicio).days + 1


class EscalaDia(models.Model):
    data = models.DateField(unique=True)
    s1 = models.ForeignKey(
        UsuarioEscala, on_delete=models.PROTECT,
        null=True, blank=True, related_name='escalas_s1'
    )
    s2 = models.ForeignKey(
        UsuarioEscala, on_delete=models.PROTECT,
        null=True, blank=True, related_name='escalas_s2'
    )
    STATUS_CHOICES = [
        ('AUTOMATICA', 'Automática'),
        ('MANUAL', 'Manual'),
        ('CONFIRMADA', 'Confirmada'),
        ('FECHADA', 'Fechada'),
        ('BLOQUEADA', 'Bloqueada'),
    ]
    dia_util = models.BooleanField(default=True)
    fim_de_semana = models.BooleanField(default=False)
    feriado = models.BooleanField(default=False)
    feriadao = models.BooleanField(default=False)
    manual = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='AUTOMATICA')
    editado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='edicoes_escala'
    )
    editado_em = models.DateTimeField(null=True, blank=True)
    observacao = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Dia da Escala'
        verbose_name_plural = 'Dias da Escala'
        ordering = ['data']

    def __str__(self):
        gerente = self.s1.nome if self.s1 else '---'
        return f'{self.data} | Sobreaviso: {gerente}'

    @property
    def tem_conflito(self):
        if self.s1:
            bloqueado = self.s1.bloqueios.filter(
                models.Q(data_inicio__lte=self.data) & models.Q(data_fim__gte=self.data)
            ).exists()
            if bloqueado:
                return True
            adjacente = EscalaDia.objects.filter(
                models.Q(data=self.data - timedelta(days=1)) |
                models.Q(data=self.data + timedelta(days=1)),
                s1=self.s1,
            ).exclude(pk=self.pk).exists()
            if adjacente:
                return True
        return False


class SolicitacaoTroca(models.Model):
    STATUS_PENDENTE_DESTINO = 'PENDENTE_DESTINO'
    STATUS_RECUSADA_DESTINO = 'RECUSADA_DESTINO'
    STATUS_PENDENTE_ADMIN = 'PENDENTE_ADMIN'
    STATUS_APROVADA = 'APROVADA'
    STATUS_REJEITADA_ADMIN = 'REJEITADA_ADMIN'
    STATUS_CANCELADA = 'CANCELADA'

    STATUS_CHOICES = [
        (STATUS_PENDENTE_DESTINO, 'Aguardando gerente destino'),
        (STATUS_RECUSADA_DESTINO, 'Recusada pelo gerente destino'),
        (STATUS_PENDENTE_ADMIN, 'Aguardando aprovacao do administrador'),
        (STATUS_APROVADA, 'Aprovada'),
        (STATUS_REJEITADA_ADMIN, 'Rejeitada pelo administrador'),
        (STATUS_CANCELADA, 'Cancelada'),
    ]

    solicitante_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitacoes_troca_criadas',
    )
    gerente_solicitante = models.ForeignKey(
        UsuarioEscala,
        on_delete=models.PROTECT,
        related_name='solicitacoes_troca_solicitante',
    )
    escala_origem = models.ForeignKey(
        EscalaDia,
        on_delete=models.PROTECT,
        related_name='solicitacoes_troca_origem',
    )
    gerente_origem = models.ForeignKey(
        UsuarioEscala,
        on_delete=models.PROTECT,
        related_name='solicitacoes_troca_origem',
    )
    escala_destino = models.ForeignKey(
        EscalaDia,
        on_delete=models.PROTECT,
        related_name='solicitacoes_troca_destino',
    )
    gerente_destino = models.ForeignKey(
        UsuarioEscala,
        on_delete=models.PROTECT,
        related_name='solicitacoes_troca_destino',
    )
    motivo = models.TextField(blank=True)
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_PENDENTE_DESTINO,
    )
    resposta_destino = models.TextField(blank=True)
    destino_respondido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitacoes_troca_respondidas_destino',
    )
    destino_respondido_em = models.DateTimeField(null=True, blank=True)
    resposta_admin = models.TextField(blank=True)
    admin_respondido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitacoes_troca_respondidas_admin',
    )
    admin_respondido_em = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Solicitacao de Troca'
        verbose_name_plural = 'Solicitacoes de Troca'
        ordering = ['-created_at']

    def __str__(self):
        return (
            f'Troca {self.escala_origem.data} ({self.gerente_origem.nome}) '
            f'por {self.escala_destino.data} ({self.gerente_destino.nome})'
        )


class EscalaBloco(models.Model):
    TIPO_CHOICES = [
        ('FIM_DE_SEMANA', 'Fim de Semana'),
        ('FERIADO', 'Feriado'),
        ('FERIADAO', 'Feriadão'),
    ]
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    data_inicio = models.DateField()
    data_fim = models.DateField()
    nome = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Bloco de Escala'
        verbose_name_plural = 'Blocos de Escala'
        ordering = ['data_inicio']

    def __str__(self):
        return f'{self.get_tipo_display()}: {self.data_inicio} a {self.data_fim}'


class HistoricoAlteracao(models.Model):
    TIPO_CHOICES = [
        ('EDICAO_DIA', 'Edição de dia'),
        ('TROCA_ESCALA', 'Troca de escala'),
        ('ADICAO_BLOQUEIO', 'Adição de bloqueio'),
        ('REMOCAO_BLOQUEIO', 'Remoção de bloqueio'),
        ('REGENERACAO', 'Regeneração da escala'),
        ('OUTRO', 'Outro'),
    ]
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='historico_alteracoes'
    )
    tipo = models.CharField(max_length=25, choices=TIPO_CHOICES)
    descricao = models.TextField()
    dados_anteriores = models.JSONField(null=True, blank=True)
    dados_novos = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Histórico de Alteração'
        verbose_name_plural = 'Histórico de Alterações'
        ordering = ['-created_at']

    def __str__(self):
        who = self.usuario.username if self.usuario else 'Sistema'
        return f'{self.get_tipo_display()} por {who} em {self.created_at:%d/%m/%Y %H:%M}'


class MesFechado(models.Model):
    """Tracks which months are locked/closed — cannot be auto-modified."""
    ano = models.IntegerField()
    mes = models.IntegerField()
    status = models.CharField(
        max_length=20,
        choices=[('FECHADO', 'Fechado'), ('BLOQUEADO', 'Bloqueado')],
        default='FECHADO'
    )
    fechado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='meses_fechados'
    )
    fechado_em = models.DateTimeField(auto_now_add=True)
    motivo = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Mês Fechado'
        verbose_name_plural = 'Meses Fechados'
        ordering = ['-ano', '-mes']
        constraints = [
            models.UniqueConstraint(fields=['ano', 'mes'], name='unique_mes_fechado')
        ]

    def __str__(self):
        return f'{self.mes:02d}/{self.ano} — {self.get_status_display()}'


class AlertaSistema(models.Model):
    """System alerts about scale issues."""
    TIPO_CHOICES = [
        ('SEM_GRUPO_A', 'Sem usuário disponível no Grupo A'),
        ('SEM_GRUPO_B', 'Sem usuário disponível no Grupo B'),
        ('PROXIMO_FERIAS', 'Escala próxima a férias'),
        ('FERIADO_REPETIDO', 'Feriado/Feriadão repetido'),
        ('DESEQUILIBRIO', 'Desequilíbrio acima do limite'),
        ('MANUAL_IMPEDE', 'Escala manual impede redistribuição'),
        ('MES_FECHADO', 'Mês fechado bloqueou alteração'),
        ('OUTRO', 'Outro'),
    ]
    tipo = models.CharField(max_length=25, choices=TIPO_CHOICES, default='OUTRO')
    data_referencia = models.DateField(null=True, blank=True)
    descricao = models.TextField()
    resolvido = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Alerta do Sistema'
        verbose_name_plural = 'Alertas do Sistema'
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.get_tipo_display()}] {self.descricao[:80]}'


class ConfiguracaoSistema(models.Model):
    chave = models.CharField(max_length=100, unique=True)
    valor = models.TextField()
    descricao = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Configuração do Sistema'
        verbose_name_plural = 'Configurações do Sistema'

    def __str__(self):
        return self.chave
