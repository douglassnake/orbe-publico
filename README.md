# Orbe Público — Gestão Municipal

**Sistema original de gestão municipal, em desenvolvimento.** Não possui vínculo comercial ou técnico com a Memory Informática. A análise do mercado e do REA é feita separadamente do código de produção.

> **MVP demonstrativo. Não utilizar em produção, dados pessoais reais, contabilidade oficial, folha de pagamento ou prestação de contas antes de auditoria de segurança e homologação normativa.**

## Funcionalidades iniciais

- Autenticação com senha PBKDF2, JWT expirável e segregação de dados por entidade
- Papéis admin, operador e leitor
- Protocolo com numeração, status e tramitação
- Cadastro de legislação, fornecedores e patrimônio
- Almoxarifado com histórico de movimentos e trava para saldo negativo
- Auditoria de alterações e painel de indicadores
- Interface responsiva, API OpenAPI/Swagger, PostgreSQL 16, Docker Compose e testes

## Executar localmente

1. Copie o arquivo de exemplo: cp .env.example .env
2. Gere uma chave para SECRET_KEY: python -c "import secrets; print(secrets.token_urlsafe(48))"
3. Troque as senhas de exemplo por segredos fortes: docker compose up --build -d
4. Abra http://127.0.0.1:8000 e acesse com os dados do bootstrap no arquivo .env.
5. Documentação da API: http://127.0.0.1:8000/docs. Saúde: /api/health.

O primeiro bootstrap cria o administrador somente se não houver entidades. Alterar as variáveis no .env não troca uma senha já gravada.

A porta é vinculada apenas a 127.0.0.1. Para publicar em rede, configurar proxy reverso HTTPS com proteção adicional. Não conectar este projeto ao banco de produção do Câmara360 ou de outros serviços.

## Testes

cd backend && python -m pip install -r requirements-dev.txt && pytest -q tests

## Roadmap

1. Migrations Alembic, autenticação robusta, proteção contra brute force e MFA
2. Permissões granulares por órgão, controle de documentos e assinaturas
3. Compras, licitações, contratos e controle interno
4. Integrações normativas, SIAFIC, contabilidade, folha e prestação de contas
5. Backup/restauração testados, monitoração, LGPD, revisão de segurança e acessibilidade

## REA

O [REA](https://github.com/morluto/rea) é uma **ferramenta separada de investigação funcional**, não é o código-base deste ERP. Em pesquisa autorizada, usar apenas informação pública ou ambiente de testes licenciado. Nunca contornar autenticação, extrair dados pessoais ou copiar código privado.

Ver docs/rea-investigacao.md.

## Aviso

O MVP não está homologado para uso governamental operacional. O banco usa Alembic (revisão inicial 20261015_0001). O startup Docker roda `alembic upgrade head` antes da API. Credenciais ficam no `.env` não versionado. Implantação em base anteriormente criada por `create_all` requer análise do esquema e backup antes de qualquer migração. Ainda faltam MFA, rate limiting perimetral, backup/restore ensaiados, privacidade e validação fiscal/jurídica.


## Migrações e sessões

No ambiente de desenvolvimento:

```bash
cd backend
export DATABASE_URL='sqlite:///./orbe-dev.db'
alembic upgrade head
alembic current
```

Para instalações Docker novas, a API aplica a migração antes de iniciar. **Não rode downgrade em banco contendo dados reais**. Senhas incorretas repetidas causam bloqueio da conta após cinco tentativas por 15 minutos; a revogação de sessões invalida todos os tokens daquele usuário, inclusive em outros dispositivos. Permanecem pendentes MFA, rate limit por IP/edge e hardening de produção.
