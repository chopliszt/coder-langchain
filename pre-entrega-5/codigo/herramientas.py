import difflib

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from datos_simulados import EMPRESAS_POR_NOMBRE, POSTULACIONES_POR_EMPRESA


class EntradaBuscarEmpresa(BaseModel):
    nombre_de_la_empresa: str = Field(min_length=2, description="Nombre de la empresa tal como lo menciona el usuario.")


class EntradaBuscarPostulaciones(BaseModel):
    empresa_id: int = Field(gt=0, description="ID numérico interno de la empresa (se obtiene con buscar_empresa_por_nombre).")


@tool(args_schema=EntradaBuscarEmpresa)
def buscar_empresa_por_nombre(nombre_de_la_empresa: str) -> str:
    """Busca el ID interno (empresa_id) de una empresa a la que el usuario se postuló, a partir de su nombre.
    Usá esta herramienta SIEMPRE que el usuario mencione una empresa por su nombre y necesites su empresa_id
    para consultar las postulaciones. Si el nombre no coincide exactamente, devuelve un ERROR con sugerencias
    de nombres parecidos: en ese caso volvé a llamar a esta herramienta con el nombre sugerido."""
    nombre_normalizado: str = nombre_de_la_empresa.strip().lower()
    if nombre_normalizado in EMPRESAS_POR_NOMBRE:
        return f"Empresa encontrada: '{nombre_normalizado}' -> empresa_id={EMPRESAS_POR_NOMBRE[nombre_normalizado]}"

    nombres_parecidos: list[str] = [
        nombre for nombre in EMPRESAS_POR_NOMBRE if nombre.startswith(nombre_normalizado) or nombre_normalizado in nombre
    ] or difflib.get_close_matches(nombre_normalizado, list(EMPRESAS_POR_NOMBRE), n=3, cutoff=0.5)
    if nombres_parecidos:
        return f"ERROR: no hay una empresa llamada exactamente '{nombre_de_la_empresa}'. Nombres parecidos registrados: {nombres_parecidos}."
    return f"ERROR: no hay ninguna empresa registrada con un nombre parecido a '{nombre_de_la_empresa}'. Pedile al usuario que confirme el nombre."


@tool(args_schema=EntradaBuscarPostulaciones)
def buscar_postulaciones_de_la_empresa(empresa_id: int) -> str:
    """Devuelve todas las postulaciones del usuario en una empresa: puesto, fecha, estado, próximo paso y contacto.
    Necesita el empresa_id NUMÉRICO, no el nombre: si solo tenés el nombre, primero usá buscar_empresa_por_nombre.
    Devuelve un ERROR si el empresa_id no existe."""
    if empresa_id not in POSTULACIONES_POR_EMPRESA:
        return f"ERROR: no existe ninguna empresa con empresa_id={empresa_id}. Usá buscar_empresa_por_nombre para obtener un ID válido."
    postulaciones: list[dict[str, str]] = POSTULACIONES_POR_EMPRESA[empresa_id]
    if not postulaciones:
        return f"La empresa con empresa_id={empresa_id} está registrada pero no tiene postulaciones cargadas."
    return "\n".join(
        f"- {postulacion['puesto']} | postulado el {postulacion['fecha_de_postulacion']} | estado: {postulacion['estado']} | "
        f"próximo paso: {postulacion['proximo_paso']} | {postulacion['contacto']}"
        for postulacion in postulaciones
    )


HERRAMIENTAS_DEL_AGENTE = [buscar_empresa_por_nombre, buscar_postulaciones_de_la_empresa]
