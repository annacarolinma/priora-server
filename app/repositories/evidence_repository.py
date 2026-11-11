import json

from app.repositories.history_repository import create_history


# ============================================================
# HISTÓRICO
# ============================================================

def get_case_history(
    tx,
    caso_id: str
):

    query = """
    MATCH (h:HistoricoCaso)-[:REFERENTE_A]->(c:Caso {id:$casoId})
    OPTIONAL MATCH (u:Usuario)-[:REALIZOU]->(h)

    RETURN {
        id: h.id,
        casoId: c.id,
        tipo: h.tipo,
        entidade: h.entidade,
        valorNovo: h.valorNovo,
        criadoEm: toString(h.criadoEm),

        usuario: CASE
            WHEN u IS NULL THEN NULL
            ELSE {
                id: u.id,
                primeiroNome: u.primeiroNome,
                sobrenome: u.sobrenome,
                fotoUrl: u.fotoUrl
            }
        END
    } AS historico

    ORDER BY h.criadoEm DESC
    """

    result = tx.run(
        query,
        casoId=caso_id
    )

    historicos = []

    for record in result:

        historico = dict(record["historico"])

        if historico.get("valorNovo"):

            try:
                historico["valorNovo"] = json.loads(
                    historico["valorNovo"]
                )

            except (json.JSONDecodeError, TypeError):
                pass

        historicos.append(historico)

    return historicos



# ============================================================
# EVIDÊNCIA -> CASO
# ============================================================

def get_case_id_for_evidence(
    tx,
    evidence_id: str
):

    query = """
    MATCH (c:Caso)-[:TEM_EVIDENCIA]->(e:Evidencia {id:$evidenceId})
    RETURN c.id AS casoId
    """

    record = tx.run(
        query,
        evidenceId=evidence_id
    ).single()

    return record["casoId"] if record else None



def get_case_ids_for_evidences(
    tx,
    evidence_ids:list[str]
):

    query = """
    UNWIND $ids AS eid

    MATCH (c:Caso)-[:TEM_EVIDENCIA]->(e:Evidencia {id:eid})

    RETURN DISTINCT c.id AS casoId
    """

    result = tx.run(
        query,
        ids=evidence_ids
    )

    return [
        record["casoId"]
        for record in result
    ]



# ============================================================
# CRIAR EVIDÊNCIA
# ============================================================

def create_evidence(
    tx,
    data:dict,
    current_user_id:str
):

    query = """

    MATCH (c:Caso {id:$casoId})
    MATCH (u:Usuario {id:$userId})

    CREATE (e:Evidencia {

        id: randomUUID(),

        nome:$nome,
        tipo:$tipo,
        descricao:$descricao,
        fonte:$fonte,
        status:$status,

        dataColeta:date($dataColeta),

        pesoCondicional:$peso,

        criadoEm:datetime(),
        atualizadoEm:datetime()
    })


    CREATE (c)-[:TEM_EVIDENCIA {
        adicionadaEm:datetime()
    }]->(e)


    WITH c,e,u


    UNWIND $vinculos AS v


    MATCH (s:Suspeito {id:v.suspeitoId})


    CREATE (e)-[:VINCULA {

        pesoVinculo:v.pesoVinculo,
        efeito:coalesce(v.efeito, 'Incrimina'),
        vinculadoEm:datetime()

    }]->(s)


    RETURN e {

        .id,
        .nome,
        .tipo,
        .status,
        .descricao,

        .fonte,
        .pesoCondicional,
        dataColeta:toString(e.dataColeta)

    } AS evidencia

    """


    result = tx.run(
        query,

        casoId=data["casoId"],

        userId=current_user_id,

        vinculos=data.get(
            "vinculos",
            []
        ),

        nome=data["nome"],

        tipo=data["tipo"],

        descricao=data.get(
            "descricao"
        ),

        fonte=data.get("fonte"),

        status=data["status"],

        dataColeta=data["dataColeta"],

        peso=data["peso"]
    )


    record = result.single()


    if not record:
        raise Exception(
            "Erro ao criar evidência"
        )


    evidencia = record["evidencia"]


    # ========================================================
    # HISTÓRICO IGUAL AO CASO
    # ========================================================

    create_history(

        tx=tx,

        user_id=current_user_id,

        caso_id=data["casoId"],

        action="CREATE",

        entity_type="EVIDENCIA",

        entity_id=evidencia["id"],

        entity_name=evidencia["nome"],

        details="Evidência criada"

    )


    return evidencia

# ============================================================
# SUSPEITOS COM PESO
# ============================================================

_SUSPEITOS_COM_PESO = """

WITH e,

collect(

    CASE

        WHEN s IS NOT NULL THEN {

            id:s.id,

            nome:s.nome,

            pesoVinculo: v.pesoVinculo,
            efeito: coalesce(v.efeito, 'Incrimina')

        }

        ELSE NULL

    END

) AS suspeitosRaw


WITH e,

[x IN suspeitosRaw WHERE x IS NOT NULL] AS suspeitos

"""


# ============================================================
# LISTAR EVIDÊNCIAS
# ============================================================

def list_evidences_by_case(
    tx,
    caso_id: str
):

    query = """
    MATCH (c:Caso {id: $casoId})
          -[:TEM_EVIDENCIA]->
          (e:Evidencia)

    OPTIONAL MATCH (e)-[v:VINCULA]->(s:Suspeito)

    WITH e, collect(
        CASE
            WHEN s IS NOT NULL
            THEN {
                id: s.id,
                nome: s.nome,
                pesoVinculo: v.pesoVinculo,
            efeito: coalesce(v.efeito, 'Incrimina')
            }
            ELSE NULL
        END
    ) AS suspeitosRaw

    WITH e,
         [x IN suspeitosRaw WHERE x IS NOT NULL] AS suspeitos

    ORDER BY e.criadoEm DESC

    RETURN e {
        .id,
        .nome,
        .tipo,
        .status,
        .descricao,
        .fonte,
        .dataColeta,
        .pesoCondicional
    } AS evidencia,
    suspeitos
    """

    result = tx.run(
        query,
        casoId=caso_id
    )

    return [
        {
            **record["evidencia"],
            "dataColeta": (
                str(record["evidencia"]["dataColeta"])
                if record["evidencia"]["dataColeta"]
                else None
            ),
            "suspeitos": record["suspeitos"]
        }
        for record in result
    ]



# ============================================================
# BUSCAR EVIDÊNCIA POR ID
# ============================================================

def get_evidence_by_id(
    tx,
    evidence_id: str
):

    query = """
    MATCH (e:Evidencia {id: $evidenceId})

    OPTIONAL MATCH (e)-[v:VINCULA]->(s:Suspeito)

    WITH e, collect(
        CASE
            WHEN s IS NOT NULL
            THEN {
                id: s.id,
                nome: s.nome,
                pesoVinculo: v.pesoVinculo,
            efeito: coalesce(v.efeito, 'Incrimina')
            }
            ELSE NULL
        END
    ) AS suspeitosRaw

    WITH e,
         [x IN suspeitosRaw WHERE x IS NOT NULL] AS suspeitos

    RETURN e {
        .id,
        .nome,
        .tipo,
        .status,
        .descricao,

        .fonte,
        .pesoCondicional,
        .dataColeta
    } AS evidencia,
    suspeitos
    """

    result = tx.run(
        query,
        evidenceId=evidence_id
    )

    record = result.single()

    if not record:
        raise Exception("Evidência não encontrada")

    ev = dict(record["evidencia"])

    if ev.get("dataColeta"):
        ev["dataColeta"] = str(ev["dataColeta"])

    ev["suspeitos"] = record["suspeitos"]

    return ev



# ============================================================
# DELETAR EVIDÊNCIAS
# ============================================================

def delete_evidences(
    tx,
    evidence_ids:list[str],
    current_user_id:str
):


    for evidence_id in evidence_ids:


        caso_id = get_case_id_for_evidence(

            tx,

            evidence_id

        )


        if not caso_id:

            continue



        # Busca nome antes de apagar

        find_query = """

        MATCH (e:Evidencia {id:$id})

        RETURN e.nome AS nome

        """

        record = tx.run(

            find_query,

            id=evidence_id

        ).single()



        nome = (

            record["nome"]

            if record

            else "Evidência"

        )



        # Histórico igual ao Caso

        create_history(

            tx=tx,

            user_id=current_user_id,

            caso_id=caso_id,

            action="DELETE",

            entity_type="EVIDENCIA",

            entity_id=evidence_id,

            entity_name=nome,

            details="Evidência excluída"

        )



        delete_query = """

        MATCH (e:Evidencia {id:$id})

        DETACH DELETE e

        """



        tx.run(

            delete_query,

            id=evidence_id

        )



    return {

        "message":

        "Evidências excluídas com sucesso"

    }

# ============================================================
# ATUALIZAR EVIDÊNCIA
# ============================================================

def update_evidence(
    tx,
    evidence_id:str,
    data:dict,
    current_user_id:str
):


    # ========================================================
    # BUSCAR ESTADO ANTIGO
    # Igual ao update_case()
    # ========================================================

    old_query = """

    MATCH (e:Evidencia {id:$evidenceId})

    RETURN e {

        .id,
        .nome,
        .tipo,
        .status,
        .descricao,

        .fonte,
        .pesoCondicional,

        dataColeta:toString(e.dataColeta)

    } AS evidencia

    """


    old_record = tx.run(

        old_query,

        evidenceId=evidence_id

    ).single()



    if not old_record:

        raise Exception(
            "Evidência não encontrada"
        )



    old_evidence = old_record["evidencia"]



    # ========================================================
    # MONTA UPDATE
    # ========================================================

    field_map = {

        "nome":"e.nome",

        "tipo":"e.tipo",

        "status":"e.status",

        "descricao":"e.descricao",

        "fonte":"e.fonte",

        "dataColeta":"e.dataColeta",

        "peso":"e.pesoCondicional"

    }



    set_clauses = []

    params = {

        "evidenceId":evidence_id,

        "userId":current_user_id

    }



    for field,value in data.items():


        if field not in field_map:

            continue


        if value is None:

            continue



        neo_field = field_map[field]



        if field == "dataColeta":


            set_clauses.append(

                f"{neo_field}=date(${field})"

            )


        else:


            set_clauses.append(

                f"{neo_field}=${field}"

            )



        params[field]=value



    set_clauses.append(

        "e.atualizadoEm=datetime()"

    )



    set_query = ", ".join(
        set_clauses
    )



    query = f"""

    MATCH (e:Evidencia {{

        id:$evidenceId

    }})


    OPTIONAL MATCH (c:Caso)-[:TEM_EVIDENCIA]->(e)


    MATCH (u:Usuario {{

        id:$userId

    }})



    SET {set_query}



    WITH e,c,u

    """



    # ========================================================
    # ATUALIZAR VÍNCULOS
    # ========================================================


    if "vinculos" in data:


        query += """

        OPTIONAL MATCH (e)-[r:VINCULA]->()

        DELETE r


        WITH e,c,u


        UNWIND $vinculos AS v


        MATCH (s:Suspeito {

            id:v.suspeitoId

        })


        CREATE (e)-[:VINCULA {

            pesoVinculo:v.pesoVinculo,
        efeito:coalesce(v.efeito, 'Incrimina'),

            vinculadoEm:datetime()

        }]->(s)


        WITH DISTINCT e,c,u

        """



        params["vinculos"] = data["vinculos"]




    # ========================================================
    # RETORNA EVIDÊNCIA ATUAL
    # ========================================================


    query += """

    RETURN e {

        .id,

        .nome,

        .tipo,

        .status,

        .descricao,


        .fonte,

        .pesoCondicional,

        dataColeta:toString(e.dataColeta)

    } AS evidencia

    """



    record = tx.run(

        query,

        **params

    ).single()



    if not record:

        raise Exception(
            "Erro ao atualizar evidência"
        )



    evidencia = record["evidencia"]




    # ========================================================
    # COMPARA ALTERAÇÕES
    # Igual ao Caso
    # ========================================================


    changed_fields = []


    fields_to_compare = [

        "nome",

        "tipo",

        "status",

        "descricao",

        "fonte",

        "pesoCondicional",

        "dataColeta"

    ]



    for field in fields_to_compare:


        old_value = old_evidence.get(
            field
        )


        new_value = evidencia.get(
            field
        )



        if old_value != new_value:


            changed_fields.append({

                "campo":field,

                "antes":old_value,

                "depois":new_value

            })




    # ========================================================
    # HISTÓRICO IGUAL AO CASO
    # ========================================================


    if changed_fields:


        caso_id = get_case_id_for_evidence(

            tx,

            evidence_id

        )



        create_history(

            tx=tx,

            user_id=current_user_id,

            caso_id=caso_id,

            action="UPDATE",

            entity_type="EVIDENCIA",

            entity_id=evidence_id,

            entity_name=evidencia["nome"],

            valor_novo=changed_fields

        )



    return evidencia