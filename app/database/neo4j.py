from neo4j import GraphDatabase
from contextlib import contextmanager
import os
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

if not all([NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD]):
    raise ValueError("Variáveis do Neo4j não configuradas corretamente")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

@contextmanager
def get_session():
    session = driver.session(database=NEO4J_DATABASE)
    tx = session.begin_transaction()
    try:
        yield tx
        tx.commit()
    except Exception:
        tx.rollback()
        raise
    finally:
        session.close()

def verify_connection():
    try:
        driver.verify_connectivity()
        print("Neo4j conectado com sucesso")
    except Exception as e:
        print(f"Erro ao conectar no Neo4j: {e}")
        raise


# Constraints e índices descritos na documentação (seção 15.4).
# `IF NOT EXISTS` torna a criação idempotente — segura para rodar a
# cada startup, sem risco de duplicar ou falhar se já existirem.
_CONSTRAINTS = [
    "CREATE CONSTRAINT IF NOT EXISTS FOR (u:Usuario) REQUIRE u.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (u:Usuario) REQUIRE u.email IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Caso) REQUIRE c.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Suspeito) REQUIRE s.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (e:Evidencia) REQUIRE e.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (ct:Contato) REQUIRE ct.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (a:AnaliseProb) REQUIRE a.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (a:AcaoInvestigativa) REQUIRE a.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (a:AcaoInvestigativa) REQUIRE a.sourceKey IS UNIQUE",
]

_INDEXES = [
    "CREATE INDEX IF NOT EXISTS FOR (c:Caso) ON (c.status)",
    "CREATE INDEX IF NOT EXISTS FOR (s:Suspeito) ON (s.posicaoRanking)",
    "CREATE INDEX IF NOT EXISTS FOR (e:Evidencia) ON (e.tipo)",
    "CREATE INDEX IF NOT EXISTS FOR (e:Evidencia) ON (e.status)",
]


def ensure_constraints():
    try:
        with driver.session(database=NEO4J_DATABASE) as session:
            for statement in _CONSTRAINTS + _INDEXES:
                session.run(statement)
        print("Constraints e índices do Neo4j verificados/criados com sucesso")
    except Exception as e:
        print(f"Erro ao criar constraints/índices do Neo4j: {e}")
        raise