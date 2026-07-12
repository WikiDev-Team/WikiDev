# tests/test_crud.py
import pytest
from sqlmodel import Session, SQLModel, create_engine

from app.models import (
    User, UserCreate, 
    PageCreate, 
    PageBlockCreate, PageBlockType
)
from app.crud import create_user, create_page, create_page_block

# ... (Mantenha o engine, a fixture da session e o test_create_user aqui intactos) ...

# 1. Configurando o motor do SQLite em memória
sqlite_url = "sqlite:///:memory:"
engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})

@pytest.fixture(name="session")
def session_fixture():
    """
    Esta fixture equivale ao @Before e @After do JUnit.
    Tudo antes do 'yield' roda na inicialização. Tudo depois roda na limpeza.
    """
    # Cria todas as tabelas vazias na memória
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        yield session  # Entrega a sessão limpa para o teste usar
        
    # Limpa as tabelas da memória para não interferir no próximo teste
    SQLModel.metadata.drop_all(engine)


# 2. Escrevendo o Teste (Ciclo TDD)
def test_create_user_salva_no_banco_e_hashea_senha(session: Session):
    dados_usuario = UserCreate(
        username="ada_lovelace",
        email="ada@computacao.com",
        display_name="Ada",
        password="senha_super_secreta"
    )
    usuario_criado = create_user(session, dados_usuario)

    assert usuario_criado.id is not None
    assert usuario_criado.username == "ada_lovelace"
    assert usuario_criado.email == "ada@computacao.com"
    assert usuario_criado.hashed_password != "senha_super_secreta"
    assert len(usuario_criado.hashed_password) > 0

# Observe que a função abaixo está encostada na margem esquerda
def test_create_page_exige_autor_e_gera_slug(session: Session):
    # Senha ajustada para ter 6 caracteres
    autor = create_user(session, UserCreate(
        username="autor_regras", 
        email="regras@teste.com", 
        password="senha123" 
    ))

    dados_pagina = PageCreate(
        title="Regras de Qualquer Coisa",
        summary="Descrição aleatória.",
        author_id=autor.id,
        tag_ids=[] 
    )
    pagina = create_page(session, dados_pagina)

    assert pagina.id is not None
    assert pagina.author_id == autor.id
    assert pagina.slug == "regras-de-qualquer-coisa"

# Função também encostada na margem esquerda
def test_create_page_block_calcula_posicao_corretamente(session: Session):
    # Senha ajustada para ter 6 caracteres
    autor = create_user(session, UserCreate(
        username="dev_lisp", 
        email="lisp@teste.com", 
        password="senha123"
    ))
    
    pagina = create_page(session, PageCreate(
        title="Página de Blocos", 
        author_id=autor.id, 
        tag_ids=[]
    ))

    bloco_texto = create_page_block(session, pagina.id, PageBlockCreate(
        block_type=PageBlockType.TEXT,
        content="Introdução aos fundamentos."
    ))

    bloco_codigo = create_page_block(session, pagina.id, PageBlockCreate(
        block_type=PageBlockType.CODE,
        content="(print \"Hello World\")",
        language="lisp"
    ))

    assert bloco_texto.position == 0
    assert bloco_codigo.position == 1
    assert bloco_codigo.page_id == pagina.id
    assert bloco_codigo.language == "lisp"