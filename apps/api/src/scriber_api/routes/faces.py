from fastapi import APIRouter, Depends, HTTPException

from scriber_api import disk
from scriber_api.auth import require_token
from scriber_api.deps import DepsDep
from scriber_api.routes.common import need_model, need_version
from scriber_api.schemas import Frozen
from scriber_ir import face_driver

router = APIRouter(prefix="/models/{model_id}", dependencies=[Depends(require_token)])
Vec = tuple[float, float, float]


class FacePick(Frozen):
    point: Vec
    normal: Vec
    version: int | None = None


class FaceDriverOut(Frozen):
    part: str
    feature: str
    param: str
    rate: float


@router.post("/face-driver")
def driver(model_id: str, body: FacePick, d: DepsDep) -> FaceDriverOut:
    need_model(d, model_id)
    n, data = need_version(d, model_id, body.version)
    if data.status != "ok":
        raise HTTPException(404, f"version {n} of model {model_id} failed and has no faces")
    found = face_driver(disk.design(disk.version_dir(d.settings.data_dir, model_id, n)), body.point, body.normal)
    if found is None:
        raise HTTPException(404, "no parameter drives this face")
    return FaceDriverOut(part=found.part, feature=found.feature, param=found.param, rate=found.rate)
