"""
Migra as fotos de perfil que estão como base64 dentro do Neo4j
(Usuario.fotoUrl = "data:image/...;base64,...") para o armazenamento de
imagens (Supabase ou disco local), trocando o valor pela URL pública.

Uso (na pasta do priora_server, com o .env configurado):

    python scripts/migrate_user_photos.py            # só mostra o que seria feito
    python scripts/migrate_user_photos.py --apply    # migra de fato

É seguro rodar mais de uma vez: usuários que já têm URL são ignorados.
"""
import asyncio
import base64
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.neo4j import driver, NEO4J_DATABASE  # noqa: E402
from app.database.supabase_storage import upload_user_photo, validate_image  # noqa: E402


def decode_data_url(value: str) -> bytes:
    _, _, payload = value.partition(",")
    return base64.b64decode(payload)


async def main(apply: bool) -> None:
    with driver.session(database=NEO4J_DATABASE) as session:
        rows = session.run(
            "MATCH (u:Usuario) WHERE u.fotoUrl STARTS WITH 'data:' "
            "RETURN u.id AS id, u.email AS email, size(u.fotoUrl) AS tamanho, u.fotoUrl AS foto"
        ).data()

        print(f"{len(rows)} usuário(s) com foto em base64.")
        migrados = 0

        for r in rows:
            try:
                dados = decode_data_url(r["foto"])
                validate_image(dados, None)
            except Exception as e:
                print(f"  - {r['email']}: foto inválida, ignorada ({e})")
                continue

            print(f"  - {r['email']}: {r['tamanho'] / 1024:.0f} KB em base64")
            if not apply:
                continue

            url = await upload_user_photo(r["id"], dados, None)
            session.run("MATCH (u:Usuario {id: $id}) SET u.fotoUrl = $url", id=r["id"], url=url)
            migrados += 1
            print(f"    migrada -> {url}")

        if apply:
            print(f"{migrados} foto(s) migrada(s).")
        elif rows:
            print("Nada foi alterado. Rode com --apply para migrar.")

    driver.close()


if __name__ == "__main__":
    asyncio.run(main("--apply" in sys.argv))
