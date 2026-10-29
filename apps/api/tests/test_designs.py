import json
from typing import Any

import pytest

from apps.api.tests.conftest import Api, plate

SIZING = b"""<aircraft name="Test wing"><wing><airfoil>NACA 2412</airfoil><span unit="mm">600</span>
<root_chord unit="mm">150</root_chord><tip_chord unit="mm">80</tip_chord><sweep unit="deg">10</sweep>
<dihedral unit="deg">3</dihedral><twist unit="deg">1</twist></wing></aircraft>"""


def post_design(api: Api, project: str, design: str | dict[str, Any]) -> dict[str, Any]:
    body = {"design": json.loads(design) if isinstance(design, str) else design}
    return api.wait(api.ok(api.client.post(f"/projects/{project}/designs", json=body))["id"])


def test_posted_design_builds_without_the_llm(api: Api) -> None:
    job = post_design(api, api.project(), plate())
    assert job["status"] == "done" and job["kind"] == "build" and not api.llm.calls
    version = api.ok(api.client.get(f"/models/{job['model_id']}"))["version"]
    assert version["origin"] == "design" and version["metrics"]["bbox"] == pytest.approx([120, 80, 5])


def test_invalid_design_is_rejected_before_a_model_exists(api: Api) -> None:
    project = api.project()
    design = json.loads(plate())
    design["parts"][0]["features"][0]["sketch"] = "missing"
    response = api.client.post(f"/projects/{project}/designs", json={"design": design})
    assert response.status_code == 400 and "missing" in response.text
    assert api.ok(api.client.get(f"/projects/{project}/models")) == []


def test_sizing_xml_builds_a_wing(api: Api) -> None:
    project = api.project()
    job = api.wait(api.ok(api.client.post(f"/projects/{project}/sizing", content=SIZING))["id"])
    assert job["status"] == "done", job
    version = api.ok(api.client.get(f"/models/{job['model_id']}"))["version"]
    params = {p["name"]: p for p in version["params"]}
    assert params["wing_span"]["value"] == 600 and params["wing_span"]["provenance"]["ref"] == "sizing.xml#wing/span"
    assert version["origin"] == "sizing" and version["metrics"]["bbox"][1] == pytest.approx(600, abs=1)
    bad = api.client.post(f"/projects/{project}/sizing", content=b"<aircraft><wing/></aircraft>")
    assert bad.status_code == 400 and "wing/airfoil" in bad.text


def test_material_lookup_attaches_properties_and_mass(api: Api) -> None:
    model_id = post_design(api, api.project(), plate())["model_id"]
    [found] = api.ok(api.client.get("/materials", params={"q": "Aluminum 6061"}))
    assert (found["density_g_cm3"], found["youngs_modulus_gpa"]) == (2.70, 68.9) and "MA6061T6" in found["source"]
    job = api.wait(api.ok(api.client.put(f"/models/{model_id}/material", json={"material": "Aluminum 6061"}))["id"])
    version = api.ok(api.client.get(f"/models/{model_id}"))["version"]
    assert job["status"] == "done" and version["origin"] == "material"
    assert version["metrics"]["mass_g"] == pytest.approx(version["metrics"]["volume"] * 2.70 / 1000)
    [component] = api.ok(api.client.get(f"/models/{model_id}/components"))
    assert component["material"] == "Aluminum 6061-T6" and component["properties"]["youngs_modulus_gpa"] == 68.9
    assert api.client.put(f"/models/{model_id}/material", json={"material": "unobtainium"}).status_code == 400


def test_sensitivities_match_the_plate_formulas(api: Api) -> None:
    design = json.loads(plate())
    design["parts"][0]["material"] = "steel"
    model_id = post_design(api, api.project(), design)["model_id"]
    query = {"params": ["length", "thickness"]}
    found = api.ok(api.client.get(f"/models/{model_id}/sensitivities", params=query))
    by_name = {p["name"]: p["d"] for p in found["params"]}
    holes = 4 * 3.141592653589793 * 3.3**2
    assert by_name["length"]["bbox_x"] == pytest.approx(1, rel=1e-6) and by_name["length"]["bbox_y"] == pytest.approx(0, abs=1e-6)
    assert by_name["length"]["volume"] == pytest.approx(80 * 5, rel=1e-4)
    assert by_name["thickness"]["volume"] == pytest.approx(120 * 80 - holes, rel=1e-4)
    assert by_name["thickness"]["mass_g"] == pytest.approx((120 * 80 - holes) * 7.85 / 1000, rel=1e-4)
    assert api.client.get(f"/models/{model_id}/sensitivities", params={"params": ["nope"]}).status_code == 400


def test_simulation_over_the_limit_asks_for_suggestions(api: Api) -> None:
    design = json.loads(plate())
    design["parts"][0]["face_groups"] = [{"name": "mount_face", "faces": {"normal": "-x"}}]
    model_id = post_design(api, api.project(), design)["model_id"]
    api.llm.responses.append(json.dumps({"suggestions": [{"target": "thickness", "change": {"thickness": 6}, "rationale": "stress"}]}))
    sim = {"solver": "mock", "results": [{"face_group": "mount_face", "max_stress_mpa": 140, "allowable_mpa": 100}]}
    [made] = api.ok(api.client.post(f"/models/{model_id}/simulation", json=sim))
    assert made["change"] == {"thickness": 6} and "1.40x the allowable" in api.llm.calls[-1][-1].content
    ok = {"results": [{"face_group": "mount_face", "max_stress_mpa": 90, "allowable_mpa": 100}]}
    assert api.ok(api.client.post(f"/models/{model_id}/simulation", json=ok)) == []
    unknown = {"results": [{"face_group": "load_face", "max_stress_mpa": 90, "allowable_mpa": 100}]}
    assert api.client.post(f"/models/{model_id}/simulation", json=unknown).status_code == 400
