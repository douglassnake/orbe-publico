import base64
import hashlib
import hmac
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Literal

import jwt
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./orbe.db")
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal = sessionmaker(engine, expire_on_commit=False)
bearer = HTTPBearer(auto_error=False)

def utcnow():
    return datetime.now(timezone.utc)

class Base(DeclarativeBase):
    pass

class Entidade(Base):
    __tablename__ = "entidades"
    id = Column(Integer, primary_key=True)
    codigo = Column(String(50), unique=True, nullable=False)
    nome = Column(String(200), nullable=False)

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True)
    entidade_id = Column(Integer, ForeignKey("entidades.id"), nullable=False, index=True)
    email = Column(String(255), nullable=False)
    nome = Column(String(150), nullable=False)
    senha_hash = Column(String(255), nullable=False)
    perfil = Column(String(20), nullable=False, default="leitor")
    ativo = Column(Integer, nullable=False, default=1)
    token_versao = Column(Integer, nullable=False, default=0)
    falhas_login = Column(Integer, nullable=False, default=0)
    bloqueado_ate = Column(DateTime(timezone=True), nullable=True)
    __table_args__ = (UniqueConstraint("entidade_id", "email"),)

class Protocolo(Base):
    __tablename__ = "protocolos"
    id = Column(Integer, primary_key=True)
    entidade_id = Column(Integer, ForeignKey("entidades.id"), nullable=False, index=True)
    numero = Column(String(60), nullable=False)
    assunto = Column(String(250), nullable=False)
    descricao = Column(Text, nullable=False, default="")
    requerente = Column(String(200), nullable=False)
    setor_atual = Column(String(100), nullable=False)
    status = Column(String(30), nullable=False, default="aberto")
    criado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    criado_em = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    __table_args__ = (UniqueConstraint("entidade_id", "numero"),)

class Tramite(Base):
    __tablename__ = "tramites"
    id = Column(Integer, primary_key=True)
    entidade_id = Column(Integer, ForeignKey("entidades.id"), nullable=False, index=True)
    protocolo_id = Column(Integer, ForeignKey("protocolos.id"), nullable=False)
    origem = Column(String(100), nullable=False)
    destino = Column(String(100), nullable=False)
    observacao = Column(Text, nullable=False, default="")
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    criado_em = Column(DateTime(timezone=True), default=utcnow, nullable=False)

class Lei(Base):
    __tablename__ = "leis"
    id = Column(Integer, primary_key=True)
    entidade_id = Column(Integer, ForeignKey("entidades.id"), nullable=False, index=True)
    tipo = Column(String(80), nullable=False)
    numero = Column(String(50), nullable=False)
    ano = Column(Integer, nullable=False)
    ementa = Column(Text, nullable=False)
    __table_args__ = (UniqueConstraint("entidade_id", "tipo", "numero", "ano"),)

class Fornecedor(Base):
    __tablename__ = "fornecedores"
    id = Column(Integer, primary_key=True)
    entidade_id = Column(Integer, ForeignKey("entidades.id"), nullable=False, index=True)
    nome = Column(String(220), nullable=False)
    documento = Column(String(30), nullable=False)
    email = Column(String(255))
    __table_args__ = (UniqueConstraint("entidade_id", "documento"),)

class Bem(Base):
    __tablename__ = "bens"
    id = Column(Integer, primary_key=True)
    entidade_id = Column(Integer, ForeignKey("entidades.id"), nullable=False, index=True)
    tombamento = Column(String(70), nullable=False)
    descricao = Column(String(250), nullable=False)
    localizacao = Column(String(150), nullable=False)
    valor_aquisicao = Column(Numeric(15, 2), nullable=False)
    __table_args__ = (UniqueConstraint("entidade_id", "tombamento"),)

class Item(Base):
    __tablename__ = "estoque"
    id = Column(Integer, primary_key=True)
    entidade_id = Column(Integer, ForeignKey("entidades.id"), nullable=False, index=True)
    codigo = Column(String(60), nullable=False)
    descricao = Column(String(250), nullable=False)
    unidade = Column(String(30), nullable=False, default="un")
    saldo = Column(Numeric(15, 3), nullable=False, default=Decimal("0"))
    __table_args__ = (UniqueConstraint("entidade_id", "codigo"),)

class Movimento(Base):
    __tablename__ = "movimentos"
    id = Column(Integer, primary_key=True)
    entidade_id = Column(Integer, ForeignKey("entidades.id"), nullable=False)
    item_id = Column(Integer, ForeignKey("estoque.id"), nullable=False)
    quantidade = Column(Numeric(15, 3), nullable=False)
    motivo = Column(String(250), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    criado_em = Column(DateTime(timezone=True), default=utcnow, nullable=False)

class Auditoria(Base):
    __tablename__ = "auditoria"
    id = Column(Integer, primary_key=True)
    entidade_id = Column(Integer, ForeignKey("entidades.id"), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    recurso = Column(String(60), nullable=False)
    recurso_id = Column(Integer, nullable=False)
    acao = Column(String(50), nullable=False)
    resumo = Column(String(250), nullable=False)
    criado_em = Column(DateTime(timezone=True), default=utcnow, nullable=False)

class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

class Login(Input):
    entidade: str
    email: str
    senha: str

class NovoUsuario(Input):
    email: str
    nome: str = Field(min_length=2)
    senha: str = Field(min_length=12)
    perfil: Literal["admin", "operador", "leitor"]

class NovoProtocolo(Input):
    assunto: str = Field(min_length=3, max_length=250)
    descricao: str = Field(default="", max_length=10000)
    requerente: str = Field(min_length=2, max_length=200)
    setor_atual: str = Field(min_length=2, max_length=100)

class NovoTramite(Input):
    destino: str = Field(min_length=2, max_length=100)
    observacao: str = Field(default="", max_length=2000)

class NovoStatus(Input):
    status: Literal["aberto", "em_andamento", "concluido", "cancelado"]

class NovaLei(Input):
    tipo: str = Field(min_length=2)
    numero: str = Field(min_length=1)
    ano: int = Field(ge=1900, le=2100)
    ementa: str = Field(min_length=3)

class NovoFornecedor(Input):
    nome: str = Field(min_length=2)
    documento: str = Field(min_length=5)
    email: str | None = None

class NovoBem(Input):
    tombamento: str = Field(min_length=1)
    descricao: str = Field(min_length=3)
    localizacao: str = Field(min_length=2)
    valor_aquisicao: Decimal = Field(ge=0, max_digits=15, decimal_places=2)

class NovoItem(Input):
    codigo: str = Field(min_length=1)
    descricao: str = Field(min_length=3)
    unidade: str = "un"

class NovoMovimento(Input):
    quantidade: Decimal = Field(max_digits=15, decimal_places=3)
    motivo: str = Field(min_length=3)

def secret():
    value = os.getenv("SECRET_KEY", "")
    if len(value) < 32 or value.startswith("SUBSTITUA"):
        raise RuntimeError("SECRET_KEY precisa ser aleatória e ter pelo menos 32 caracteres")
    return value

def password_hash(password):
    if len(password) < 12:
        raise ValueError("Senha curta")
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 300000)
    return "pbkdf2_sha256$300000$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(key).decode()

def password_matches(password, stored):
    try:
        alg, rounds, salt, key = stored.split("$")
        if alg != "pbkdf2_sha256":
            return False
        computed = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.b64decode(salt), int(rounds))
        return hmac.compare_digest(computed, base64.b64decode(key))
    except (ValueError, TypeError):
        return False

DUMMY_PASSWORD_HASH = password_hash("senha-ficticia-sem-usuario")

def safe_flush(db):
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Identificador duplicado nesta entidade") from exc

def initialize():
    secret()
    # O esquema é provisionado exclusivamente por `alembic upgrade head`.
    with SessionLocal() as db:
        if db.scalar(select(func.count()).select_from(Entidade)):
            return
        required = ["BOOTSTRAP_ENTIDADE_CODIGO", "BOOTSTRAP_ENTIDADE_NOME", "BOOTSTRAP_ADMIN_EMAIL", "BOOTSTRAP_ADMIN_PASSWORD"]
        if any(not os.getenv(k) or os.getenv(k, "").startswith("SUBSTITUA") for k in required):
            raise RuntimeError("Defina as variáveis de bootstrap no arquivo .env")
        e = Entidade(codigo=os.environ[required[0]], nome=os.environ[required[1]])
        db.add(e)
        safe_flush(db)
        db.add(Usuario(entidade_id=e.id, email=os.environ[required[2]].lower(), nome="Administrador", perfil="admin", senha_hash=password_hash(os.environ[required[3]])))
        db.commit()

@asynccontextmanager
async def lifespan(app):
    initialize()
    yield

app = FastAPI(title="Orbe Público - MVP", version="0.1.0", lifespan=lifespan)

def session():
    with SessionLocal() as db:
        yield db

def current(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(session)):
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(401, "Autenticação obrigatória")
    try:
        data = jwt.decode(credentials.credentials, secret(), algorithms=["HS256"], options={"require": ["sub", "tenant", "exp"]})
        user = db.get(Usuario, int(data["sub"]))
        if user is None or not user.ativo or user.entidade_id != data["tenant"] or data.get("tv") != user.token_versao:
            raise ValueError("Principal inválido")
    except (jwt.PyJWTError, ValueError, KeyError, TypeError):
        raise HTTPException(401, "Token inválido ou expirado")
    return user

def writer(u: Usuario = Depends(current)):
    if u.perfil not in ("admin", "operador"):
        raise HTTPException(403, "Perfil sem permissão de escrita")
    return u

def admin(u: Usuario = Depends(current)):
    if u.perfil != "admin":
        raise HTTPException(403, "Exige administrador")
    return u

def save(db, item):
    try:
        db.commit()
        db.refresh(item)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Identificador duplicado nesta entidade") from exc
    return jsonable_encoder(item)

def audit(db, u, model, item_id, action, summary):
    db.add(Auditoria(entidade_id=u.entidade_id, usuario_id=u.id, recurso=model, recurso_id=item_id, acao=action, resumo=summary[:250]))

def owned(db, model, u, item_id, lock=False):
    query = select(model).where(model.id == item_id, model.entidade_id == u.entidade_id)
    if lock and db.bind.dialect.name != "sqlite":
        query = query.with_for_update()
    item = db.scalar(query)
    if item is None:
        raise HTTPException(404, "Registro não encontrado")
    return item

def listed(db, model, u, limit, offset):
    return jsonable_encoder(db.scalars(select(model).where(model.entidade_id == u.entidade_id).order_by(model.id.desc()).limit(limit).offset(offset)).all())

@app.get("/api/health")
def health():
    return {"status": "ok", "version": app.version}

@app.post("/api/auth/login")
def login(body: Login, db: Session = Depends(session)):
    tenant = db.scalar(select(Entidade).where(Entidade.codigo == body.entidade))
    user = db.scalar(select(Usuario).where(Usuario.entidade_id == tenant.id, Usuario.email == body.email.lower())) if tenant else None
    if user is None:
        password_matches(body.senha, DUMMY_PASSWORD_HASH)  # Uniformiza o trabalho criptográfico.
        raise HTTPException(401, "Credenciais inválidas")
    until = user.bloqueado_ate
    if until is not None:
        until = until.replace(tzinfo=timezone.utc) if until.tzinfo is None else until
    if until is not None and until > utcnow():
        raise HTTPException(401, "Credenciais inválidas")
    if not user.ativo or not password_matches(body.senha, user.senha_hash):
        if user.ativo:
            user.falhas_login += 1
            if user.falhas_login >= 5:
                user.bloqueado_ate = utcnow() + timedelta(minutes=15)
            db.commit()
        raise HTTPException(401, "Credenciais inválidas")
    if user.falhas_login or user.bloqueado_ate is not None:
        user.falhas_login, user.bloqueado_ate = 0, None
        db.commit()
    token = jwt.encode({"sub": str(user.id), "tenant": tenant.id, "tv": user.token_versao, "exp": utcnow() + timedelta(hours=1)}, secret(), algorithm="HS256")
    return {"access_token": token, "token_type": "bearer", "nome": user.nome, "perfil": user.perfil, "entidade": tenant.nome}

@app.get("/api/auth/me")
def me(u: Usuario = Depends(current)):
    return {"id": u.id, "nome": u.nome, "email": u.email, "perfil": u.perfil, "entidade_id": u.entidade_id}

@app.post("/api/auth/revogar-sessoes")
def revogar_sessoes(u: Usuario = Depends(current), db: Session = Depends(session)):
    registro = owned(db, Usuario, u, u.id, lock=True)
    registro.token_versao += 1
    audit(db, u, "usuarios", u.id, "revogar_sessoes", "Revogação global pelo usuário")
    save(db, registro)
    return {"revogado": True}

@app.post("/api/admin/usuarios", status_code=201)
def create_user(body: NovoUsuario, u: Usuario = Depends(admin), db: Session = Depends(session)):
    item = Usuario(entidade_id=u.entidade_id, email=body.email.lower(), nome=body.nome, senha_hash=password_hash(body.senha), perfil=body.perfil)
    db.add(item)
    safe_flush(db)
    audit(db, u, "usuarios", item.id, "criar", item.email)
    save(db, item)
    return {"id": item.id, "nome": item.nome, "email": item.email, "perfil": item.perfil}

@app.get("/api/resumo")
def resumo(u: Usuario = Depends(current), db: Session = Depends(session)):
    return {key: db.scalar(select(func.count()).select_from(model).where(model.entidade_id == u.entidade_id)) for key, model in [("protocolos", Protocolo), ("leis", Lei), ("fornecedores", Fornecedor), ("bens", Bem), ("estoque", Item)]}

@app.get("/api/protocolos")
def protocolos(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), u: Usuario = Depends(current), db: Session = Depends(session)):
    return listed(db, Protocolo, u, limit, offset)

@app.post("/api/protocolos", status_code=201)
def novo_protocolo(body: NovoProtocolo, u: Usuario = Depends(writer), db: Session = Depends(session)):
    item = Protocolo(entidade_id=u.entidade_id, numero="tmp-" + os.urandom(12).hex(), criado_por=u.id, **body.model_dump())
    db.add(item)
    safe_flush(db)
    item.numero = f"{utcnow().year}/{item.id:06d}"
    audit(db, u, "protocolos", item.id, "criar", item.assunto)
    return save(db, item)

@app.get("/api/protocolos/{pid}")
def detalhar(pid: int, u: Usuario = Depends(current), db: Session = Depends(session)):
    item = owned(db, Protocolo, u, pid)
    return {"protocolo": jsonable_encoder(item), "tramites": jsonable_encoder(db.scalars(select(Tramite).where(Tramite.entidade_id == u.entidade_id, Tramite.protocolo_id == item.id).order_by(Tramite.id)).all())}

@app.post("/api/protocolos/{pid}/tramitar", status_code=201)
def tramitar(pid: int, body: NovoTramite, u: Usuario = Depends(writer), db: Session = Depends(session)):
    item = owned(db, Protocolo, u, pid, lock=True)
    if item.status in ("concluido", "cancelado"):
        raise HTTPException(409, "Protocolo encerrado")
    mov = Tramite(entidade_id=u.entidade_id, protocolo_id=pid, origem=item.setor_atual, destino=body.destino, observacao=body.observacao, usuario_id=u.id)
    db.add(mov)
    item.setor_atual = body.destino
    item.status = "em_andamento"
    safe_flush(db)
    audit(db, u, "protocolos", pid, "tramitar", body.destino)
    return save(db, mov)

@app.patch("/api/protocolos/{pid}/status")
def status_protocolo(pid: int, body: NovoStatus, u: Usuario = Depends(writer), db: Session = Depends(session)):
    item = owned(db, Protocolo, u, pid, lock=True)
    permitted = {"aberto": {"em_andamento", "concluido", "cancelado"}, "em_andamento": {"concluido", "cancelado"}, "concluido": set(), "cancelado": set()}
    if body.status not in permitted[item.status]:
        raise HTTPException(409, "Transição de status não permitida")
    item.status = body.status
    audit(db, u, "protocolos", pid, "status", body.status)
    return save(db, item)

@app.get("/api/leis")
def leis(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), u: Usuario = Depends(current), db: Session = Depends(session)):
    return listed(db, Lei, u, limit, offset)

@app.post("/api/leis", status_code=201)
def nova_lei(body: NovaLei, u: Usuario = Depends(writer), db: Session = Depends(session)):
    item = Lei(entidade_id=u.entidade_id, **body.model_dump())
    db.add(item)
    safe_flush(db)
    audit(db, u, "leis", item.id, "criar", item.ementa)
    return save(db, item)

@app.get("/api/fornecedores")
def fornecedores(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), u: Usuario = Depends(current), db: Session = Depends(session)):
    return listed(db, Fornecedor, u, limit, offset)

@app.post("/api/fornecedores", status_code=201)
def novo_fornecedor(body: NovoFornecedor, u: Usuario = Depends(writer), db: Session = Depends(session)):
    item = Fornecedor(entidade_id=u.entidade_id, **body.model_dump())
    db.add(item)
    safe_flush(db)
    audit(db, u, "fornecedores", item.id, "criar", item.nome)
    return save(db, item)

@app.get("/api/bens")
def bens(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), u: Usuario = Depends(current), db: Session = Depends(session)):
    return listed(db, Bem, u, limit, offset)

@app.post("/api/bens", status_code=201)
def novo_bem(body: NovoBem, u: Usuario = Depends(writer), db: Session = Depends(session)):
    item = Bem(entidade_id=u.entidade_id, **body.model_dump())
    db.add(item)
    safe_flush(db)
    audit(db, u, "bens", item.id, "criar", item.tombamento)
    return save(db, item)

@app.get("/api/estoque")
def estoque(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), u: Usuario = Depends(current), db: Session = Depends(session)):
    return listed(db, Item, u, limit, offset)

@app.post("/api/estoque", status_code=201)
def novo_item(body: NovoItem, u: Usuario = Depends(writer), db: Session = Depends(session)):
    item = Item(entidade_id=u.entidade_id, **body.model_dump())
    db.add(item)
    safe_flush(db)
    audit(db, u, "estoque", item.id, "criar", item.codigo)
    return save(db, item)

@app.post("/api/estoque/{iid}/movimentos", status_code=201)
def movimentar(iid: int, body: NovoMovimento, u: Usuario = Depends(writer), db: Session = Depends(session)):
    item = owned(db, Item, u, iid, lock=True)
    if body.quantidade == 0:
        raise HTTPException(422, "Quantidade deve ser diferente de zero")
    if item.saldo + body.quantidade < 0:
        raise HTTPException(409, "Saldo insuficiente")
    item.saldo += body.quantidade
    mov = Movimento(entidade_id=u.entidade_id, item_id=iid, quantidade=body.quantidade, motivo=body.motivo, usuario_id=u.id)
    db.add(mov)
    safe_flush(db)
    audit(db, u, "estoque", iid, "movimentar", body.motivo)
    result = save(db, mov)
    return {"movimento": result, "saldo": str(item.saldo)}

@app.get("/api/auditoria")
def auditoria(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), u: Usuario = Depends(admin), db: Session = Depends(session)):
    return listed(db, Auditoria, u, limit, offset)

@app.get("/")
def index():
    return FileResponse("static/index.html")

@app.get("/static/app.js")
def js():
    return FileResponse("static/app.js", media_type="application/javascript")
