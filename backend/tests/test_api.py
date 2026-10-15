import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from alembic import command
from alembic.config import Config

_fd, _name = tempfile.mkstemp(suffix=".db")
os.close(_fd)
os.environ["DATABASE_URL"] = "sqlite:///" + _name
os.environ["SECRET_KEY"] = "chave-exclusiva-para-testes-" + "x" * 48
os.environ["BOOTSTRAP_ENTIDADE_CODIGO"] = "municipio-teste"
os.environ["BOOTSTRAP_ENTIDADE_NOME"] = "Município de Teste"
os.environ["BOOTSTRAP_ADMIN_EMAIL"] = "gestor@teste.gov.br"
os.environ["BOOTSTRAP_ADMIN_PASSWORD"] = "senha-muito-forte-123"

from app import app, Entidade, Usuario, SessionLocal, password_hash

@pytest.fixture(scope="module")
def client():
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    command.upgrade(cfg, "head")
    with TestClient(app) as c:
        yield c
    Path(_name).unlink(missing_ok=True)

def auth(client, codigo="municipio-teste", email="gestor@teste.gov.br", senha="senha-muito-forte-123"):
    response = client.post("/api/auth/login", json={"entidade":codigo,"email":email,"senha":senha})
    assert response.status_code == 200, response.text
    return {"Authorization":"Bearer "+response.json()["access_token"]}

def test_health_and_auth(client):
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/protocolos").status_code == 401
    assert client.post("/api/auth/login",json={"entidade":"municipio-teste","email":"gestor@teste.gov.br","senha":"errada"}).status_code == 401
    assert client.get("/api/auth/me",headers=auth(client)).status_code == 200

def test_protocol_and_tenant_isolation(client):
    h=auth(client)
    response=client.post("/api/protocolos",headers=h,json={"assunto":"Pedido de material","requerente":"Cidadão","setor_atual":"Protocolo"})
    assert response.status_code == 201,response.text
    pid=response.json()["id"]
    assert client.post(f"/api/protocolos/{pid}/tramitar",headers=h,json={"destino":"Secretaria","observacao":"Análise"}).status_code == 201
    assert client.get(f"/api/protocolos/{pid}",headers=h).json()["protocolo"]["setor_atual"]=="Secretaria"
    with SessionLocal() as db:
        e=Entidade(codigo="outra-entidade",nome="Outra Entidade")
        db.add(e); db.flush()
        db.add(Usuario(entidade_id=e.id, email="admin@outra.gov.br",nome="Outro administrador",perfil="admin",senha_hash=password_hash("senha-outra-muito-forte")))
        db.commit()
    other=auth(client,"outra-entidade","admin@outra.gov.br","senha-outra-muito-forte")
    assert client.get(f"/api/protocolos/{pid}",headers=other).status_code == 404
    assert client.get("/api/protocolos",headers=other).json()==[]

def test_roles_and_inventory(client):
    h=auth(client)
    assert client.post("/api/admin/usuarios",headers=h,json={"nome":"Leitor de teste","email":"leitor@teste.gov.br","perfil":"leitor","senha":"senha-leitor-forte"}).status_code==201
    reader=auth(client,"municipio-teste","leitor@teste.gov.br","senha-leitor-forte")
    assert client.get("/api/auditoria",headers=reader).status_code == 403
    assert client.post("/api/leis",headers=reader,json={"tipo":"Lei","numero":"1","ano":2026,"ementa":"Lei de teste"}).status_code == 403
    response=client.post("/api/estoque",headers=h,json={"codigo":"001","descricao":"Papel sulfite","unidade":"pct"})
    assert response.status_code==201,response.text
    iid=response.json()["id"]
    assert client.post(f"/api/estoque/{iid}/movimentos",headers=h,json={"quantidade":"10","motivo":"Compra"}).status_code==201
    assert client.post(f"/api/estoque/{iid}/movimentos",headers=h,json={"quantidade":"-11","motivo":"Saída"}).status_code==409
    assert client.post(f"/api/estoque/{iid}/movimentos",headers=h,json={"quantidade":"-4","motivo":"Consumo"}).json()["saldo"]=="6.000"


def test_duplicate_supplier_and_audit(client):
    h=auth(client)
    payload={"nome":"Fornecedor Exemplo","documento":"12345678900","email":"contato@exemplo.com"}
    assert client.post("/api/fornecedores",headers=h,json=payload).status_code==201
    assert client.post("/api/fornecedores",headers=h,json=payload).status_code==409
    records=client.get("/api/auditoria",headers=h)
    assert records.status_code==200
    assert len(records.json())>=3

def test_status_transition_and_revocation(client):
    h=auth(client)
    p=client.post("/api/protocolos",headers=h,json={"assunto":"Encerrar protocolo","requerente":"Pessoa","setor_atual":"Setor inicial"})
    assert p.status_code == 201, p.text
    pid=p.json()["id"]
    assert client.patch(f"/api/protocolos/{pid}/status",headers=h,json={"status":"concluido"}).status_code==200
    assert client.patch(f"/api/protocolos/{pid}/status",headers=h,json={"status":"aberto"}).status_code==409
    assert client.post(f"/api/protocolos/{pid}/tramitar",headers=h,json={"destino":"Outro setor"}).status_code==409
    assert client.post("/api/auth/revogar-sessoes",headers=h).status_code==200
    assert client.get("/api/auth/me",headers=h).status_code==401
    assert client.get("/api/auth/me",headers=auth(client)).status_code==200


def test_login_lockout(client):
    h=auth(client)
    response=client.post("/api/admin/usuarios",headers=h,json={
        "nome":"Conta de bloqueio", "email":"bloqueio@teste.gov.br",
        "perfil":"leitor", "senha":"senha-bloqueio-forte"
    })
    assert response.status_code==201
    for _ in range(5):
        response=client.post("/api/auth/login",json={
            "entidade":"municipio-teste","email":"bloqueio@teste.gov.br","senha":"incorreta"})
        assert response.status_code==401
    response=client.post("/api/auth/login",json={
        "entidade":"municipio-teste","email":"bloqueio@teste.gov.br","senha":"senha-bloqueio-forte"})
    assert response.status_code==401


def test_compras_contratos_mesma_entidade(client):
    h=auth(client)
    fornecedor=client.post("/api/fornecedores",headers=h,json={
        "nome":"Fornecedor contrato", "documento":"99887766000188"}).json()
    compra=client.post("/api/compras",headers=h,json={
        "descricao":"Serviço de manutenção", "justificativa":"Manutenção preventiva do patrimônio",
        "solicitante":"Administração", "valor_estimado":"2500.00"})
    assert compra.status_code==201,compra.text
    cid=compra.json()["id"]
    assert compra.json()["numero"].startswith("SC-")
    assert client.patch(f"/api/compras/{cid}/status",headers=h,json={"status":"aprovada"}).status_code==409
    assert client.patch(f"/api/compras/{cid}/status",headers=h,json={"status":"em_analise"}).status_code==200
    assert client.patch(f"/api/compras/{cid}/status",headers=h,json={"status":"aprovada"}).status_code==200
    assert client.patch(f"/api/compras/{cid}/status",headers=h,json={"status":"aberta"}).status_code==409
    bad=client.post("/api/contratos",headers=h,json={
        "numero":"001/2026","objeto":"Manutenção de instalações",
        "fornecedor_id":999999,"valor_global":"1000.00",
        "vigencia_inicio":"2026-11-01","vigencia_fim":"2026-12-31"})
    assert bad.status_code==404
    payload={"numero":"001/2026","objeto":"Manutenção de instalações",
             "fornecedor_id":fornecedor["id"],"valor_global":"1000.00",
             "vigencia_inicio":"2026-11-01","vigencia_fim":"2026-12-31"}
    assert client.post("/api/contratos",headers=h,json={**payload,
        "vigencia_fim":"2026-10-01"}).status_code==422
    ok=client.post("/api/contratos",headers=h,json=payload)
    assert ok.status_code==201,ok.text
    assert client.post("/api/contratos",headers=h,json=payload).status_code==409
    assert len(client.get("/api/contratos",headers=h).json())==1
    assert client.get("/api/resumo",headers=h).json()["compras"]>=1
    reader=auth(client,"municipio-teste","leitor@teste.gov.br","senha-leitor-forte")
    assert client.post("/api/contratos",headers=reader,json=payload).status_code==403
    assert client.patch(f"/api/compras/{cid}/status",headers=reader,json={"status":"rejeitada"}).status_code==403
    other=auth(client,"outra-entidade","admin@outra.gov.br","senha-outra-muito-forte")
    assert client.get("/api/contratos",headers=other).json()==[]
    assert client.post("/api/contratos",headers=other,json=payload).status_code==404
