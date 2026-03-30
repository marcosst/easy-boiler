"""Seed example data for user marcos@medire.com.br (username: marcosst)."""

import json
import os
import sqlite3
from pathlib import Path

from passlib.hash import bcrypt

DB_PATH = os.getenv("DATABASE_URL", "sqlite:data/data.db").replace("sqlite:", "")


def main():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")

    email = "marcos@medire.com.br"
    username = "marcosst"

    # Get or create user
    row = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if row:
        user_id = row["id"]
        print(f"User '{email}' already exists (id={user_id})")
    else:
        cursor = db.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, bcrypt.hash("senha123")),
        )
        user_id = cursor.lastrowid
        print(f"Created user '{email}' (id={user_id})")

    # Delete existing data for this user (clean seed)
    db.execute("DELETE FROM subjects WHERE owner_id = ?", (user_id,))

    subjects_data = [
        {
            "name": "Cadastro de Componentes",
            "shortname": "cadastro-componentes",
            "is_public": 1,
            "library_items": [
                {"name": "Tutorial Cadastro Completo", "type": "youtube", "url": "https://youtube.com/watch?v=abc001"},
                {"name": "Cadastro de Agregados", "type": "youtube", "url": "https://youtube.com/watch?v=abc002"},
                {"name": "Tipos de Componentes", "type": "youtube", "url": "https://youtube.com/watch?v=abc003"},
                {"name": "Manual de Componentes", "type": "pdf", "file_path": "/midias/marcosst/manual-componentes.pdf"},
                {"name": "Guia de Classificacao", "type": "pdf", "file_path": "/midias/marcosst/guia-classificacao.pdf"},
            ],
        },
        {
            "name": "Montagem de Modulos",
            "shortname": "montagem-modulos",
            "is_public": 1,
            "library_items": [
                {"name": "Montagem Basica", "type": "youtube", "url": "https://youtube.com/watch?v=mont001"},
                {"name": "Montagem Avancada", "type": "youtube", "url": "https://youtube.com/watch?v=mont002"},
                {"name": "Encaixes e Conexoes", "type": "youtube", "url": "https://youtube.com/watch?v=mont003"},
                {"name": "Manual de Montagem", "type": "pdf", "file_path": "/midias/marcosst/manual-montagem.pdf"},
                {"name": "Tabela de Medidas", "type": "pdf", "file_path": "/midias/marcosst/tabela-medidas.pdf"},
                {"name": "Checklist de Montagem", "type": "pdf", "file_path": "/midias/marcosst/checklist-montagem.pdf"},
            ],
        },
        {
            "name": "Configuracao de Ferragens",
            "shortname": "configuracao-ferragens",
            "is_public": 0,
            "library_items": [
                {"name": "Ferragens Basicas", "type": "youtube", "url": "https://youtube.com/watch?v=ferr001"},
                {"name": "Dobradicas e Corrediceas", "type": "youtube", "url": "https://youtube.com/watch?v=ferr002"},
                {"name": "Catalogo de Ferragens", "type": "pdf", "file_path": "/midias/marcosst/catalogo-ferragens.pdf"},
                {"name": "Manual Tecnico Blum", "type": "pdf", "file_path": "/midias/marcosst/manual-blum.pdf"},
                {"name": "Ajustes e Regulagens", "type": "youtube", "url": "https://youtube.com/watch?v=ferr003"},
            ],
        },
        {
            "name": "Renderizacao 3D",
            "shortname": "renderizacao-3d",
            "is_public": 1,
            "library_items": [
                {"name": "Introducao ao Render", "type": "youtube", "url": "https://youtube.com/watch?v=rend001"},
                {"name": "Iluminacao e Materiais", "type": "youtube", "url": "https://youtube.com/watch?v=rend002"},
                {"name": "Exportacao de Imagens", "type": "youtube", "url": "https://youtube.com/watch?v=rend003"},
                {"name": "Guia de Renderizacao", "type": "pdf", "file_path": "/midias/marcosst/guia-renderizacao.pdf"},
                {"name": "Biblioteca de Materiais", "type": "pdf", "file_path": "/midias/marcosst/biblioteca-materiais.pdf"},
            ],
        },
        {
            "name": "Orcamento e Propostas",
            "shortname": "orcamento-propostas",
            "is_public": 0,
            "library_items": [
                {"name": "Gerando Orcamentos", "type": "youtube", "url": "https://youtube.com/watch?v=orc001"},
                {"name": "Personalizando Propostas", "type": "youtube", "url": "https://youtube.com/watch?v=orc002"},
                {"name": "Modelo de Proposta", "type": "pdf", "file_path": "/midias/marcosst/modelo-proposta.pdf"},
                {"name": "Tabela de Precos", "type": "pdf", "file_path": "/midias/marcosst/tabela-precos.pdf"},
                {"name": "Exportacao para PDF", "type": "youtube", "url": "https://youtube.com/watch?v=orc003"},
            ],
        },
        {
            "name": "Instalacao em Obra",
            "shortname": "instalacao-obra",
            "is_public": 1,
            "library_items": [
                {"name": "Preparacao do Ambiente", "type": "youtube", "url": "https://youtube.com/watch?v=inst001"},
                {"name": "Instalacao Passo a Passo", "type": "youtube", "url": "https://youtube.com/watch?v=inst002"},
                {"name": "Nivelamento e Prumo", "type": "youtube", "url": "https://youtube.com/watch?v=inst003"},
                {"name": "Manual de Instalacao", "type": "pdf", "file_path": "/midias/marcosst/manual-instalacao.pdf"},
                {"name": "Checklist de Obra", "type": "pdf", "file_path": "/midias/marcosst/checklist-obra.pdf"},
                {"name": "Ficha de Vistoria", "type": "pdf", "file_path": "/midias/marcosst/ficha-vistoria.pdf"},
            ],
        },
    ]

    for subj in subjects_data:
        cursor = db.execute(
            "INSERT INTO subjects (name, shortname, is_public, owner_id) VALUES (?, ?, ?, ?)",
            (subj["name"], subj["shortname"], subj["is_public"], user_id),
        )
        subject_id = cursor.lastrowid

        # Insert library items and collect their IDs
        lib_ids = []
        for pos, lib in enumerate(subj["library_items"]):
            c = db.execute(
                "INSERT INTO library_items (subject_id, name, type, url, file_path, position) VALUES (?, ?, ?, ?, ?, ?)",
                (subject_id, lib["name"], lib["type"], lib.get("url"), lib.get("file_path"), pos),
            )
            lib_ids.append({"id": c.lastrowid, **lib})

        # Build content_json referencing the library items
        videos = [li for li in lib_ids if li["type"] == "youtube"]
        pdfs = [li for li in lib_ids if li["type"] == "pdf"]

        content = {"topicos": []}

        # Topic 1: uses first 2 videos + first pdf
        t1_passos_1 = []
        if len(videos) > 0:
            t1_passos_1.append({
                "library_id": videos[0]["id"], "acao": f"Assistir: {videos[0]['name']}",
                "timestamp": "00:00:30", "pagina": None, "trecho_referencia": "",
                "file_path": None, "url": videos[0]["url"],
            })
        if len(pdfs) > 0:
            t1_passos_1.append({
                "library_id": pdfs[0]["id"], "acao": f"Consultar: {pdfs[0]['name']}",
                "timestamp": None, "pagina": 1, "trecho_referencia": "Veja a introducao do documento",
                "file_path": pdfs[0]["file_path"], "url": None,
            })

        t1_passos_2 = []
        if len(videos) > 1:
            t1_passos_2.append({
                "library_id": videos[1]["id"], "acao": f"Assistir: {videos[1]['name']}",
                "timestamp": "00:01:15", "pagina": None, "trecho_referencia": "",
                "file_path": None, "url": videos[1]["url"],
            })
        if len(pdfs) > 0:
            t1_passos_2.append({
                "library_id": pdfs[0]["id"], "acao": f"Verificar detalhes na pagina 3",
                "timestamp": None, "pagina": 3, "trecho_referencia": "Secao de detalhamento tecnico",
                "file_path": pdfs[0]["file_path"], "url": None,
            })

        content["topicos"].append({
            "titulo": f"Introducao a {subj['name']}",
            "subtopicos": [
                {"titulo": "Conceitos iniciais", "passos": t1_passos_1},
                {"titulo": "Aprofundamento", "passos": t1_passos_2},
            ],
        })

        # Topic 2: uses remaining videos + remaining pdfs
        t2_passos_1 = []
        if len(videos) > 2:
            t2_passos_1.append({
                "library_id": videos[2]["id"], "acao": f"Assistir: {videos[2]['name']}",
                "timestamp": "00:00:42", "pagina": None, "trecho_referencia": "",
                "file_path": None, "url": videos[2]["url"],
            })
        if len(pdfs) > 1:
            t2_passos_1.append({
                "library_id": pdfs[1]["id"], "acao": f"Consultar: {pdfs[1]['name']}",
                "timestamp": None, "pagina": 2, "trecho_referencia": "Tabela de referencia",
                "file_path": pdfs[1]["file_path"], "url": None,
            })

        t2_passos_2 = []
        if len(videos) > 0:
            t2_passos_2.append({
                "library_id": videos[0]["id"], "acao": f"Revisar: {videos[0]['name']} - trecho final",
                "timestamp": "00:03:20", "pagina": None, "trecho_referencia": "",
                "file_path": None, "url": videos[0]["url"],
            })
        if len(pdfs) > 1:
            t2_passos_2.append({
                "library_id": pdfs[1]["id"], "acao": f"Confirmar procedimento na pagina 5",
                "timestamp": None, "pagina": 5, "trecho_referencia": "Procedimento de verificacao final",
                "file_path": pdfs[1]["file_path"], "url": None,
            })

        content["topicos"].append({
            "titulo": f"Pratica de {subj['name']}",
            "subtopicos": [
                {"titulo": "Execucao guiada", "passos": t2_passos_1},
                {"titulo": "Revisao e validacao", "passos": t2_passos_2},
            ],
        })

        db.execute(
            "UPDATE subjects SET content_json = ? WHERE id = ?",
            (json.dumps(content, ensure_ascii=False), subject_id),
        )
        print(f"  Created subject '{subj['name']}' with {len(lib_ids)} library items")

    db.commit()
    db.close()
    print("Seed complete!")


if __name__ == "__main__":
    main()
