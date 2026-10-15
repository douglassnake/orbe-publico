"""Solicitações de compras e contratos administrativos (sem efeitos contábeis)."""
from alembic import op
import sqlalchemy as sa

revision = "20261015_0002"
down_revision = "20261015_0001"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("compras",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entidade_id", sa.Integer(), sa.ForeignKey("entidades.id"), nullable=False),
        sa.Column("numero", sa.String(60), nullable=False),
        sa.Column("descricao", sa.String(250), nullable=False),
        sa.Column("justificativa", sa.Text(), nullable=False),
        sa.Column("solicitante", sa.String(150), nullable=False),
        sa.Column("valor_estimado", sa.Numeric(15, 2), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("criado_por", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("entidade_id", "numero"))
    op.create_index("ix_compras_entidade_id", "compras", ["entidade_id"])
    op.create_table("contratos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entidade_id", sa.Integer(), sa.ForeignKey("entidades.id"), nullable=False),
        sa.Column("numero", sa.String(60), nullable=False),
        sa.Column("objeto", sa.Text(), nullable=False),
        sa.Column("fornecedor_id", sa.Integer(), sa.ForeignKey("fornecedores.id"), nullable=False),
        sa.Column("valor_global", sa.Numeric(15, 2), nullable=False),
        sa.Column("vigencia_inicio", sa.Date(), nullable=False),
        sa.Column("vigencia_fim", sa.Date(), nullable=False),
        sa.Column("situacao", sa.String(30), nullable=False),
        sa.Column("registrado_por", sa.Integer(), sa.ForeignKey("usuarios.id"), nullable=False),
        sa.Column("criado_em", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("entidade_id", "numero"))
    op.create_index("ix_contratos_entidade_id", "contratos", ["entidade_id"])

def downgrade():
    op.drop_table("contratos")
    op.drop_table("compras")
