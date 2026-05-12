from fastapi import FastAPI,HTTPException,Depends
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv
import os
import redis
import json

load_dotenv()


from sqlalchemy import create_engine,Column,Integer,String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session,sessionmaker

DATABASE_URL=os.getenv("DATABASE_URL")
engine=create_engine(DATABASE_URL,connect_args={"check_same_thread":False})
SessionLocal=sessionmaker(autocommit=False,autoflush=False,bind=engine)
Base=declarative_base()


REDIS_HOST=os.getenv("REDIS_HOST","localhost")
REDIS_PORT=int(os.getenv("REDIS_PORT","6379"))

redis_client=redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=0,
    decode_responses=True
)


app=FastAPI()


class PokemonDB(Base):
    __tablename__="Pokemons"
    id_pokemon=Column(Integer,primary_key=True,index=True)
    nome_pokemon=Column(String,index=True)
    tipo_pokemon=Column(String,index=True)
    nivel_pokemon=Column(Integer,index=True)


class Pokemon(BaseModel):
    nome_pokemon:str
    tipo_pokemon:str
    nivel_pokemon:int


Base.metadata.create_all(bind=engine)


def salvar_redis(id_pokemon:int,pokemon:Pokemon):
    redis_client.set(f"pokemon:{id_pokemon}",json.dumps(pokemon.model_dump()))


def deletar_redis(id_pokemon):
    redis_client.delete(f"pokemon:{id_pokemon}")

def limpar_cache():
    for key in redis_client.keys("pokemon:page=*"):
        redis_client.delete(key)


def sessao_db():
    db=SessionLocal()
    try:
        yield db
    finally:
        db.close()
    
@app.get("/")
def home():
    return{"message":"Hello"}

@app.get("/debug/redis")
def listar_pokemons_redis():
    poke=redis_client.keys("*")
    pokemons=[]
    for pokes in poke:
        valor= redis_client.get(pokes)
        ttl=redis_client.ttl(pokes)
        pokemons.append({"id":pokes,"valor":json.loads(valor),"ttl":ttl})
    
    return pokemons


@app.get("/pokemons")
def listar_pokemons(page:int=1,limit:int=10,db:Session=Depends(sessao_db)):
    if page<1 or limit <1:
        raise HTTPException(status_code=401,detail="Erro de paginacao")
    
    cache_key=f"pokemon:page={page}&limit={limit}"
    cached=redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    

    pokemons=db.query(PokemonDB).offset((page-1)*limit).limit(limit).all()
    if not pokemons:
        raise HTTPException(status_code=404,detail="Nao ha pokemons listados")
    

    resposta={"page":page,"limit":limit,"total_pokemons":len(pokemons),"pokemons":[{"id_pokemon":pokemon.id_pokemon,"nome_pokemon":pokemon.nome_pokemon,"tipo_pokemon":pokemon.tipo_pokemon,"nivel_pokemon":pokemon.nivel_pokemon}for pokemon in pokemons]}
    redis_client.setex(cache_key,30,json.dumps(resposta))
    return resposta


@app.post("/adicionar")
def adicionar_pokemon(pokemon:Pokemon,db:Session=Depends(sessao_db)):
    poke_db=db.query(PokemonDB).filter(PokemonDB.nome_pokemon==pokemon.nome_pokemon,PokemonDB.tipo_pokemon==pokemon.tipo_pokemon,PokemonDB.nivel_pokemon==pokemon.nivel_pokemon).first()
    if poke_db:
        raise HTTPException(status_code=409,detail="Pokemon ja cadastrado treinador")
    
    novo_pokemon=PokemonDB(nome_pokemon=pokemon.nome_pokemon,tipo_pokemon=pokemon.tipo_pokemon,nivel_pokemon=pokemon.nivel_pokemon)
    db.add(novo_pokemon)
    db.commit()
    db.refresh(novo_pokemon)
    salvar_redis(novo_pokemon.id_pokemon,pokemon)
    limpar_cache()
    return{"message":f"O {novo_pokemon.nome_pokemon} foi criado com sucesso"}


@app.put("/atualizar/{id_pokemon}")
def atualizar_pokemon(id_pokemon:int,pokemon:Pokemon,db:Session=Depends(sessao_db)):
    poke_db=db.query(PokemonDB).filter(PokemonDB.id_pokemon==id_pokemon).first()
    if not poke_db:
        raise HTTPException(status_code=404,detail="Pokemon nao encontrado")
    
    nivel_antigo=poke_db.nivel_pokemon

    poke_db.nivel_pokemon=pokemon.nivel_pokemon

    db.commit()
    db.refresh(poke_db)

    salvar_redis(poke_db.id_pokemon,pokemon)
    limpar_cache()

    return{"message":"O nivel do pokemon foi atualizado","pokemon":poke_db.nome_pokemon,"nivel_antigo":nivel_antigo,"nivel_novo":poke_db.nivel_pokemon}


@app.put("/evoluir/{id_pokemon}")
def evoluir_pokemon(id_pokemon:int,pokemon:Pokemon,db:Session=Depends(sessao_db)):
    poke_db=db.query(PokemonDB).filter(PokemonDB.id_pokemon==id_pokemon).first()
    if not poke_db:
        raise HTTPException(status_code=404,detail="Pokemon nao encontrado")
    
    poke_db.nome_pokemon=pokemon.nome_pokemon
    poke_db.tipo_pokemon=pokemon.tipo_pokemon
    poke_db.nivel_pokemon=pokemon.nivel_pokemon
    db.commit()
    db.refresh(poke_db)
    salvar_redis(poke_db.id_pokemon,pokemon)
    return{"message":f"O pokemon evoluio para {poke_db.nome_pokemon}"}


@app.delete("/deletar/{id_pokemon}")
def deletar_pokemon(id_pokemon:int,db:Session=Depends(sessao_db)):
    poke_db=db.query(PokemonDB).filter(PokemonDB.id_pokemon==id_pokemon).first()
    if not poke_db:
        raise HTTPException(status_code=404,detail="Erro pokemon nao encontrado")
    
    db.delete(poke_db)
    db.commit()
    deletar_redis(id_pokemon)
    limpar_cache()
    return{"message":f"O pokemon {poke_db.nome_pokemon} foi excluido"}




    


        
    


