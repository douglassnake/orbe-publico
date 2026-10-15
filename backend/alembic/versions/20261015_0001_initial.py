"""Esquema inicial do MVP Orbe Público (sem dados de demonstração)."""
from alembic import op
import sqlalchemy as sa

revision = "20261015_0001"
down_revision = None
branch_labels = None
depends_on = None

def tenant():
    return sa.Column("entidade_id", sa.Integer(), sa.ForeignKey("entidades.id"), nullable=False)

def upgrade():
    op.create_table("entidades",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("codigo", sa.String(50), nullable=False, unique=True),
        sa.Column("nome", sa.String(200), nullable=False))
    op.create_table("usuarios",
        sa.Column("id", sa.Integer(), primary_key=True),
        tenant(), sa.Column("email", sa.String(255), nullable=False),
        sa.Column("nome", sa.String(150), nullable=False),
        sa.Column("senha_hash", sa.String(255), nullable=False),
        sa.Column("perfil", sa.String(20), nullable=False),
        sa.Column("ativo", sa.Integer(), nullable=False),
        sa.Column("token_versao", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("falhas_login", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bloqueado_ate", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("entidade_id", "email"))
    op.create_index("ix_usuarios_entidade_id", "usuarios", ["entidade_id"])
    op.create_table("protocolos",
        sa.Column("id", sa.Integer(), primary_key=True),
        tenant(), sa.Column("numero", sa.String(60), nullable=False),
        sa.Column("assunto", sa.String(250), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("requerente", sa.String(200), nullable=False),
        sa.Column("setor_atual", sa.String(100), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("criado_por", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("entidade_id", "numero"))
    op.create_index("ix_protocolos_entidade_id", "protocolos", ["entidade_id"])
    op.create_table("tramites",
        sa.Column("id", sa.Integer(), primary_key=True),
        tenant(), sa.Column("protocolo_id", sa.Integer(), sa.ForeignKey("protocolos.id"), nullable=False),
        sa.Column("origem", sa.String(100), nullable=False),
        sa.Column("destino", sa.String(100), nullable=False),
        sa.Column("observacao", sa.Text(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_tramites_entidade_id", "tramites", ["entidade_id"])
    op.create_table("leis",
        sa.Column("id", sa.Integer(), primary_key=True),
        tenant(), sa.Column("tipo", sa.String(80), nullable=False),
        sa.Column("numero", sa.String(50), nullable=False),
        sa.Column("ano", sa.Integer(), nullable=False),
        sa.Column("ementa", sa.Text(), nullable=False),
        sa.UniqueConstraint("entidade_id", "tipo", "numero", "ano"))
    op.create_index("ix_leis_entidade_id", "leis", ["entidade_id"])
    op.create_table("fornecedores",
        sa.Column("id", sa.Integer(), primary_key=True),
        tenant(), sa.Column("nome", sa.String(220), nullable=False),
        sa.Column("documento", sa.String(30), nullable=False),
        sa.Column("email", sa.String(255)),
        sa.UniqueConstraint("entidade_id", "documento"))
    op.create_index("ix_fornecedores_entidade_id", "fornecedores", ["entidade_id"])
    op.create_table("bens",
        sa.Column("id", sa.Integer(), primary_key=True),
        tenant(), sa.Column("tombamento", sa.String(70), nullable=False),
        sa.Column("descricao", sa.String(250), nullable=False),
        sa.Column("localizacao", sa.String(150), nullable=False),
        sa.Column("valor_aquisicao", sa.Numeric(15,2), nullable=False),
        sa.UniqueConstraint("entidade_id", "tombamento"))
    op.create_index("ix_bens_entidade_id", "bens", ["entidade_id"])
    op.create_table("estoque",
        sa.Column("id", sa.Integer(), primary_key=True),
        tenant(), sa.Column("codigo", sa.String(60), nullable=False),
        sa.Column("descricao", sa.String(250), nullable=False),
        sa.Column("unidade", sa.String(30), nullable=False),
        sa.Column("saldo", sa.Numeric(15,3), nullable=False),
        sa.UniqueConstraint("entidade_id", "codigo"))
    op.create_index("ix_estoque_entidade_id", "estoque", ["entidade_id"])
    op.create_table("movimentos",
        sa.Column("id", sa.Integer(), primary_key=True),
        tenant(), sa.Column("item_id", sa.Integer(), sa.ForeignKey("estoque.id"), nullable=False),
        sa.Column("quantidade", sa.Numeric(15,3), nullable=False),
        sa.Column("motivo", sa.String(250), nullable=False),
        sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False))
    op.create_table("auditoria",
        sa.Column("id", sa.Integer(), primary_key=True),
        tenant(), sa.Column("usuario_id", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("recurso", sa.String(60), nullable=False),
        sa.Column("recurso_id", sa.Integer(), nullable=False),
        sa.Column("acao", sa.String(50), nullable=False),
        sa.Column("resumo", sa.String(250), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False))
    op.create_index("ix_auditoria_entidade_id", "auditoria", ["entidade_id"])

def downgrade():
    for name in ("auditoria", "movimentos", "estoque", "bens", "fornecedores", "leis", "tramites", "protocolos", "usuarios", "entidades"):
        op.drop_table(name)
