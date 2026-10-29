from fastapi import APIRouter, Depends, HTTPException

from partwright_api import views
from partwright_api.auth import require_token
from partwright_api.deps import DepsDep
from partwright_api.routes.common import latest_design, need_model, start_rebuild
from partwright_api.schemas import Job, MaterialIn, MaterialOut
from partwright_api.work import Rebuild
from partwright_ir import material
from partwright_ir.materials import ALIASES

router = APIRouter(dependencies=[Depends(require_token)])


@router.get("/materials")
def materials(q: str | None = None) -> list[MaterialOut]:
    found = [m for _, m in ALIASES] if q is None else [m for m in [material(q)] if m]
    return [views.material(m) for m in dict.fromkeys(found)]


@router.put("/models/{model_id}/material", status_code=202)
async def set_material(model_id: str, body: MaterialIn, d: DepsDep) -> Job:
    model = need_model(d, model_id)
    found = material(body.material)
    if found is None:
        raise HTTPException(400, f"unknown material {body.material!r}; see GET /materials")
    parts = [p.id for p in latest_design(d, model_id).parts]
    if body.part is not None and body.part not in parts:
        raise HTTPException(400, f"unknown part {body.part!r}; parts: {sorted(parts)}")
    chosen = {p: found.name for p in ([body.part] if body.part else parts)}
    edit = Rebuild({}, "material", f"material {found.name} ({found.source})", materials=chosen)
    return start_rebuild(d, model, edit, "params")
