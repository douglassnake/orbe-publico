# Implantação de homologação — ZimaOS

**Atenção: o Orbe Público ainda é um MVP demonstrativo. Não exponha à internet e não cadastre dados pessoais reais ou financeiros oficiais.** O roteiro não executa deploy no servidor automaticamente e não reutiliza nenhum banco de outros projetos.

## 1. Preparar diretório isolado

No terminal do NAS (com Docker e Compose já disponíveis):

```bash
cd /DATA/AppData
git clone https://github.com/douglassnake/orbe-publico.git orbe-publico
cd /DATA/AppData/orbe-publico
umask 077
cp .env.example .env
chmod 600 .env
```

Edite o arquivo `.env` localmente para configurar código e nome da entidade de teste, administrador fictício e valores fortes para `SECRET_KEY`, `POSTGRES_PASSWORD` e `BOOTSTRAP_ADMIN_PASSWORD`. **Jamais copie credenciais no chat, commit ou print.** Gere a chave:

```bash
python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
```

## 2. Validar e iniciar

```bash
docker compose config --quiet
docker compose up --build -d
docker compose ps
curl --fail http://127.0.0.1:8000/api/ready
docker compose logs --tail=100 api
```

Os serviços usam um volume exclusivo `orbe_pgdata`; a API só publica `127.0.0.1:8000` no host. Em máquinas onde esse endereço já está ocupado, altere apenas a porta de host do Orbe (não as portas dos sistemas existentes). **Não coloque um proxy público neste MVP.**

## 3. Backup e ensaio de restauração

```bash
export ORBE_BACKUP_DIR=/DATA/AppData/orbe-publico-backups
bash scripts/backup-db.sh
# escolha o .dump criado no diretório:
bash scripts/restore-check.sh /DATA/AppData/orbe-publico-backups/orbe-AAAA*.dump
```

O segundo script cria um banco temporário separado, restaura nele e o remove ao finalizar. Não modifica o banco principal. Guarde os backups fora do Git, de preferência criptografados, com retenção e cópia off-site. **Nunca rode `docker compose down -v` contra banco com dados.**

## 4. Atualização segura

Para qualquer atualização, registre a revisão instalada, confirme que o repositório não tem mudanças locais, realize backup e restore-check, depois atualize os arquivos e rode migrações na janela de manutenção. Uma migração de banco pode ser irreversível com dados; restore depende de procedimento planejado. Não execute `alembic downgrade` diretamente contra o volume persistente.

## 5. Limites de homologação

O fluxo ainda não oferece MFA, rate limiting perimetral, política de retenção LGPD, assinatura eletrônica, integrações PNCP/SIAFIC, nem homologação de contabilidade e folha. A prontidão operacional exige revisão de segurança, acessibilidade, atendimento normativo, testes com usuários, plano de continuidade e aceite formal.
