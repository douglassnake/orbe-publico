# Arquitetura inicial

- Frontend estático: HTML/CSS/JavaScript responsivo (servido pela API)
- Backend: FastAPI + Pydantic + SQLAlchemy
- Banco: PostgreSQL 16 (SQLite exclusivo para testes locais)
- Isolamento lógico: chave entidade_id nas tabelas de domínio e escopo obrigatório nas consultas.
- Autorização: admin, operador, leitor; autenticação por JWT assinado com chave de ambiente.
- Deploy de desenvolvimento: Docker Compose, porta em loopback.

**Não está pronto para produção**: faltam Alembic, isolamento multi-entidade formalmente auditado, MFA, limites de requisição, gerência de sessões, backups e restauração validados, segurança de dados, LGPD, observabilidade e homologação funcional/normativa.
