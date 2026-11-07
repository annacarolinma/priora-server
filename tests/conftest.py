import os
import sys

# Variáveis mínimas para importar os módulos do app sem um banco real.
for k, v in {
    "NEO4J_URI": "bolt://localhost:7687",
    "NEO4J_USERNAME": "neo4j",
    "NEO4J_PASSWORD": "teste",
    "SECRET_KEY": "chave-de-teste-com-mais-de-32-caracteres-xxxx",
    "ALGORITHM": "HS256",
    "MAIL_USERNAME": "a@b.c",
    "MAIL_PASSWORD": "x",
    "MAIL_FROM": "a@b.c",
    "MAIL_PORT": "587",
    "MAIL_SERVER": "localhost",
}.items():
    os.environ.setdefault(k, v)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
