"""
Troca os 5 atributos de perfil antigos (comportamento, agressividade,
proximidade, conexoesSociais, nivelConfissao) pelas 5 dimensões de Canter
(2000) usadas na documentação: coerenciaInterpessoal, significanciaTempoLugar,
caracteristicasCriminais, historicoCriminal e conscienciaForense.

Os valores antigos NÃO são convertidos: as propriedades antigas são removidas
e, nos suspeitos, as novas começam no ponto médio (50). O perfil estimado do
Caso é apagado e deve ser definido de novo na tela.

Uso (na pasta do priora_server, com o .env configurado):

    python scripts/reset_profile_attributes.py            # só mostra o que seria feito
    python scripts/reset_profile_attributes.py --apply    # aplica

É seguro rodar mais de uma vez.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.neo4j import driver, NEO4J_DATABASE  # noqa: E402

NEW = ["coerenciaInterpessoal", "significanciaTempoLugar", "caracteristicasCriminais",
       "historicoCriminal", "conscienciaForense"]
OLD = ["comportamento", "agressividade", "proximidade", "conexoesSociais", "nivelConfissao"]


def cap(name: str) -> str:
    return name[0].upper() + name[1:]


def main(apply: bool) -> None:
    with driver.session(database=NEO4J_DATABASE) as session:
        n_s = session.run(
            "MATCH (s:Suspeito) WHERE s.coerenciaInterpessoal IS NULL OR s.comportamento IS NOT NULL "
            "RETURN count(s) AS n"
        ).single()["n"]
        n_c = session.run(
            "MATCH (c:Caso) WHERE c.perfilEstimadoComportamento IS NOT NULL "
            "RETURN count(c) AS n"
        ).single()["n"]
        print(f"{n_s} suspeito(s) e {n_c} perfil(is) estimado(s) a atualizar.")
        if not apply:
            print("Nada alterado. Use --apply para aplicar.")
            return

        sets = ", ".join(f"s.{k} = 50.0" for k in NEW)
        removes = ", ".join(f"s.{k}" for k in OLD)
        session.run(f"MATCH (s:Suspeito) WHERE s.coerenciaInterpessoal IS NULL OR s.comportamento IS NOT NULL SET {sets} REMOVE {removes}")

        # Perfil estimado: é apagado; o investigador define de novo na tela.
        cremoves = ", ".join(f"c.perfilEstimado{cap(k)}" for k in OLD)
        session.run(f"MATCH (c:Caso) WHERE c.perfilEstimadoComportamento IS NOT NULL REMOVE {cremoves}")
        print("Atualizado.")


if __name__ == "__main__":
    main("--apply" in sys.argv)
