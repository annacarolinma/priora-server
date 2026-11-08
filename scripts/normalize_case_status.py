"""
Padroniza a situação dos casos já gravados: versões antigas do front salvavam
"Pendente" como "Arquivado" e "Finalizado" como "Concluído". O sistema usa
Ativo, Pendente e Finalizado.

Uso (na pasta do priora_server, com o .env configurado):

    python scripts/normalize_case_status.py            # só mostra o que seria feito
    python scripts/normalize_case_status.py --apply    # aplica

É seguro rodar mais de uma vez.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.neo4j import driver, NEO4J_DATABASE  # noqa: E402

MAP = {"Arquivado": "Pendente", "Concluído": "Finalizado"}


def main(apply: bool) -> None:
    with driver.session(database=NEO4J_DATABASE) as session:
        for old, new in MAP.items():
            n = session.run("MATCH (c:Caso {status: $old}) RETURN count(c) AS n", old=old).single()["n"]
            print(f"{n} caso(s) com status '{old}' -> '{new}'")
            if apply and n:
                session.run("MATCH (c:Caso {status: $old}) SET c.status = $new", old=old, new=new)
        print("Atualizado." if apply else "Nada alterado. Use --apply para aplicar.")


if __name__ == "__main__":
    main("--apply" in sys.argv)
