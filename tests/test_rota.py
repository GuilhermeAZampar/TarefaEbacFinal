import sys
import os
import pytest

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from fastapi.testclient import TestClient
from main import Base,sessao_db,PokemonDB,app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL_TEST="sqlite:///:memory:"
engine=create_engine(DATABASE_URL_TEST,connect_args={"check_same_thread":False})
TestSessionLocal=sessionmaker(autocommit=False,autoflush=False,bind=engine)
Base.metadata.create_all(bind=engine)


@pytest.fixture(autouse=True)
def mocker_redis(mocker):
    redis_client_mocker=mocker.patch("main.redis_client",autospec=True)
    redis_client_mocker.get.return_value=None


@pytest.fixture(scope="function")
def db():
    db=TestSessionLocal()
    pokemon1=PokemonDB(nome_pokemon="Kyogre",tipo_pokemon="Lendario",nivel_pokemon=184)
    pokemon2=PokemonDB(nome_pokemon="Charizard",tipo_pokemon="Fogo",nivel_pokemon=120)
    pokemon3=PokemonDB(nome_pokemon="Blastoise",tipo_pokemon="Agua",nivel_pokemon=120)
    pokemon4=PokemonDB(nome_pokemon="Bulbasaur",tipo_pokemon="Planta",nivel_pokemon=120)
    db.add(pokemon1)
    db.add(pokemon2)
    db.add(pokemon3)
    db.add(pokemon4)
    db.commit()
    try:
        yield db
    finally:
        db.close()



def override_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[sessao_db] = override_db

client = TestClient(app)

def test_rota():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello"}


def test_get(db,mocker_redis):
    response=client.get("/pokemons")
    assert response.status_code == 200

    data=response.json()

    assert len(data["pokemons"])==4
    assert data["pokemons"][0]["nome_pokemon"]=="Kyogre"
    assert data["pokemons"][0]["tipo_pokemon"]=="Lendario"
    assert data["pokemons"][0]["nivel_pokemon"]==184


def test_adicionar(db,mocker_redis):
    response=client.post("/adicionar",json={"nome_pokemon":"Mew","tipo_pokemon":"Psquico","nivel_pokemon":144})
    assert response.status_code==200

def test_atualizar(db,mocker_redis):
    response = client.put("/atualizar/1",json={"nome_pokemon":"Kyogre", "tipo_pokemon":"Lendario", "nivel_pokemon":200 })
    assert response.status_code == 200


def test_evoluir(db,mocker_redis):
    response=client.put("/evoluir/2",json={"nome_pokemon":"MegaCharizard","tipo_pokemon":"Super","nivel_pokemon":200})
    assert response.status_code==200


def test_excluir(db,mocker_redis):
    response=client.delete("/deletar/1")
    assert response.status_code==200



def test_pokemon_nao_econtrado(db,mocker_redis):
    response=client.delete("/deletar/999")
    assert response.status_code==404