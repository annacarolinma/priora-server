"""Armazenamento de imagens: validação do conteúdo real e gravação local."""
import asyncio
import os

import pytest

from app.database import supabase_storage as st

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 32
GIF = b"GIF89a" + b"\x00" * 32
WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 32


@pytest.mark.parametrize("dados,tipo,ext", [
    (PNG, "image/png", "png"),
    (JPG, "image/jpeg", "jpg"),
    (GIF, "image/gif", "gif"),
    (WEBP, "image/webp", "webp"),
])
def test_reconhece_o_tipo_pelo_conteudo(dados, tipo, ext):
    assert st.validate_image(dados, "application/octet-stream") == (tipo, ext)


def test_ignora_o_content_type_declarado():
    # um PNG declarado como "text/html" é aceito como PNG; o inverso, não
    assert st.validate_image(PNG, "text/html")[0] == "image/png"


@pytest.mark.parametrize("dados", [
    b"<html><script>alert(1)</script></html>",
    b"MZ\x90\x00 executavel",
    b"%PDF-1.4",
    b"nao e imagem",
])
def test_rejeita_arquivo_que_nao_e_imagem_mesmo_com_content_type_de_imagem(dados):
    with pytest.raises(ValueError):
        st.validate_image(dados, "image/png")


def test_rejeita_vazio_e_grande_demais():
    with pytest.raises(ValueError):
        st.validate_image(b"", "image/png")
    with pytest.raises(ValueError):
        st.validate_image(PNG + b"\x00" * st.MAX_FILE_SIZE_BYTES, "image/png")


@pytest.fixture
def modo_local(tmp_path, monkeypatch):
    monkeypatch.setattr(st, "USE_SUPABASE", False)
    monkeypatch.setattr(st, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(st, "PUBLIC_API_URL", "http://api.local:8000")
    return tmp_path


def test_foto_de_suspeito_em_disco(modo_local):
    url = asyncio.run(st.upload_suspect_photo("caso-1", PNG, "image/png"))
    assert url.startswith("http://api.local:8000/uploads/suspects/caso-1/") and url.endswith(".png")
    nome = url.rsplit("/", 1)[1]
    assert (modo_local / "suspects" / "caso-1" / nome).read_bytes() == PNG


def test_foto_de_perfil_em_disco(modo_local):
    url = asyncio.run(st.upload_user_photo("user-9", JPG, "image/jpeg"))
    assert "/uploads/users/user-9/" in url and url.endswith(".jpg")


def test_imagem_do_quadro_mantem_o_caminho_antigo(modo_local):
    url = asyncio.run(st.upload_board_image("caso-1", GIF, "image/gif"))
    assert url.startswith("http://api.local:8000/uploads/caso-1/")
    assert os.path.isdir(modo_local / "caso-1")


def test_arquivo_invalido_nao_grava_nada(modo_local):
    with pytest.raises(ValueError):
        asyncio.run(st.upload_user_photo("user-9", b"nao e imagem", "image/png"))
    assert list(modo_local.iterdir()) == []
